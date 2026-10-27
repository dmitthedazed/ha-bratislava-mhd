"""Shared fixtures: a small stop catalogue, and no network."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.bratislava_mhd.api import Platform, Stop

pytest_plugins = ["pytest_homeassistant_custom_component"]

HODZOVO = Stop(83, "Hodžovo nám.", "Bratislava", "bus", 48.1486, 17.1077, (Platform(213, "A"), Platform(214, "B")))
POSTOVA = Stop(270, "Poštová", "Bratislava", "bus", 48.1458, 17.1095, (Platform(664, "A"), Platform(665, "B")))
TRNAVSKE = Stop(394, "Trnavské mýto", "Bratislava", "bus", 48.1575, 17.1270, (Platform(953, "A"),))
CATALOGUE = [HODZOVO, POSTOVA, TRNAVSKE]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load integrations from custom_components."""


@pytest.fixture
def mock_catalogue() -> Generator[AsyncMock]:
    with patch("custom_components.bratislava_mhd.config_flow.fetch_stops", AsyncMock(return_value=CATALOGUE)) as mock:
        yield mock


@pytest.fixture
def mock_geocode() -> Generator[AsyncMock]:
    with patch(
        "custom_components.bratislava_mhd.config_flow.geocode",
        AsyncMock(return_value=(48.1464, 17.1087, "Obchodná 10, Bratislava")),
    ) as mock:
        yield mock


@pytest.fixture
def no_socket() -> Generator[None]:
    """Boards don't connect; tests feed them messages."""
    with (
        patch("custom_components.bratislava_mhd.api.LiveBoard.start"),
        patch("custom_components.bratislava_mhd.api.LiveBoard.stop", AsyncMock()),
    ):
        yield
