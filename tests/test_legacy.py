"""Running against ZoneMinder's built-in API (API v2), as core users do."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
import re
from typing import Any

from aioresponses import aioresponses
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.zoneminder.const import (
    CONF_MQTT_ENABLED,
    CONF_STREAM_MAXFPS,
    CONF_STREAM_SCALE,
    DOMAIN,
)

ZM = "http://zm.local/zm"
ZMS = f"{ZM}/cgi-bin/nph-zms"
MJPEG = b"--ZoneMinderFrame\r\nContent-Type: image/jpeg\r\n\r\n\xff\xd8frame\r\n"


def _v2(path: str) -> re.Pattern[str]:
    return re.compile(rf"^{re.escape(ZM)}/{path}(\?.*)?$")


def _monitor(monitor_id: int, name: str) -> dict[str, Any]:
    return {
        "Monitor": {
            "Id": str(monitor_id),
            "Name": name,
            "Type": "Ffmpeg",
            "Width": "1920",
            "Height": "1080",
            "Capturing": "Always",
            "Analysing": "Always",
            "Recording": "OnMotion",
            "Controllable": "0",
            "ServerId": "0",
        },
        "Monitor_Status": {"MonitorId": str(monitor_id), "Status": "Connected"},
        "Event_Summary": {"MonitorId": str(monitor_id), "DayEvents": "4"},
    }


@pytest.fixture
def zm_v2() -> Generator[aioresponses]:
    """A stand-in ZoneMinder with no go2rtc, so cameras are MJPEG."""
    with aioresponses(passthrough=["http://127.0.0.1"]) as mocked:
        mocked.post(
            _v2(r"api/host/login\.json"), payload={"access_token": "tok"}, repeat=True
        )
        mocked.get(
            _v2(r"api/host/getVersion\.json"),
            payload={"version": "1.36.33"},
            repeat=True,
        )
        mocked.get(
            _v2(r"api/host/daemonCheck\.json"), payload={"result": 1}, repeat=True
        )
        mocked.get(
            _v2(r"api/monitors\.json"),
            payload={"monitors": [_monitor(1, "Driveway")]},
            repeat=True,
        )
        mocked.get(_v2(r"api/events.*\.json"), payload={"events": []}, repeat=True)
        mocked.get(_v2(r"api/configs\.json"), payload={"configs": []}, repeat=True)
        mocked.get(_v2(r"api/states\.json"), payload={"states": []}, repeat=True)
        # nph-zms: a 403 without a token marks where it lives.
        mocked.get(ZMS, status=403, repeat=True)
        mocked.get(
            re.compile(rf"^{re.escape(ZMS)}\?.*mode=single"),
            body=b"\xff\xd8still",
            repeat=True,
        )
        yield mocked


@pytest.fixture
async def setup_v2(
    hass: HomeAssistant, zm_v2: aioresponses
) -> AsyncGenerator[Callable[..., Awaitable[MockConfigEntry]]]:
    """Set up an API v2 entry with the given options; unload it afterwards."""
    entries: list[MockConfigEntry] = []

    async def _setup(**options: Any) -> MockConfigEntry:
        entry = MockConfigEntry(
            domain=DOMAIN,
            version=2,
            data={
                "backend": "legacy",
                "host": ZM,
                "username": "admin",
                "password": "hunter2",
                "verify_ssl": True,
            },
            options={CONF_MQTT_ENABLED: False, **options},
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        entries.append(entry)
        return entry

    yield _setup
    for entry in entries:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_mjpeg_cameras_stream_live(
    hass: HomeAssistant,
    zm_v2: aioresponses,
    setup_v2: Callable[..., Awaitable[MockConfigEntry]],
    hass_client: ClientSessionGenerator,
) -> None:
    """Without go2rtc, the live view is ZoneMinder's MJPEG, relayed by HA.

    Core's camera did this. The ZoneMinder token stays on the server side.
    """
    await setup_v2()
    zm_v2.get(
        re.compile(rf"^{re.escape(ZMS)}\?.*mode=jpeg.*token=tok"),
        body=MJPEG,
        content_type="multipart/x-mixed-replace;boundary=ZoneMinderFrame",
    )

    client = await hass_client()
    response = await client.get("/api/camera_proxy_stream/camera.driveway")
    assert response.status == 200
    assert response.content_type == "multipart/x-mixed-replace"
    assert await response.read() == MJPEG


async def test_stream_options_reach_the_mjpeg_url(
    setup_v2: Callable[..., Awaitable[MockConfigEntry]],
) -> None:
    entry = await setup_v2(**{CONF_STREAM_SCALE: 50, CONF_STREAM_MAXFPS: 5})
    url = entry.runtime_data.coordinator.api.get_stream_url(1)
    assert "scale=50" in url
    assert "maxfps=5" in url


async def test_api_v2_health_and_counts(
    hass: HomeAssistant, setup_v2: Callable[..., Awaitable[MockConfigEntry]]
) -> None:
    """Connectivity and event counts come from API v2's monitor list now."""
    await setup_v2()
    assert hass.states.get("binary_sensor.driveway_camera_connection").state == "on"
    assert hass.states.get("sensor.driveway_events_past_day").state == "4"
