"""Tests for the ZoneMinder entity platforms and services."""

from __future__ import annotations

from unittest.mock import patch

from aioresponses import aioresponses
from aiozoneminder import ZMApiError
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util.yaml import load_yaml
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zoneminder.const import DOMAIN

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
        pytest.raises(HomeAssistantError, match="locked"),
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
        pytest.raises(HomeAssistantError, match="permission"),
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


async def test_stream_waits_for_the_first_segment(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """A fresh live session is handed over only once it has video to play.

    Home Assistant's stream worker gives up on an empty playlist with
    "Stream has no video", which is what a just-started session serves.
    """
    from homeassistant.components.camera import async_get_stream_source

    from .conftest import _url, register_zm_api

    with aioresponses(passthrough=["http://127.0.0.1"]) as mocked:
        # Registered first, so these two answers are served before the
        # fixture's ready playlist.
        empty = "#EXTM3U\n#EXT-X-VERSION:6\n#EXT-X-TARGETDURATION:5\n"
        for _ in range(2):
            mocked.get(_url(r"api/v3/live/1/hls/live\.m3u8"), body=empty)
        register_zm_api(mocked)
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        with patch("aiozoneminder.client.v3._FIRST_SEGMENT_POLL", 0):
            source = await async_get_stream_source(hass, "camera.driveway")

        polls = [
            key
            for key in mocked.requests
            if str(key[1]).endswith("api/v3/live/1/hls/live.m3u8")
        ]
        assert source is not None
        assert len(mocked.requests[polls[0]]) == 3


async def test_stream_prefers_a_signed_rtsp_link(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """With RTSP on, cameras hand Home Assistant zm-api's signed link.

    The link is reused, not re-minted on every stream start.
    """
    from homeassistant.components.camera import async_get_stream_source

    from .conftest import _url, register_zm_api

    link = "rtsp://zm.example:8554/live/1?st=signed"
    with aioresponses(passthrough=["http://127.0.0.1"]) as mocked:
        mocked.post(
            _url(r"api/v3/live/1/rtsp/link"),
            payload={
                "url": link,
                "tls_url": None,
                "token": "signed",
                "expires_at": 4102444800,  # 2100-01-01
            },
            repeat=True,
        )
        register_zm_api(mocked)
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        first = await async_get_stream_source(hass, "camera.driveway")
        second = await async_get_stream_source(hass, "camera.driveway")

        mints = [
            calls
            for key, calls in mocked.requests.items()
            if key[0] == "POST" and str(key[1]).endswith("live/1/rtsp/link")
        ]

    assert first == second == link
    assert len(mints[0]) == 1


async def test_stream_falls_back_to_hls_when_rtsp_is_off(
    hass: HomeAssistant, setup_integration: MockConfigEntry, zm_api: aioresponses
) -> None:
    """A 503 from the link endpoint means HLS, and we don't keep asking."""
    from homeassistant.components.camera import async_get_stream_source

    first = await async_get_stream_source(hass, "camera.driveway")
    await async_get_stream_source(hass, "camera.driveway")

    assert first is not None
    assert first.endswith("api/v3/live/1/hls/master.m3u8")
    mints = [
        calls
        for key, calls in zm_api.requests.items()
        if key[0] == "POST" and "rtsp/link" in str(key[1])
    ]
    assert sum(len(calls) for calls in mints) == 1


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


def test_service_decoding_options_are_zoneminder_values() -> None:
    """The service's Decoding choices are the values of ZoneMinder's enum."""
    services = load_yaml("custom_components/zoneminder/services.yaml")
    field = services["set_monitor_state"]["fields"]["decoding"]
    assert field["selector"]["select"]["options"] == [
        "None",
        "Ondemand",
        "KeyFrames",
        "KeyFrames+Ondemand",
        "Always",
    ]


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


async def test_a_camera_that_never_recorded_reads_zero(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """zm-api has no summary for a monitor without events: that's 0, not unknown."""
    from .conftest import _url, register_zm_api

    with aioresponses(passthrough=["http://127.0.0.1"]) as mocked:
        mocked.get(_url(r"api/v3/event-summaries/3"), status=404, repeat=True)
        register_zm_api(mocked)
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get("sensor.gate_events_today").state == "0"
    assert hass.states.get("sensor.gate_recording_storage").state == "0.0"
    assert hass.states.get("sensor.driveway_events_today").state == "85"


async def test_continuous_chunks_are_not_motion(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """An analysing camera that also records continuously isn't always moving."""
    from homeassistant.helpers.dispatcher import async_dispatcher_send

    from custom_components.zoneminder.const import SIGNAL_MQTT_EVENT
    from custom_components.zoneminder.mqtt import ZoneMinderMQTTEvent

    async_dispatcher_send(
        hass,
        SIGNAL_MQTT_EVENT.format(2),
        ZoneMinderMQTTEvent(
            monitor_id=2, event_id=903, action="start", cause="Continuous"
        ),
    )
    await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.back_door_motion").state == "off"
    assert hass.states.get("event.back_door_event").attributes["event_type"] == (
        "recording"
    )


async def test_latest_event_image(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    zm_api: aioresponses,
    hass_client,
) -> None:
    """Each camera shows its latest event's picture; motion wins where analysed."""
    zm_api.get(
        f"{HOST}/api/v3/events/300/thumbnail",
        body=b"\xff\xd8driveway",
        content_type="image/jpeg",
        repeat=True,
    )
    driveway = hass.states.get("image.driveway_latest_event")
    assert driveway.attributes["event_id"] == 300
    # Back door analyses, so its latest *motion* (298) is shown.
    assert hass.states.get("image.back_door_latest_event").attributes["event_id"] == 298

    # A camera with no events has nothing to show yet.
    assert hass.states.get("image.gate_latest_event").state == "unavailable"

    client = await hass_client()
    response = await client.get(driveway.attributes["entity_picture"])
    assert response.status == 200
    assert await response.read() == b"\xff\xd8driveway"
