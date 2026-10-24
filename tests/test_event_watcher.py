"""Tests for noticing events without MQTT."""

from __future__ import annotations

import asyncio

from aioresponses import aioresponses
from homeassistant.core import HomeAssistant, callback
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zoneminder.event_watcher import (
    async_publish_event,
    labels_from_notes,
)
from custom_components.zoneminder.mqtt import ZoneMinderMQTTEvent

from .const import EVENTS, event


async def test_watcher_reports_events_without_mqtt(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Start and end reach the entities by polling alone, and startup is quiet."""
    from .conftest import register_zm_api

    catalogue = list(EVENTS)
    with aioresponses(passthrough=["http://127.0.0.1"]) as mocked:
        register_zm_api(mocked, events=catalogue)
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        watcher = config_entry.runtime_data.event_watcher

        # Events that already existed at startup are not news.
        assert hass.states.get("event.back_door_event").state == "unknown"

        catalogue.insert(
            0,
            event(
                400,
                2,
                cause="Motion",
                start="2026-08-22T14:00:00Z",
                end=None,
                alarm_frames=3,
                default_video=None,
            ),
        )
        await watcher.async_check()
        await hass.async_block_till_done()
        state = hass.states.get("event.back_door_event")
        assert state.attributes["event_type"] == "motion"
        assert state.attributes["event_id"] == 400
        assert hass.states.get("binary_sensor.back_door_motion").state == "on"

        catalogue[0] = event(
            400, 2, cause="Motion", start="2026-08-22T14:00:00Z", alarm_frames=3
        )
        await watcher.async_check()
        await hass.async_block_till_done()
        assert hass.states.get("event.back_door_event").attributes["event_type"] == (
            "ended"
        )
        assert hass.states.get("binary_sensor.back_door_motion").state == "off"


async def test_a_short_event_between_checks_still_fires(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """An event that opened and closed between two checks fires start and end."""
    from .conftest import register_zm_api

    catalogue = list(EVENTS)
    fired: list[str] = []
    with aioresponses(passthrough=["http://127.0.0.1"]) as mocked:
        register_zm_api(mocked, events=catalogue)
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        watcher = config_entry.runtime_data.event_watcher
        await watcher.async_check()

        @callback
        def _record(e) -> None:
            if e.data["entity_id"] == "event.back_door_event":
                fired.append(e.data["new_state"].attributes.get("event_type"))

        hass.bus.async_listen("state_changed", _record)
        catalogue.insert(0, event(401, 2, cause="Motion", start="2026-08-22T14:01:00Z"))
        await watcher.async_check()
        await hass.async_block_till_done()

    assert fired == ["motion", "ended"]


async def test_mqtt_and_polling_do_not_double_fire(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Whichever source hears about an event second is ignored."""
    start = ZoneMinderMQTTEvent(monitor_id=2, event_id=500, action="start")

    assert async_publish_event(hass, setup_integration, start)
    assert not async_publish_event(hass, setup_integration, start)
    assert async_publish_event(
        hass,
        setup_integration,
        ZoneMinderMQTTEvent(monitor_id=2, event_id=500, action="end"),
    )


def test_labels_come_from_zmeventnotification_notes() -> None:
    """Object detection results survive without MQTT, via the event notes."""
    assert labels_from_notes("[a] detected:person:97% car:81% Motion: Front") == [
        "person",
        "car",
    ]
    assert labels_from_notes("Motion: All") == []
    assert labels_from_notes(None) == []


SSE_BODY = (
    ": hello\n\n"
    "event: alarm_state\n"
    'data: {"type":"alarm_state","monitor_id":2,"state":"idle","score":0}\n\n'
    "event: alarm_state\n"
    'data: {"type":"alarm_state","monitor_id":2,"state":"alarm","score":41}\n\n'
    "id: 410\n"
    "event: event_start\n"
    'data: {"type":"event_start","event_id":410,"monitor_id":2,"name":"Event 410",'
    '"cause":"Motion","notes":"detected:person:93%","start_date_time":'
    '"2026-08-22T14:05:00Z","end_date_time":null,"frames":10,"alarm_frames":4,'
    '"max_score":41,"length":1.5}\n\n'
)


async def test_event_stream_pushes_events_and_alarm_state(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """With API v3's stream, events and live motion arrive without MQTT."""
    from .conftest import _url, register_zm_api

    with aioresponses(passthrough=["http://127.0.0.1"]) as mocked:
        # Registered first, so this is what the integration gets.
        mocked.get(
            _url("api/v3/events/stream"),
            body=SSE_BODY,
            content_type="text/event-stream",
        )
        register_zm_api(mocked)
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        for _ in range(20):
            await asyncio.sleep(0)

        assert hass.states.get("binary_sensor.back_door_motion").state == "on"
        state = hass.states.get("event.back_door_event")
        assert state.attributes["event_type"] == "motion"
        assert state.attributes["event_id"] == 410
        assert state.attributes["detected_objects"] == ["person"]


async def test_api_v2_has_no_stream_and_keeps_polling(hass: HomeAssistant) -> None:
    """On API v2 the stream task ends quietly and polling carries on."""
    from unittest.mock import AsyncMock, MagicMock

    from aiozoneminder import ZMNotSupportedError

    from custom_components.zoneminder.event_watcher import ZoneMinderEventWatcher

    async def no_stream(since: int | None = None):
        raise ZMNotSupportedError("The legacy backend has no event stream")
        yield  # pragma: no cover

    api = MagicMock()
    api.get_events = AsyncMock(return_value=[])
    api.async_event_stream = no_stream
    entry = MagicMock()
    entry.runtime_data.coordinator.api = api

    watcher = ZoneMinderEventWatcher(hass, entry)
    watcher._unsub = lambda: None  # As if started.
    await watcher._async_run_stream()

    assert watcher.streaming is False
    api.get_events.assert_awaited()
