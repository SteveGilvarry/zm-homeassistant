"""Tests for ZoneMinder motion detection."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from aioresponses import aioresponses
from aiozoneminder import ServerInfo
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.zoneminder.const import MQTT_MOTION_TIMEOUT, SIGNAL_MQTT_EVENT
from custom_components.zoneminder.mqtt import ZoneMinderMQTTEvent

DRIVEWAY = "binary_sensor.driveway_motion"  # records continuously, never analyses
BACK_DOOR = "binary_sensor.back_door_motion"  # analyses, so it can see motion


def _send(hass: HomeAssistant, monitor_id: int, event_id: int, action: str) -> None:
    """Deliver an MQTT notification the way the listener would."""
    async_dispatcher_send(
        hass,
        SIGNAL_MQTT_EVENT.format(monitor_id),
        ZoneMinderMQTTEvent(monitor_id=monitor_id, event_id=event_id, action=action),
    )


async def test_continuous_recording_is_not_motion(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """A camera that records around the clock always has an open event.

    Treating any open event as motion pinned these sensors on permanently.
    """
    assert hass.states.get(DRIVEWAY).state == STATE_OFF


async def test_alarmed_event_is_motion(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """A finished alarm event is not still happening."""
    # Fixture event 298 has alarm frames but has ended.
    assert hass.states.get(BACK_DOOR).state == STATE_OFF


async def test_mqtt_turns_motion_on_and_off(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """MQTT drives the state without waiting for the next poll."""
    _send(hass, 2, 999, "start")
    await hass.async_block_till_done()
    assert hass.states.get(BACK_DOOR).state == STATE_ON

    _send(hass, 2, 999, "end")
    await hass.async_block_till_done()
    assert hass.states.get(BACK_DOOR).state == STATE_OFF


async def test_mqtt_ignores_monitors_that_do_not_analyse(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """ZoneMinder publishes a start for continuous events too."""
    _send(hass, 1, 999, "start")
    await hass.async_block_till_done()
    assert hass.states.get(DRIVEWAY).state == STATE_OFF


async def test_end_for_another_event_does_not_clear_motion(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Only the tracked event's end message ends it."""
    _send(hass, 2, 999, "start")
    await hass.async_block_till_done()
    assert hass.states.get(BACK_DOOR).state == STATE_ON

    _send(hass, 2, 111, "end")
    await hass.async_block_till_done()
    assert hass.states.get(BACK_DOOR).state == STATE_ON


async def test_lost_end_message_recovers(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A dropped end message used to pin the sensor on forever.

    The poll cannot correct a state that refuses to be corrected, so the MQTT
    override now expires and hands control back.
    """
    _send(hass, 2, 999, "start")
    await hass.async_block_till_done()
    assert hass.states.get(BACK_DOOR).state == STATE_ON

    # The "end" never arrives.
    freezer.tick(MQTT_MOTION_TIMEOUT + timedelta(minutes=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(BACK_DOOR).state == STATE_OFF


async def test_motion_attributes_describe_the_event(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The attributes point at the alarmed event, not the newest one."""
    attrs = hass.states.get(BACK_DOOR).attributes
    assert attrs["event_id"] == 298
    assert attrs["alarm_frames"] == 17
    assert attrs["cause"] == "Motion"


async def test_connectivity_sensor_reports_capture_state(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """A camera ZoneMinder cannot reach shows as disconnected."""
    assert hass.states.get("binary_sensor.driveway_camera_connection").state == STATE_ON
    assert hass.states.get("binary_sensor.gate_camera_connection").state == STATE_OFF


async def test_server_running_sensor(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The server device reports whether ZoneMinder is up."""
    state = hass.states.get("binary_sensor.zoneminder_test_running")
    assert state is not None
    assert state.state == STATE_ON
    assert state.attributes["daemons_running"] == 2


async def test_server_running_unknown_without_status(
    hass: HomeAssistant, config_entry: MockConfigEntry, zm_api: aioresponses
) -> None:
    """A user who may not read the server status sees unknown, not off.

    The daemon tally would read 0 of 0, so it is left out.
    """
    with patch(
        "aiozoneminder.client.v3.ZoneMinderV3Client.get_server_info",
        return_value=ServerInfo(version="1.38.0", running=None),
    ):
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.zoneminder_test_running")
    assert state is not None
    assert state.state == STATE_UNKNOWN
    assert "daemons_running" not in state.attributes
    assert "daemons_total" not in state.attributes
