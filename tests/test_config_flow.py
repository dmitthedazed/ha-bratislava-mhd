"""Finding stops near a point, near an address and by name, and changing them later."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bratislava_mhd.api import GeocodeError
from custom_components.bratislava_mhd.const import CONF_MAX_DEPARTURES, CONF_STOPS, DOMAIN

pytestmark = pytest.mark.usefixtures("mock_catalogue", "no_socket")


def _options(result, key: str) -> list[str]:
    return [o["value"] for o in result["data_schema"].schema[key].config["options"]]


async def _start(hass: HomeAssistant, method: str):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["nearby", "address", "search"]
    return await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": method})


async def test_nearby(hass: HomeAssistant) -> None:
    result = await _start(hass, "nearby")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"location": {"latitude": 48.1486, "longitude": 17.1077, "radius": 500}, "max_stops": 5},
    )
    assert result["step_id"] == "stops"
    # Trnavské mýto is 1.7 km away, outside the circle.
    assert _options(result, "stops") == ["83", "270"]

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"stops": ["83"]})
    assert result["step_id"] == "platforms"
    assert result["data_schema"]({})["platforms"] == ["83:213", "83:214"]

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"platforms": ["83:213"]})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "MHD Hodžovo nám."
    assert result["data"][CONF_STOPS] == [
        {
            "id": 83,
            "name": "Hodžovo nám.",
            "type": "bus",
            "lat": 48.1486,
            "lng": 17.1077,
            "platforms": [{"id": 213, "label": "A"}],
        }
    ]


async def test_nothing_in_radius_offers_closest(hass: HomeAssistant) -> None:
    result = await _start(hass, "nearby")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"location": {"latitude": 48.0, "longitude": 17.0, "radius": 50}, "max_stops": 2}
    )
    assert len(_options(result, "stops")) == 2


async def test_address(hass: HomeAssistant, mock_geocode: AsyncMock) -> None:
    result = await _start(hass, "address")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"address": "Obchodná 10", "radius": 300, "max_stops": 5}
    )
    mock_geocode.assert_awaited_once()
    assert result["step_id"] == "stops"
    assert _options(result, "stops")[0] == "270"


async def test_address_not_found(hass: HomeAssistant, mock_geocode: AsyncMock) -> None:
    mock_geocode.side_effect = GeocodeError("nowhere")
    result = await _start(hass, "address")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"address": "nowhere", "radius": 300, "max_stops": 5}
    )
    assert result["step_id"] == "address"
    assert result["errors"] == {"base": "address_not_found"}


async def test_search_without_diacritics_and_combine(hass: HomeAssistant) -> None:
    result = await _start(hass, "search")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"query": "hodzovo"})
    assert _options(result, "stops") == ["83"]

    # Keep it and look for another one.
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"stops": ["83"], "add_more": True})
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "search"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"query": "trnavske, postova"})
    # Already picked stops stay on top.
    found = _options(result, "stops")
    assert found[0] == "83"
    assert sorted(found[1:]) == ["270", "394"]

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"stops": ["83", "394"]})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"platforms": ["83:214", "394:953"]})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "MHD Hodžovo nám. +1"
    assert [s["id"] for s in result["data"][CONF_STOPS]] == [83, 394]


async def test_search_no_match(hass: HomeAssistant) -> None:
    result = await _start(hass, "search")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"query": "xyz"})
    assert result["errors"] == {"base": "no_stops"}


async def test_no_stop_selected(hass: HomeAssistant) -> None:
    result = await _start(hass, "search")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"query": "hodzovo"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"stops": []})
    assert result["errors"] == {"base": "select_stop"}


async def test_options_departures_only(hass: HomeAssistant) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_MAX_DEPARTURES: 3})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_MAX_DEPARTURES: 3}


async def test_options_change_stops_keeps_platforms(hass: HomeAssistant) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_MAX_DEPARTURES: 5, "change_stops": True}
    )
    assert result["step_id"] == "stops"
    assert _options(result, "stops") == ["83"]

    result = await hass.config_entries.options.async_configure(result["flow_id"], {"stops": ["83"], "add_more": True})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "search"})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"query": "postova"})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"stops": ["83", "270"]})
    # Hodžovo keeps only its configured platform; the new stop starts with all of its own.
    assert result["data_schema"]({})["platforms"] == ["83:213", "270:664", "270:665"]

    result = await hass.config_entries.options.async_configure(result["flow_id"], {"platforms": ["83:213", "270:664"]})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert [s["id"] for s in entry.options[CONF_STOPS]] == [83, 270]


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="MHD Hodžovo nám.",
        data={
            CONF_STOPS: [
                {
                    "id": 83,
                    "name": "Hodžovo nám.",
                    "type": "bus",
                    "lat": 48.1486,
                    "lng": 17.1077,
                    "platforms": [{"id": 213, "label": "A"}],
                }
            ]
        },
    )
