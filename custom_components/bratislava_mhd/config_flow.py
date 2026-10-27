"""Config flow: find stops near a point, near an address or by name, then pick their platforms.

Stops picked in one way stay picked when another is used, so they can be combined.
"""

from __future__ import annotations

import unicodedata
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    LocationSelector,
    LocationSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .api import GeocodeError, Stop, fetch_stops, geocode
from .const import (
    CONF_MAX_DEPARTURES,
    CONF_MAX_STOPS,
    CONF_PLATFORMS,
    CONF_STOPS,
    DEFAULT_MAX_DEPARTURES,
    DEFAULT_MAX_STOPS,
    DEFAULT_RADIUS,
    DOMAIN,
)

CONF_LOCATION = "location"
CONF_ADDRESS = "address"
CONF_RADIUS = "radius"
CONF_QUERY = "query"
CONF_ADD_MORE = "add_more"

MAX_SEARCH_RESULTS = 30


def _fold(text: str) -> str:
    """Lowercase without diacritics, so "hodzovo" finds "Hodžovo nám."."""
    return "".join(c for c in unicodedata.normalize("NFD", text.casefold()) if not unicodedata.combining(c))


def _stop_to_data(stop: Stop) -> dict[str, Any]:
    return {
        "id": stop.id,
        "name": stop.name,
        "type": stop.type,
        "lat": stop.lat,
        "lng": stop.lng,
        "platforms": [{"id": p.id, "label": p.label} for p in stop.platforms],
    }


class _StopPicker:
    """Steps shared by setup and options: method menu → nearby / address / search → stops → platforms."""

    hass: Any
    _catalogue: list[Stop] | None = None
    # Candidates of the last search, with the distance to show (None when there's no reference point).
    _candidates: list[tuple[Stop, float | None]]
    # Stops picked so far, by id, in pick order.
    _picked: dict[int, Stop]
    # Platforms preselected on the last step ("stop:platform"); None means all.
    _preselected: set[str] | None = None

    def _init_picker(self) -> None:
        if not hasattr(self, "_picked"):
            self._picked = {}
            self._candidates = []

    async def _load_catalogue(self) -> str | None:
        if self._catalogue is None:
            try:
                self._catalogue = [s for s in await fetch_stops(async_get_clientsession(self.hass)) if s.platforms]
            except (aiohttp.ClientError, TimeoutError, ValueError):
                return "cannot_connect"
        return None

    def _nearest(self, lat: float, lng: float, radius: float, limit: int) -> list[tuple[Stop, float | None]]:
        by_distance = sorted(((s, s.distance_to(lat, lng)) for s in self._catalogue), key=lambda x: x[1])
        within = [x for x in by_distance if x[1] <= radius][:limit]
        # Nothing inside the circle: still offer the closest ones instead of a dead end.
        return within or by_distance[:limit]

    async def async_step_method(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        self._init_picker()
        return self.async_show_menu(step_id="method", menu_options=["nearby", "address", "search"])

    async def async_step_nearby(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not (error := await self._load_catalogue()):
                loc = user_input[CONF_LOCATION]
                self._candidates = self._nearest(
                    loc["latitude"],
                    loc["longitude"],
                    loc.get("radius") or DEFAULT_RADIUS,
                    int(user_input[CONF_MAX_STOPS]),
                )
                return await self.async_step_stops()
            errors["base"] = error
        lat, lng = self._reference_point()
        return self.async_show_form(
            step_id="nearby",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LOCATION, default={"latitude": lat, "longitude": lng, "radius": DEFAULT_RADIUS}
                    ): LocationSelector(LocationSelectorConfig(radius=True, icon="mdi:bus-stop")),
                    vol.Required(CONF_MAX_STOPS, default=DEFAULT_MAX_STOPS): _count_selector(30),
                }
            ),
            errors=errors,
        )

    async def async_step_address(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            error = await self._load_catalogue()
            if not error:
                try:
                    lat, lng, _ = await geocode(async_get_clientsession(self.hass), user_input[CONF_ADDRESS])
                except GeocodeError:
                    error = "address_not_found"
                except (aiohttp.ClientError, TimeoutError):
                    error = "geocode_failed"
            if not error:
                self._candidates = self._nearest(
                    lat, lng, float(user_input[CONF_RADIUS]), int(user_input[CONF_MAX_STOPS])
                )
                return await self.async_step_stops()
            errors["base"] = error
        return self.async_show_form(
            step_id="address",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS, default=(user_input or {}).get(CONF_ADDRESS, "")): TextSelector(),
                    vol.Required(CONF_RADIUS, default=DEFAULT_RADIUS): NumberSelector(
                        NumberSelectorConfig(
                            min=50, max=3000, step=50, unit_of_measurement="m", mode=NumberSelectorMode.BOX
                        )
                    ),
                    vol.Required(CONF_MAX_STOPS, default=DEFAULT_MAX_STOPS): _count_selector(30),
                }
            ),
            errors=errors,
        )

    async def async_step_search(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not (error := await self._load_catalogue()):
                queries = [_fold(q.strip()) for q in user_input[CONF_QUERY].split(",") if q.strip()]
                lat, lng = self._reference_point()
                found = [
                    (s, s.distance_to(lat, lng)) for s in self._catalogue if any(q in _fold(s.name) for q in queries)
                ]
                # Exact and prefix matches first, then by distance from home.
                found.sort(key=lambda x: (not any(_fold(x[0].name).startswith(q) for q in queries), x[1]))
                if found:
                    self._candidates = found[:MAX_SEARCH_RESULTS]
                    return await self.async_step_stops()
                error = "no_stops"
            errors["base"] = error
        return self.async_show_form(
            step_id="search",
            data_schema=vol.Schema(
                {vol.Required(CONF_QUERY, default=(user_input or {}).get(CONF_QUERY, "")): TextSelector()}
            ),
            errors=errors,
        )

    async def async_step_stops(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        shown = {s.id: s for s, _ in self._candidates} | self._picked
        if user_input is not None:
            ids = [int(i) for i in user_input[CONF_STOPS]]
            self._picked = {i: shown[i] for i in ids if i in shown}
            if user_input.get(CONF_ADD_MORE):
                return await self.async_step_method()
            if self._picked:
                return await self.async_step_platforms()
            errors["base"] = "select_stop"
        distances = {s.id: d for s, d in self._candidates}
        options = [
            SelectOptionDict(value=str(stop.id), label=self._stop_label(stop, distances.get(stop.id)))
            for stop in [*self._picked.values(), *(s for s, _ in self._candidates if s.id not in self._picked)]
        ]
        # A fresh nearby search preselects the closest three; picks made earlier stay ticked.
        default = [str(i) for i in self._picked] or [str(s.id) for s, _ in self._candidates[:3]]
        return self.async_show_form(
            step_id="stops",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STOPS, default=default): SelectSelector(
                        SelectSelectorConfig(options=options, multiple=True, mode=SelectSelectorMode.LIST)
                    ),
                    vol.Optional(CONF_ADD_MORE, default=False): bool,
                }
            ),
            errors=errors,
        )

    def _stop_label(self, stop: Stop, distance: float | None) -> str:
        parts = [stop.name]
        if distance is not None:
            parts.append(f"{round(distance)} m" if distance < 1000 else f"{distance / 1000:.1f} km")
        parts.append(", ".join(p.label or str(p.id) for p in stop.platforms))
        return " · ".join(parts)

    def _platforms_schema(self) -> vol.Schema:
        options = [
            SelectOptionDict(value=f"{stop.id}:{p.id}", label=f"{stop.name} — {p.label or p.id}")
            for stop in self._picked.values()
            for p in stop.platforms
        ]
        values = [o["value"] for o in options]
        known = {v.split(":")[0] for v in self._preselected or ()}
        # Stops configured before keep their platforms; new ones start with all of theirs.
        default = [
            v for v in values if self._preselected is None or v in self._preselected or v.split(":")[0] not in known
        ]
        return vol.Schema(
            {
                vol.Required(CONF_PLATFORMS, default=default): SelectSelector(
                    SelectSelectorConfig(options=options, multiple=True, mode=SelectSelectorMode.LIST)
                )
            }
        )

    def _result(self, platforms: list[str]) -> dict[str, Any]:
        wanted: dict[int, set[int]] = {}
        for value in platforms:
            stop_id, platform_id = value.split(":")
            wanted.setdefault(int(stop_id), set()).add(int(platform_id))
        stops = []
        for stop in self._picked.values():
            if stop.id not in wanted:
                continue
            data = _stop_to_data(stop)
            data["platforms"] = [p for p in data["platforms"] if p["id"] in wanted[stop.id]]
            stops.append(data)
        return {CONF_STOPS: stops}

    def _reference_point(self) -> tuple[float, float]:
        return self.hass.config.latitude, self.hass.config.longitude


def _count_selector(maximum: int) -> NumberSelector:
    return NumberSelector(NumberSelectorConfig(min=1, max=maximum, step=1, mode=NumberSelectorMode.BOX))


class BratislavaMhdConfigFlow(_StopPicker, ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self.async_step_method()

    async def async_step_platforms(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_PLATFORMS]:
                data = self._result(user_input[CONF_PLATFORMS])
                names = [s["name"] for s in data[CONF_STOPS]]
                title = names[0] if len(names) == 1 else f"{names[0]} +{len(names) - 1}"
                return self.async_create_entry(title=f"MHD {title}", data=data)
            errors["base"] = "select_platform"
        return self.async_show_form(step_id="platforms", data_schema=self._platforms_schema(), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return BratislavaMhdOptionsFlow()


class BratislavaMhdOptionsFlow(_StopPicker, OptionsFlow):
    """Change the departure count, or add and remove stops."""

    def _current_stops(self) -> list[dict[str, Any]]:
        return self.config_entry.options.get(CONF_STOPS, self.config_entry.data[CONF_STOPS])

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._options = {**self.config_entry.options, CONF_MAX_DEPARTURES: int(user_input[CONF_MAX_DEPARTURES])}
            if not user_input.get("change_stops"):
                return self.async_create_entry(data=self._options)
            if error := await self._load_catalogue():
                return self.async_abort(reason=error)
            # Start from the configured stops, refreshed from the catalogue.
            by_id = {s.id: s for s in self._catalogue}
            current = self._current_stops()
            self._init_picker()
            self._picked = {s["id"]: by_id[s["id"]] for s in current if s["id"] in by_id}
            self._preselected = {f"{s['id']}:{p['id']}" for s in current for p in s["platforms"]}
            return await self.async_step_stops()
        current = self.config_entry.options.get(CONF_MAX_DEPARTURES, DEFAULT_MAX_DEPARTURES)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MAX_DEPARTURES, default=current): _count_selector(30),
                    vol.Optional("change_stops", default=False): bool,
                }
            ),
        )

    async def async_step_platforms(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_PLATFORMS]:
                return self.async_create_entry(data={**self._options, **self._result(user_input[CONF_PLATFORMS])})
            errors["base"] = "select_platform"
        return self.async_show_form(step_id="platforms", data_schema=self._platforms_schema(), errors=errors)

    def _reference_point(self) -> tuple[float, float]:
        stops = self._current_stops()
        if not stops:
            return super()._reference_point()
        return sum(s["lat"] for s in stops) / len(stops), sum(s["lng"] for s in stops) / len(stops)
