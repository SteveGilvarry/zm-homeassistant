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


async def test_stream_drop_withdraws_the_live_alarm_state(hass: HomeAssistant) -> None:
    """A dropped stream can't report the alarm ending, so its last state is withdrawn.

    The motion sensor follows the stream's alarm state while it's up; left at
    "alarm" after a drop, it would stay on long after the motion ended.
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    from aiozoneminder import ZMConnectionError
    from homeassistant.helpers.dispatcher import async_dispatcher_connect

    from custom_components.zoneminder.const import SIGNAL_ALARM_STATE
    from custom_components.zoneminder.event_watcher import ZoneMinderEventWatcher

    received: list[str] = []
    async_dispatcher_connect(hass, SIGNAL_ALARM_STATE.format(2), received.append)

    async def stream_then_drop(since: int | None = None):
        yield "alarm_state", {"monitor_id": 2, "state": "alarm"}
        raise ZMConnectionError("connection reset")

    api = MagicMock()
    api.get_events = AsyncMock(return_value=[])
    api.async_event_stream = stream_then_drop
    entry = MagicMock()
    entry.runtime_data.coordinator.api = api
    watcher = ZoneMinderEventWatcher(hass, entry)
    unsub = MagicMock()
    watcher._unsub = unsub

    async def stop_after_one_drop(_delay: float) -> None:
        watcher._unsub = None  # As if stopped, so the loop ends after the drop.

    with patch(
        "custom_components.zoneminder.event_watcher.asyncio.sleep", stop_after_one_drop
    ):
        await watcher._async_run_stream()
    await hass.async_block_till_done()

    assert received == ["alarm", "unknown"]
    assert watcher.streaming is False


async def test_events_open_before_the_stream_still_end(hass: HomeAssistant) -> None:
    """An event running when the stream connected gets its end within 30 s.

    The stream only reports events that start after it connects, so the
    watcher keeps checking every sixth tick while streaming.
    """
    from unittest.mock import AsyncMock, MagicMock

    from custom_components.zoneminder.event_watcher import (
        STREAMING_CHECK_TICKS,
        ZoneMinderEventWatcher,
    )

    api = MagicMock()
    api.get_events = AsyncMock(return_value=[])
    entry = MagicMock()
    entry.runtime_data.coordinator.api = api
    watcher = ZoneMinderEventWatcher(hass, entry)
    watcher.streaming = True

    for _ in range(STREAMING_CHECK_TICKS - 1):
        await watcher._async_tick(None)
    assert api.get_events.await_count == 0
    await watcher._async_tick(None)
    assert api.get_events.await_count == 1


async def test_rejected_login_pauses_polling(hass: HomeAssistant) -> None:
    """After a rejected login the watcher stops asking until reauthentication.

    Retrying every few seconds piled up failed logins while the user fixed the
    password.
    """
    from unittest.mock import AsyncMock, MagicMock

    from aiozoneminder import ZMAuthenticationError

    from custom_components.zoneminder.event_watcher import ZoneMinderEventWatcher

    api = MagicMock()
    api.get_events = AsyncMock(side_effect=ZMAuthenticationError("Login failed"))
    entry = MagicMock()
    entry.runtime_data.coordinator.api = api

    watcher = ZoneMinderEventWatcher(hass, entry)
    for _ in range(3):
        await watcher.async_check()

    assert api.get_events.await_count == 1


async def test_rejected_login_ends_the_stream(hass: HomeAssistant) -> None:
    """A rejected login on the event stream is not retried either."""
    from unittest.mock import AsyncMock, MagicMock

    from aiozoneminder import ZMAuthenticationError

    from custom_components.zoneminder.event_watcher import ZoneMinderEventWatcher

    connects = 0

    async def rejected(since: int | None = None):
        nonlocal connects
        connects += 1
        raise ZMAuthenticationError("Login failed")
        yield  # pragma: no cover

    api = MagicMock()
    api.get_events = AsyncMock(return_value=[])
    api.async_event_stream = rejected
    entry = MagicMock()
    entry.runtime_data.coordinator.api = api

    watcher = ZoneMinderEventWatcher(hass, entry)
    watcher._unsub = lambda: None  # As if started.
    await asyncio.wait_for(watcher._async_run_stream(), timeout=1)
    await watcher.async_check()

    assert connects == 1
    assert api.get_events.await_count == 1
    assert watcher.streaming is False


def _rejecting_watcher(hass: HomeAssistant, api):
    """Return a watcher whose coordinator listeners the test can fire."""
    from unittest.mock import MagicMock

    from custom_components.zoneminder.event_watcher import ZoneMinderEventWatcher

    listeners = []

    def add_listener(update):
        listeners.append(update)
        return lambda: listeners.remove(update)

    coordinator = MagicMock()
    coordinator.api = api
    coordinator.last_update_success = False
    coordinator.async_add_listener = add_listener
    entry = MagicMock()
    entry.runtime_data.coordinator = coordinator

    def refreshed(success: bool) -> None:
        coordinator.last_update_success = success
        for update in list(listeners):
            update()

    return ZoneMinderEventWatcher(hass, entry), entry, refreshed


async def test_polling_resumes_once_the_login_works_again(
    hass: HomeAssistant,
) -> None:
    """A momentary rejection does not leave the watcher off for good.

    Nothing is retried while the coordinator keeps failing; its next good
    refresh lets the watcher poll again.
    """
    from unittest.mock import AsyncMock, MagicMock

    from aiozoneminder import ZMAuthenticationError

    api = MagicMock()
    api.get_events = AsyncMock(side_effect=ZMAuthenticationError("Login failed"))
    watcher, _entry, refreshed = _rejecting_watcher(hass, api)

    await watcher.async_check()
    refreshed(False)
    await watcher.async_check()
    assert api.get_events.await_count == 1

    api.get_events.side_effect = None
    api.get_events.return_value = []
    refreshed(True)
    await watcher.async_check()
    assert api.get_events.await_count == 2


async def test_stream_restarts_once_the_login_works_again(
    hass: HomeAssistant,
) -> None:
    """The stream task that ended on a rejection is started again, once."""
    from unittest.mock import AsyncMock, MagicMock

    from aiozoneminder import ZMAuthenticationError

    connects = 0

    async def rejected(since: int | None = None):
        nonlocal connects
        connects += 1
        raise ZMAuthenticationError("Login failed")
        yield  # pragma: no cover

    api = MagicMock()
    api.get_events = AsyncMock(return_value=[])
    api.async_event_stream = rejected
    watcher, entry, refreshed = _rejecting_watcher(hass, api)
    watcher._unsub = lambda: None  # As if started.
    await asyncio.wait_for(watcher._async_run_stream(), timeout=1)
    assert connects == 1

    refreshed(False)
    entry.async_create_background_task.assert_not_called()

    refreshed(True)
    refreshed(True)
    entry.async_create_background_task.assert_called_once()
    restarted = entry.async_create_background_task.call_args.args[1]
    await asyncio.wait_for(restarted, timeout=1)
    assert connects == 2


async def test_rejected_login_withdraws_the_live_alarm_state(
    hass: HomeAssistant,
) -> None:
    """A stream ended by a rejected login can't report the alarm ending either."""
    from unittest.mock import AsyncMock, MagicMock

    from aiozoneminder import ZMAuthenticationError
    from homeassistant.helpers.dispatcher import async_dispatcher_connect

    from custom_components.zoneminder.const import SIGNAL_ALARM_STATE
    from custom_components.zoneminder.event_watcher import ZoneMinderEventWatcher

    received: list[str] = []
    async_dispatcher_connect(hass, SIGNAL_ALARM_STATE.format(2), received.append)

    async def stream_then_reject(since: int | None = None):
        yield "alarm_state", {"monitor_id": 2, "state": "alarm"}
        raise ZMAuthenticationError("Login failed")

    api = MagicMock()
    api.get_events = AsyncMock(return_value=[])
    api.async_event_stream = stream_then_reject
    entry = MagicMock()
    entry.runtime_data.coordinator.api = api
    watcher = ZoneMinderEventWatcher(hass, entry)
    watcher._unsub = MagicMock()

    await watcher._async_run_stream()
    await hass.async_block_till_done()

    assert received == ["alarm", "unknown"]
