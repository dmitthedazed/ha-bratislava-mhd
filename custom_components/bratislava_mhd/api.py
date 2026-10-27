"""Clients for the imhd.sk live board and the stop catalogue.

The live board is the imhd.sk Socket.IO feed used by the Transi app
(https://github.com/magicsk/Transi): after connecting, the server sends `cack`,
the client answers `tabStart [stopId, "*"]`, and the server pushes `tabs`
(departures by platform) and `vInfo` (vehicle details) messages.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import aiohttp
import socketio

from .const import (
    BRATISLAVA_VIEWBOX,
    NOMINATIM_URL,
    NOMINATIM_USER_AGENT,
    SOCKET_PATH,
    SOCKET_URL,
    STOPS_URL,
    VEHICLE_IMG_URL,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Platform:
    id: int
    label: str


@dataclass(frozen=True)
class Stop:
    id: int
    name: str
    city: str
    type: str
    lat: float
    lng: float
    platforms: tuple[Platform, ...]

    def distance_to(self, lat: float, lng: float) -> float:
        """Great-circle distance in metres."""
        r = 6_371_000
        p1, p2 = math.radians(lat), math.radians(self.lat)
        dp, dl = p2 - p1, math.radians(self.lng - lng)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * r * math.asin(math.sqrt(a))


@dataclass
class Vehicle:
    issi: str
    type: str
    plate: str | None
    low_floor: bool
    ac: bool
    img: int
    imgt: int

    @property
    def image_url(self) -> str | None:
        if not self.img or ":" not in self.issi:
            return None
        return VEHICLE_IMG_URL.format(
            folder="vm" if self.imgt == 0 else "vs",
            img=self.img,
            vehicle=self.issi.split(":", 1)[1],
        )


@dataclass
class Departure:
    trip_id: int
    line: str
    platform: int
    headsign: str
    scheduled: float  # epoch seconds
    expected: float  # epoch seconds
    delay: int  # minutes
    realtime: bool
    vehicle_id: str | None
    last_stop: str | None
    stuck: bool

    def as_dict(self, vehicle: Vehicle | None) -> dict[str, Any]:
        data: dict[str, Any] = {
            "line": self.line,
            "headsign": self.headsign,
            "expected": int(self.expected),
            "scheduled": int(self.scheduled),
            "minutes": max(0, int((self.expected - time.time()) // 60)),
            "delay": self.delay,
            "realtime": self.realtime,
            "stuck": self.stuck,
        }
        if self.last_stop:
            data["last_stop"] = self.last_stop
        if vehicle:
            data["vehicle"] = {
                "type": vehicle.type,
                "plate": vehicle.plate,
                "low_floor": vehicle.low_floor,
                "ac": vehicle.ac,
                "image": vehicle.image_url,
            }
        return data


async def fetch_stops(session: aiohttp.ClientSession) -> list[Stop]:
    """The Bratislava stop catalogue Transi uses, with platform labels."""
    async with session.get(STOPS_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        resp.raise_for_status()
        raw = await resp.json(content_type=None)
    stops = []
    for item in raw:
        if item.get("lat") is None or item.get("lng") is None:
            continue
        platforms = tuple(
            Platform(int(p["id"]), p.get("label") or "")
            for p in item.get("platform_labels") or []
            if str(p.get("id", "")).isdigit()
        )
        stops.append(
            Stop(
                id=int(item["id"]),
                name=item.get("name") or str(item["id"]),
                city=item.get("city") or "",
                type=item.get("type") or "",
                lat=float(item["lat"]),
                lng=float(item["lng"]),
                platforms=platforms,
            )
        )
    return stops


class GeocodeError(Exception):
    """The address matched nothing."""


async def geocode(session: aiohttp.ClientSession, address: str) -> tuple[float, float, str]:
    """Latitude, longitude and display name of an address, via OpenStreetMap Nominatim."""
    params = {"q": address, "format": "jsonv2", "limit": "1", "countrycodes": "sk"}
    # Prefer the Bratislava region without excluding the rest of Slovakia.
    params["viewbox"] = BRATISLAVA_VIEWBOX
    async with session.get(
        NOMINATIM_URL,
        params=params,
        headers={"User-Agent": NOMINATIM_USER_AGENT, "Accept-Language": "sk"},
        timeout=aiohttp.ClientTimeout(total=15),
    ) as resp:
        resp.raise_for_status()
        results = await resp.json(content_type=None)
    if not results:
        raise GeocodeError(address)
    first = results[0]
    return float(first["lat"]), float(first["lon"]), first.get("display_name", address)


def _parse_departure(row: dict[str, Any], platform: int) -> Departure:
    expected = (row.get("cas") or 0) / 1000
    scheduled = round((row.get("casCP") or 0) / 1000 / 60) * 60
    last = row.get("predoslaZstr")
    return Departure(
        trip_id=int(row.get("i") or 0),
        line=str(row.get("linka") or "?"),
        platform=platform,
        headsign=row.get("cielStr") or row.get("konecnaZstr") or "?",
        scheduled=scheduled,
        expected=expected,
        delay=int(row.get("casDelta") or 0),
        realtime=row.get("typ") == "online",
        vehicle_id=row.get("issi"),
        last_stop=last.replace("Bratislava, ", "") if last else None,
        stuck=bool(row.get("uviaznute")),
    )


@dataclass
class LiveBoard:
    """One Socket.IO connection streaming the departure board of one stop."""

    stop_id: int
    on_update: Callable[[], None] | None = None
    departures: dict[int, list[Departure]] = field(default_factory=dict)
    vehicles: dict[str, Vehicle] = field(default_factory=dict)
    info_texts: list[str] = field(default_factory=list)
    connected: bool = False
    last_message: float | None = None

    def __post_init__(self) -> None:
        self._sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_delay=2,
            reconnection_delay_max=30,
        )
        self._task: asyncio.Task | None = None
        self._closing = False
        self._sio.on("connect", self._on_connect)
        self._sio.on("disconnect", self._on_disconnect)
        self._sio.on("cack", self._on_cack)
        self._sio.on("tabs", self._on_tabs)
        self._sio.on("vInfo", self._on_vinfo)
        self._sio.on("iText", self._on_itext)

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name=f"bratislava_mhd_{self.stop_id}")

    async def stop(self) -> None:
        self._closing = True
        # Closing anyway: a failed disconnect has nothing left to clean up.
        with contextlib.suppress(Exception):
            await self._sio.disconnect()
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _run(self) -> None:
        # The client reconnects by itself once connected; this loop covers the first connect.
        delay = 2
        while not self._closing:
            try:
                await self._sio.connect(
                    SOCKET_URL, socketio_path=SOCKET_PATH, transports=["websocket"], wait_timeout=15
                )
                await self._sio.wait()
                return
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Stop %s: connect failed: %s", self.stop_id, err)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)

    def _notify(self) -> None:
        if self.on_update:
            self.on_update()

    async def _on_connect(self) -> None:
        self.connected = True
        self._notify()

    async def _on_disconnect(self, *_: Any) -> None:
        self.connected = False
        self._notify()

    async def _on_cack(self, *_: Any) -> None:
        await self._sio.emit("tabStart", [self.stop_id, "*"])
        await self._sio.emit("infoStart")

    async def _on_tabs(self, data: Any) -> None:
        # Each message replaces the rows of the platforms it lists and leaves the others.
        if not isinstance(data, list):
            return
        for item in data:
            if not isinstance(item, dict) or item.get("zastavka") != self.stop_id:
                continue
            platform = item.get("nastupiste")
            if platform is None:
                continue
            self.departures[int(platform)] = [
                _parse_departure(row, int(platform)) for row in item.get("tab") or [] if isinstance(row, dict)
            ]
        self.last_message = time.time()
        self._notify()

    async def _on_vinfo(self, data: Any) -> None:
        if not isinstance(data, dict) or not data.get("issi"):
            return
        self.vehicles[data["issi"]] = Vehicle(
            issi=data["issi"],
            type=data.get("type") or "",
            plate=data.get("plate"),
            low_floor=data.get("lf") == 1,
            ac=data.get("ac") == 1,
            img=int(data.get("img") or 0),
            imgt=int(data.get("imgt") or 0),
        )
        self._notify()

    async def _on_itext(self, data: Any) -> None:
        if isinstance(data, list):
            self.info_texts = [t for t in data if isinstance(t, str) and t]
            self._notify()

    def upcoming(self, platforms: set[int] | None = None) -> list[Departure]:
        """Departures not yet gone, by expected time."""
        cutoff = time.time() - 30
        rows = [
            d
            for platform, deps in self.departures.items()
            if platforms is None or platform in platforms
            for d in deps
            if d.expected >= cutoff
        ]
        return sorted(rows, key=lambda d: (d.expected, d.trip_id))
