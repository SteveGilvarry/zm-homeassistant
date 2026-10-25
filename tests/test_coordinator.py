"""Tests for the ZoneMinder coordinator."""

from __future__ import annotations

from datetime import timedelta
import re

from aioresponses import aioresponses
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zoneminder.const import (
    CONF_INCLUDE_ARCHIVED,
    CONF_MQTT_ENABLED,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    MQTT_SCAN_INTERVAL,
)
from custom_components.zoneminder.coordinator import _resolve_interval

from .const import HOST, MONITORS, event, paginated


def _requested_event_urls(mocked: aioresponses) -> list[str]:
    """Return every /events URL the integration asked for."""
    return [
        str(url)
        for (_method, url), calls in mocked.requests.items()
        for _ in calls
        if "/api/v3/events" in str(url) and "event-summaries" not in str(url)
    ]


async def test_events_are_fetched_in_one_request(
    hass: HomeAssistant, zm_api: aioresponses, setup_integration: MockConfigEntry
) -> None:
    """Three monitors must not mean three event requests.

    The old coordinator issued one request per monitor per refresh, so a
    sixteen camera server made seventeen calls every cycle.
    """
    data = setup_integration.runtime_data.coordinator.data
    assert len(data.monitors) == len(MONITORS)

    per_monitor = [url for url in _requested_event_urls(zm_api) if "monitor_id" in url]
    # Monitor 3 has no events in the fixture, so it alone earns a follow-up.
    assert len(per_monitor) == 1
    assert "monitor_id=3" in per_monitor[0]


async def test_events_are_bucketed_per_monitor(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The bulk response is split out per monitor, newest first."""
    data = setup_integration.runtime_data.coordinator.data

    assert [e.id for e in data.events[1]] == [300, 299]
    assert [e.id for e in data.events[2]] == [298, 297]
    assert data.latest_event(1).id == 300


async def test_latest_alarm_skips_continuous_events(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Continuous recording must not look like motion."""
    data = setup_integration.runtime_data.coordinator.data

    # Monitor 1 records continuously and has no alarmed frames at all.
    assert data.latest_event(1) is not None
    assert data.latest_alarm(1) is None

    # Monitor 2 analyses, so its newest alarmed event is real motion.
    assert data.latest_alarm(2).id == 298


async def test_quiet_monitor_gets_a_targeted_fetch(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """A monitor missing from the bulk window still gets its last event."""
    config_entry.add_to_hass(hass)

    from .conftest import register_zm_api

    with aioresponses() as mocked:
        # Registered first so they win over the catch-all bulk matcher.
        mocked.get(
            re.compile(rf"^{re.escape(HOST)}/api/v3/events\?.*monitor_id=2.*$"),
            payload=paginated([event(410, 2, cause="Motion", alarm_frames=3)]),
            repeat=True,
        )
        mocked.get(
            re.compile(rf"^{re.escape(HOST)}/api/v3/events\?.*monitor_id=3.*$"),
            payload=paginated([]),
            repeat=True,
        )
        # The bulk response only covers monitor 1, as it would on a server
        # where one busy camera fills the whole window.
        register_zm_api(mocked, events=[event(500, 1)])
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    data = config_entry.runtime_data.coordinator.data
    assert [e.id for e in data.events[1]] == [500]
    assert [e.id for e in data.events[2]] == [410]
    assert data.events[3] == []


async def test_server_info_is_collected(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Version, daemon health and storage all reach the coordinator."""
    server = setup_integration.runtime_data.coordinator.data.server

    assert server.version == "1.39.22"
    assert server.api_version == "3.0.0-alpha.1"
    assert server.running is True
    assert (server.daemons_running, server.daemons_total) == (2, 3)
    assert server.total_disk_space == 51762574243


async def test_configs_are_read_for_mqtt_discovery(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """ZoneMinder's own settings tell us the MQTT topic prefix."""
    configs = setup_integration.runtime_data.coordinator.data.configs
    assert configs["ZM_MQTT_TOPIC_PREFIX"] == "ZoneMinder"


async def test_interval_follows_the_options(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """The configured interval is honoured, which it previously was not."""
    config_entry.add_to_hass(hass)

    for options, expected in (
        ({CONF_MQTT_ENABLED: True}, MQTT_SCAN_INTERVAL),
        ({CONF_MQTT_ENABLED: False}, DEFAULT_SCAN_INTERVAL),
        ({CONF_MQTT_ENABLED: True, CONF_SCAN_INTERVAL: 90}, timedelta(seconds=90)),
    ):
        hass.config_entries.async_update_entry(config_entry, options=options)
        assert _resolve_interval(config_entry) == expected


async def test_event_counts_leave_archived_out_when_asked(
    hass: HomeAssistant, zm_api: aioresponses, config_entry: MockConfigEntry
) -> None:
    """With include_archived off, the client is asked for counts without them."""
    config_entry = MockConfigEntry(
        domain=config_entry.domain,
        data=config_entry.data,
        options={**config_entry.options, CONF_INCLUDE_ARCHIVED: False},
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    archived = [url for url in _requested_event_urls(zm_api) if "archived=true" in url]
    assert archived, "no request for archived events"
    summary = config_entry.runtime_data.coordinator.data.summaries[1]
    # Fixture: 126 events, one archived; the archived event is older than a month.
    assert summary.total_events == 125
    assert summary.day_events == 85
