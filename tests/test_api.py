"""The live board client and the stop catalogue parser."""

from __future__ import annotations

import time

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.bratislava_mhd.api import LiveBoard, Vehicle, fetch_stops
from custom_components.bratislava_mhd.const import STOPS_URL

from .conftest import HODZOVO


def _row(line: str, minutes: float, **extra) -> dict:
    when = (time.time() + minutes * 60) * 1000
    return {
        "linka": line,
        "cielStr": f"to {line}",
        "cas": when,
        "casCP": when,
        "typ": "online",
        "i": hash(line) % 1000,
        **extra,
    }


async def test_tabs_replace_listed_platforms_only() -> None:
    board = LiveBoard(83)
    await board._on_tabs([{"zastavka": 83, "nastupiste": 213, "tab": [_row("4", 5)]}])
    await board._on_tabs([{"zastavka": 83, "nastupiste": 214, "tab": [_row("9", 3)]}])
    # A later message for platform 213 replaces it and keeps 214.
    await board._on_tabs([{"zastavka": 83, "nastupiste": 213, "tab": [_row("1", 7)]}])

    assert [d.line for d in board.upcoming()] == ["9", "1"]
    assert [d.line for d in board.upcoming({213})] == ["1"]


async def test_tabs_of_another_stop_are_ignored() -> None:
    board = LiveBoard(83)
    await board._on_tabs([{"zastavka": 999, "nastupiste": 1, "tab": [_row("4", 5)]}])
    assert board.upcoming() == []


async def test_departed_rows_are_dropped() -> None:
    board = LiveBoard(83)
    await board._on_tabs([{"zastavka": 83, "nastupiste": 213, "tab": [_row("4", -2), _row("9", 2)]}])
    assert [d.line for d in board.upcoming()] == ["9"]


async def test_departure_fields() -> None:
    board = LiveBoard(83)
    await board._on_tabs(
        [
            {
                "zastavka": 83,
                "nastupiste": 213,
                "tab": [
                    _row(
                        "N53",
                        10,
                        casDelta=2,
                        issi="1:2009",
                        predoslaZstr="Bratislava, Kapucínska",
                        typ="cp",
                        uviaznute=True,
                    )
                ],
            }
        ]
    )
    await board._on_vinfo({"issi": "1:2009", "type": "Solaris Urbino 10", "lf": 1, "ac": 0, "img": 1423, "imgt": 1})

    dep = board.upcoming()[0]
    data = dep.as_dict(board.vehicles.get(dep.vehicle_id))
    assert data["line"] == "N53"
    assert data["delay"] == 2
    assert data["realtime"] is False
    assert data["stuck"] is True
    assert data["last_stop"] == "Kapucínska"
    assert 8 <= data["minutes"] <= 10
    assert data["vehicle"] == {
        "type": "Solaris Urbino 10",
        "plate": None,
        "low_floor": True,
        "ac": False,
        "image": "https://imhd.sk/ba/media/vs/00001423/2009",
    }


def test_vehicle_without_image() -> None:
    assert Vehicle("1:1", "x", None, False, False, 0, 0).image_url is None


def test_distance() -> None:
    # Hodžovo nám. to Poštová is a few hundred metres.
    assert 250 < HODZOVO.distance_to(48.1458, 17.1095) < 400


async def test_fetch_stops(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(
        STOPS_URL,
        json=[
            {
                "id": 83,
                "name": "Hodžovo nám.",
                "lat": 48.1486,
                "lng": 17.1077,
                "type": "bus",
                "platform_labels": [{"id": "213", "label": "A"}, {"id": "x", "label": "?"}],
            },
            {"id": 1, "name": "No position"},
        ],
    )
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    stops = await fetch_stops(async_get_clientsession(hass))
    assert len(stops) == 1
    assert stops[0].name == "Hodžovo nám."
    assert [(p.id, p.label) for p in stops[0].platforms] == [(213, "A")]
