"""Tests for the ZoneMinder entity platforms and services."""

from __future__ import annotations

from unittest.mock import patch

from aioresponses import aioresponses
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zoneminder.const import DOMAIN
from custom_components.zoneminder.exceptions import ZMApiError

from .const import HOST


async def test_selects_show_the_real_state_fields(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """ZoneMinder 1.37 split Function into three, so we expose three."""
    assert hass.states.get("select.driveway_capturing").state == "Always"
    assert hass.states.get("select.driveway_analysing").state == "None"
    assert hass.states.get("select.driveway_recording").state == "Always"

    options = hass.states.get("select.driveway_recording").attributes["options"]
    assert options == ["None", "OnMotion", "Always"]


async def test_select_sends_a_patch(
    hass: HomeAssistant, setup_integration: MockConfigEntry, zm_api: aioresponses
) -> None:
    """Choosing a mode patches the monitor."""
    zm_api.patch(f"{HOST}/api/v3/monitors/1", payload={}, repeat=True)

    await hass.services.async_call(
        "select",
        "select_option",
        {ATTR_ENTITY_ID: "select.driveway_analysing", "option": "Always"},
        blocking=True,
    )

    requests = [str(url) for (method, url) in zm_api.requests if method == "PATCH"]
    assert f"{HOST}/api/v3/monitors/1" in requests


async def test_select_surfaces_failures(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """A rejected change must not look like it worked.

    The client used to swallow the error and return False, so the UI showed a
    mode ZoneMinder had refused.
    """
    with (
        patch.object(
            setup_integration.runtime_data.coordinator.api,
            "set_monitor_state",
            side_effect=ZMApiError("monitor is locked"),
        ),
        pytest.raises(ZMApiError, match="locked"),
    ):
        await hass.services.async_call(
            "select",
            "select_option",
            {ATTR_ENTITY_ID: "select.driveway_analysing", "option": "Always"},
            blocking=True,
        )


async def test_button_surfaces_failures(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """A failed alarm trigger raises instead of logging quietly."""
    with (
        patch.object(
            setup_integration.runtime_data.coordinator.api,
            "trigger_alarm",
            side_effect=ZMApiError("no permission"),
        ),
        pytest.raises(ZMApiError, match="permission"),
    ):
        await hass.services.async_call(
            "button",
            "press",
            {ATTR_ENTITY_ID: "button.driveway_trigger_alarm"},
            blocking=True,
        )


async def test_camera_stream_goes_through_the_proxy(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Live video is fetched through Home Assistant so it can be authenticated."""
    from homeassistant.components.camera import async_get_stream_source

    source = await async_get_stream_source(hass, "camera.driveway")

    assert source is not None
    assert f"/api/zoneminder/{setup_integration.entry_id}/" in source
    assert source.endswith("api/v3/live/1/hls/master.m3u8")


async def test_camera_attributes(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Cards get the orientation and signalling details they need."""
    attrs = hass.states.get("camera.gate").attributes

    assert attrs["orientation"] == "Rotate right"
    assert attrs["orientation_degrees"] == 90
    assert attrs["stream_type"] == "hls"
    assert attrs["controllable"] is True
    assert attrs["webrtc_signaling_url"] == (
        "ws://192.168.0.45:8080/api/v3/live/3/webrtc/ws"
    )


async def test_sensors_report_server_and_monitor_health(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The NVR-level numbers are exposed, not just per-camera ones."""
    assert hass.states.get("sensor.driveway_capture_rate").state == "10.94"
    assert hass.states.get("sensor.driveway_events_today").state == "85"
    assert hass.states.get("sensor.zoneminder_test_version").state == "1.39.22"
    assert hass.states.get("sensor.zoneminder_test_monitors").state == "3"


async def test_service_requires_a_target(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Calling a service with nothing selected explains itself."""
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "trigger_event", {ATTR_ENTITY_ID: []}, blocking=True
        )


async def test_ptz_service_targets_a_monitor(
    hass: HomeAssistant, setup_integration: MockConfigEntry, zm_api: aioresponses
) -> None:
    """The ptz service resolves a camera entity to its monitor."""
    zm_api.post(f"{HOST}/api/v3/ptz/monitors/3/move/left", payload={}, repeat=True)

    await hass.services.async_call(
        DOMAIN,
        "ptz",
        {ATTR_ENTITY_ID: "camera.gate", "command": "left"},
        blocking=True,
    )

    posted = [str(url) for (method, url) in zm_api.requests if method == "POST"]
    assert f"{HOST}/api/v3/ptz/monitors/3/move/left" in posted


async def test_ptz_preset_requires_a_number(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Asking for a preset without saying which one is a user error."""
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "ptz",
            {ATTR_ENTITY_ID: "camera.gate", "command": "preset"},
            blocking=True,
        )


async def test_set_monitor_state_service(
    hass: HomeAssistant, setup_integration: MockConfigEntry, zm_api: aioresponses
) -> None:
    """The service can change several state fields at once."""
    zm_api.patch(f"{HOST}/api/v3/monitors/1", payload={}, repeat=True)

    await hass.services.async_call(
        DOMAIN,
        "set_monitor_state",
        {
            ATTR_ENTITY_ID: "camera.driveway",
            "analysing": "Always",
            "recording": "OnMotion",
        },
        blocking=True,
    )

    patched = [str(url) for (method, url) in zm_api.requests if method == "PATCH"]
    assert f"{HOST}/api/v3/monitors/1" in patched


async def test_event_entity_fires_on_mqtt(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The event entity distinguishes motion from plain recording."""
    from homeassistant.helpers.dispatcher import async_dispatcher_send

    from custom_components.zoneminder.const import SIGNAL_MQTT_EVENT
    from custom_components.zoneminder.mqtt import ZoneMinderMQTTEvent

    async_dispatcher_send(
        hass,
        SIGNAL_MQTT_EVENT.format(2),
        ZoneMinderMQTTEvent(
            monitor_id=2, event_id=901, action="start", labels=["person"]
        ),
    )
    await hass.async_block_till_done()

    state = hass.states.get("event.back_door_event")
    assert state.attributes["event_type"] == "motion"
    assert state.attributes["event_id"] == 901
    assert state.attributes["detected_objects"] == ["person"]

    # Monitor 1 does not analyse, so its events are recordings, not motion.
    async_dispatcher_send(
        hass,
        SIGNAL_MQTT_EVENT.format(1),
        ZoneMinderMQTTEvent(monitor_id=1, event_id=902, action="start"),
    )
    await hass.async_block_till_done()
    assert hass.states.get("event.driveway_event").attributes["event_type"] == (
        "recording"
    )


async def test_diagnostics_redact_secrets(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """A diagnostics download must not leak camera or MQTT passwords."""
    from custom_components.zoneminder.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)
    dumped = str(diagnostics)

    assert "hunter2" not in dumped
    assert "topsecret" not in dumped
    # The camera's RTSP password from the monitor fixture.
    assert "admin:secret@" not in dumped
    assert "**redacted**" in dumped
    assert diagnostics["server"]["version"] == "1.39.22"
