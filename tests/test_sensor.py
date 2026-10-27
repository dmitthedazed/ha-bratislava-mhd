"""Platform sensors follow their stop's live board."""

from __future__ import annotations

import time

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bratislava_mhd.const import CONF_MAX_DEPARTURES, CONF_STOPS, DOMAIN

pytestmark = pytest.mark.usefixtures("no_socket")

STOP = {
    "id": 83,
    "name": "Hodžovo nám.",
    "type": "bus",
    "lat": 48.1486,
    "lng": 17.1077,
    "platforms": [{"id": 213, "label": "A"}, {"id": 214, "label": "B"}],
}


def _row(line: str, minutes: float) -> dict:
    when = (time.time() + minutes * 60) * 1000
    return {"linka": line, "cielStr": "Dúbravka", "cas": when, "casCP": when, "typ": "online", "i": int(minutes * 100)}


async def _setup(hass: HomeAssistant, **options) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="MHD", data={CONF_STOPS: [STOP]}, options=options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_sensors_follow_board(hass: HomeAssistant) -> None:
    entry = await _setup(hass, **{CONF_MAX_DEPARTURES: 2})
    # Unavailable until the board has sent anything.
    assert hass.states.get("sensor.hodzovo_nam_nastupiste_a").state == "unavailable"

    board = entry.runtime_data.boards[83]
    board.connected = True
    await board._on_tabs(
        [
            {"zastavka": 83, "nastupiste": 213, "tab": [_row("4", 5.5), _row("9", 12.5), _row("1", 20.5)]},
            {"zastavka": 83, "nastupiste": 214, "tab": []},
        ]
    )
    await hass.async_block_till_done()

    a = hass.states.get("sensor.hodzovo_nam_nastupiste_a")
    assert a.state == "5"
    assert a.attributes["platform"] == "A"
    assert a.attributes["stop_name"] == "Hodžovo nám."
    assert a.attributes["mhd_board"] is True
    assert [d["line"] for d in a.attributes["departures"]] == ["4", "9"]

    b = hass.states.get("sensor.hodzovo_nam_nastupiste_b")
    assert b.state == "unknown"
    assert b.attributes["departures"] == []


async def test_unload(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
