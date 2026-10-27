"""Bratislava MHD: live departures from imhd.sk for the stops near you."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .api import LiveBoard
from .const import CARD_URL, CONF_STOPS, DOMAIN

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class Hub:
    """The live boards of one config entry and the entities listening to them."""

    stops: list[dict[str, Any]]
    boards: dict[int, LiveBoard] = field(default_factory=dict)
    listeners: dict[int, list[Callable[[], None]]] = field(default_factory=dict)

    def listen(self, stop_id: int, cb: Callable[[], None]) -> Callable[[], None]:
        self.listeners.setdefault(stop_id, []).append(cb)
        return lambda: self.listeners[stop_id].remove(cb)

    def start(self) -> None:
        for stop in self.stops:
            stop_id = stop["id"]
            board = LiveBoard(stop_id, on_update=lambda sid=stop_id: self._dispatch(sid))
            self.boards[stop_id] = board
            board.start()

    async def stop(self) -> None:
        for board in self.boards.values():
            await board.stop()

    @callback
    def _dispatch(self, stop_id: int) -> None:
        for cb in list(self.listeners.get(stop_id, [])):
            cb()


type MhdConfigEntry = ConfigEntry[Hub]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    # Without the frontend (e.g. in tests) there is nowhere to show the card.
    if "frontend" in hass.config.components:
        await async_register_card(hass)
    return True


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the Lovelace card and load it on every dashboard."""
    integration = await async_get_integration(hass, DOMAIN)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(Path(__file__).parent / "www" / "bratislava-mhd-card.js"), False)]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={integration.version}")


async def async_setup_entry(hass: HomeAssistant, entry: MhdConfigEntry) -> bool:
    hub = Hub(entry.options.get(CONF_STOPS, entry.data[CONF_STOPS]))
    hub.start()
    entry.runtime_data = hub
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MhdConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        await entry.runtime_data.stop()
    return ok


async def _async_reload(hass: HomeAssistant, entry: MhdConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
