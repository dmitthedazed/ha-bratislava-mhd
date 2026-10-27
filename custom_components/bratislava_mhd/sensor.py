"""One sensor per platform: minutes until the next departure, the board in attributes."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from . import Hub, MhdConfigEntry
from .const import CONF_MAX_DEPARTURES, DEFAULT_MAX_DEPARTURES, DOMAIN

# Countdowns move even when the board doesn't.
TICK = timedelta(seconds=20)


async def async_setup_entry(
    hass: HomeAssistant, entry: MhdConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    hub = entry.runtime_data
    max_departures = int(entry.options.get(CONF_MAX_DEPARTURES, DEFAULT_MAX_DEPARTURES))
    async_add_entities(
        PlatformSensor(hub, stop, platform, max_departures) for stop in hub.stops for platform in stop["platforms"]
    )


class PlatformSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:bus-clock"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_attribution = "Data: imhd.sk"
    _unrecorded_attributes = frozenset({"departures", "info", "stop_latitude", "stop_longitude"})

    def __init__(self, hub: Hub, stop: dict[str, Any], platform: dict[str, Any], max_departures: int) -> None:
        self._hub = hub
        self._stop = stop
        self._platform = platform
        self._max = max_departures
        label = platform["label"] or str(platform["id"])
        self._attr_name = f"Nástupište {label}"
        self._attr_unique_id = f"{stop['id']}_{platform['id']}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(stop["id"]))},
            name=stop["name"],
            manufacturer="imhd.sk",
            model=f"Zastávka {stop['id']}",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=f"https://imhd.sk/ba/online-zastavkova-tabula?z={stop['id']}",
        )

    @property
    def _board(self):
        return self._hub.boards[self._stop["id"]]

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._hub.listen(self._stop["id"], self.async_write_ha_state))
        self.async_on_remove(async_track_time_interval(self.hass, self._tick, TICK))

    @callback
    def _tick(self, _now) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        # Keep showing the last board through short reconnects.
        return self._board.connected or self._board.last_message is not None

    @property
    def native_value(self) -> int | None:
        upcoming = self._board.upcoming({self._platform["id"]})
        if not upcoming:
            return None
        return upcoming[0].as_dict(None)["minutes"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        board = self._board
        upcoming = board.upcoming({self._platform["id"]})[: self._max]
        return {
            "mhd_board": True,
            "stop_id": self._stop["id"],
            "stop_name": self._stop["name"],
            "stop_type": self._stop.get("type"),
            "stop_latitude": self._stop["lat"],
            "stop_longitude": self._stop["lng"],
            "platform_id": self._platform["id"],
            "platform": self._platform["label"],
            "connected": board.connected,
            "departures": [d.as_dict(board.vehicles.get(d.vehicle_id or "")) for d in upcoming],
            "info": board.info_texts,
        }
