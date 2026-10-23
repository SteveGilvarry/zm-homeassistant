"""Fixtures for the ZoneMinder tests."""

from __future__ import annotations

from collections.abc import Generator
import re
from typing import Any

from aioresponses import CallbackResult, aioresponses
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from yarl import URL

from custom_components.zoneminder.const import DOMAIN

from .const import (
    CONFIGS,
    ENTRY_DATA,
    ENTRY_OPTIONS,
    EVENT_SUMMARY,
    EVENTS,
    HOST,
    MONITOR_STATUS,
    MONITORS,
    STORAGE,
    SYSTEM_STATUS,
    VERSION_RESPONSE,
    paginated,
)

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Load the integration from custom_components in every test."""
    return


def _url(path: str) -> re.Pattern[str]:
    """Match a zm-api endpoint regardless of its query string."""
    return re.compile(rf"^{re.escape(HOST)}/{path}(\?.*)?$")


@pytest.fixture
def zm_api() -> Generator[aioresponses]:
    """Serve a stand-in zm-api server."""
    # Let requests to Home Assistant's own test server through, so the media
    # proxy can be exercised end to end.
    with aioresponses(passthrough=["http://127.0.0.1", "http://localhost"]) as mocked:
        register_zm_api(mocked)
        yield mocked


def register_zm_api(
    mocked: aioresponses,
    *,
    monitors: list[dict[str, Any]] | None = None,
    events: list[dict[str, Any]] | None = None,
) -> None:
    """Register the endpoints the integration calls during setup."""
    mocked.post(
        f"{HOST}/api/v3/auth/login",
        payload={
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "token_type": "Bearer",
            "expire_in": 600,
        },
        repeat=True,
    )
    mocked.get(_url("api/v3/host/getVersion"), payload=VERSION_RESPONSE, repeat=True)
    mocked.get(
        _url("api/v3/monitors"),
        payload=paginated(MONITORS if monitors is None else monitors),
        repeat=True,
    )
    mocked.get(
        _url("api/v3/monitor-status"), payload=paginated(MONITOR_STATUS), repeat=True
    )
    catalogue = EVENTS if events is None else events

    def _events(url: URL, **_kwargs: Any) -> CallbackResult:
        """Answer /events the way the server does, honouring the filters."""
        selected = catalogue
        if (monitor_id := url.query.get("monitor_id")) is not None:
            selected = [e for e in selected if e["monitor_id"] == int(monitor_id)]
        if (start := url.query.get("start_time")) is not None:
            selected = [e for e in selected if e["start_date_time"] >= start]
        if (end := url.query.get("end_time")) is not None:
            selected = [e for e in selected if e["start_date_time"] < end]
        limit = int(url.query.get("page_size", 100))
        return CallbackResult(payload=paginated(selected[:limit]))

    mocked.get(_url("api/v3/events"), callback=_events, repeat=True)
    mocked.get(_url(r"api/v3/event-summaries/\d+"), payload=EVENT_SUMMARY, repeat=True)
    mocked.get(_url("api/v3/system/status"), payload=SYSTEM_STATUS, repeat=True)
    mocked.get(_url("api/v3/storage"), payload=paginated(STORAGE), repeat=True)
    mocked.get(_url("api/v3/configs"), payload=paginated(CONFIGS), repeat=True)
    mocked.get(
        _url(r"api/v3/control_presets"),
        payload=paginated([{"monitor_id": 3, "preset": 1, "label": "Front gate"}]),
        repeat=True,
    )
    mocked.post(
        _url(r"api/v3/live/\d+/start"),
        payload={"status": "started"},
        repeat=True,
    )


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a ZoneMinder config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="ZoneMinder (test)",
        data=ENTRY_DATA,
        options=ENTRY_OPTIONS,
        unique_id=HOST.lower(),
        entry_id="01JZONEMINDERTESTENTRY000",
    )


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant, config_entry: MockConfigEntry, zm_api: aioresponses
) -> MockConfigEntry:
    """Set the integration up and return its entry."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
