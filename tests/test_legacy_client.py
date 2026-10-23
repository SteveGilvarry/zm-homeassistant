"""Tests for the built-in ZoneMinder API client."""

from __future__ import annotations

from aioresponses import aioresponses
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import pytest

from custom_components.zoneminder.client.legacy import ZoneMinderLegacyClient
from custom_components.zoneminder.const import STREAM_TYPE_GO2RTC, STREAM_TYPE_MJPEG
from custom_components.zoneminder.exceptions import (
    ZMAuthenticationError,
    ZMConnectionError,
)

ZM = "http://zm.local/zm"
GO2RTC = "http://192.168.0.45:1984/api"

# The stream names a real ZoneMinder go2rtc instance advertises. They are not
# plain monitor ids, which is what the old guess-the-name code assumed.
GO2RTC_STREAMS = {
    "1_0": {},
    "1_1": {},
    "2_0": {},
    "3": {},
    "3_ZoneMinderPrimary": {},
    "3_h264": {},
    "4_0": {},
}

CONFIGS_RESPONSE = {
    "configs": [
        {"Config": {"Name": "ZM_GO2RTC_PATH", "Value": GO2RTC}},
        {"Config": {"Name": "ZM_MQTT_TOPIC_PREFIX", "Value": "ZoneMinder"}},
    ]
}


def make_client(hass: HomeAssistant) -> ZoneMinderLegacyClient:
    """Return a legacy client pointed at a stand-in ZoneMinder."""
    return ZoneMinderLegacyClient(ZM, "admin", "hunter2", async_get_clientsession(hass))
    """Return a legacy client pointed at a stand-in ZoneMinder."""
    return ZoneMinderLegacyClient(ZM, "admin", "hunter2", async_get_clientsession(hass))


def _login(mocked: aioresponses) -> None:
    """Register a successful login."""
    mocked.post(
        f"{ZM}/api/host/login.json",
        payload={"access_token": "token"},
        repeat=True,
    )


async def test_authenticate(hass: HomeAssistant) -> None:
    """A successful login stores the token."""
    client = make_client(hass)
    with aioresponses() as mocked:
        _login(mocked)
        assert await client.authenticate() is True
    assert client.authenticated is True


async def test_bad_credentials(hass: HomeAssistant) -> None:
    """A rejected login raises so the entry can start re-authentication."""
    client = make_client(hass)
    with aioresponses() as mocked:
        mocked.post(f"{ZM}/api/host/login.json", status=401)
        with pytest.raises(ZMAuthenticationError):
            await client.authenticate()


async def test_missing_api_explains_itself(hass: HomeAssistant) -> None:
    """A 404 on login usually means the URL is missing the /zm path."""
    client = make_client(hass)
    with aioresponses() as mocked:
        mocked.post(f"{ZM}/api/host/login.json", status=404)
        with pytest.raises(ZMConnectionError, match="OPT_USE_API"):
            await client.authenticate()


async def test_go2rtc_config_is_read_from_the_right_path(hass: HomeAssistant) -> None:
    """The config endpoint sits at api/configs.json, not zm/api/configs.json.

    The old path produced http://host/zm/zm/api/configs.json, whose 404 was
    swallowed, so go2rtc was never detected and every camera silently fell
    back to MJPEG.
    """
    client = make_client(hass)
    with aioresponses() as mocked:
        _login(mocked)
        mocked.get(f"{ZM}/api/configs.json?token=token", payload=CONFIGS_RESPONSE)
        mocked.get(f"{GO2RTC}/streams", payload=GO2RTC_STREAMS)
        mocked.get(GO2RTC, payload={"rtsp": {"listen": ":8554"}})

        config = await client.check_go2rtc()

    assert config is not None
    assert config["base_url"] == "http://192.168.0.45:1984"
    assert config["rtsp_port"] == 8554


async def test_go2rtc_stream_names_are_discovered(hass: HomeAssistant) -> None:
    """Stream names are matched against the real list, not guessed."""
    client = make_client(hass)
    with aioresponses() as mocked:
        _login(mocked)
        mocked.get(f"{ZM}/api/configs.json?token=token", payload=CONFIGS_RESPONSE)
        mocked.get(f"{GO2RTC}/streams", payload=GO2RTC_STREAMS)
        mocked.get(GO2RTC, payload={"rtsp": {"listen": ":8554"}})

        # Monitor 3 is published under its bare id, the others under _0.
        assert await client.get_stream_source(3) == "rtsp://192.168.0.45:8554/3"
        assert await client.get_stream_source(1) == "rtsp://192.168.0.45:8554/1_0"
        assert client.get_stream_type(1) == STREAM_TYPE_GO2RTC


async def test_falls_back_to_mjpeg_when_rtsp_is_off(hass: HomeAssistant) -> None:
    """go2rtc ships with its RTSP server disabled in some packages.

    Handing Home Assistant an rtsp:// URL nothing is listening on produces a
    camera that never loads, so an unusable RTSP port means MJPEG instead.
    """
    client = make_client(hass)
    with aioresponses() as mocked:
        _login(mocked)
        mocked.get(f"{ZM}/api/configs.json?token=token", payload=CONFIGS_RESPONSE)
        mocked.get(f"{GO2RTC}/streams", payload=GO2RTC_STREAMS)
        # An empty listen address means no RTSP server is running.
        mocked.get(GO2RTC, payload={"rtsp": {"listen": ""}})

        source = await client.get_stream_source(1)

    assert source.startswith(f"{ZM}/cgi-bin/nph-zms")
    assert client.get_stream_type(1) == STREAM_TYPE_MJPEG


async def test_no_go2rtc_configured(hass: HomeAssistant) -> None:
    """Without ZM_GO2RTC_PATH there is nothing to discover."""
    client = make_client(hass)
    with aioresponses() as mocked:
        _login(mocked)
        mocked.get(f"{ZM}/api/configs.json?token=token", payload={"configs": []})
        assert await client.check_go2rtc() is None
        assert await client.get_stream_source(1) is not None


async def test_set_monitor_state_writes_both_shapes(hass: HomeAssistant) -> None:
    """1.36 wants Function, 1.37+ wants the split fields, so send both."""
    client = make_client(hass)
    posted: dict[str, str] = {}

    def _capture(url, **kwargs):
        posted.update(kwargs.get("data") or {})
        from aioresponses import CallbackResult

        return CallbackResult(payload={})

    with aioresponses() as mocked:
        _login(mocked)
        mocked.get(
            f"{ZM}/api/monitors/1.json?token=token",
            payload={
                "monitor": {
                    "Monitor": {
                        "Id": "1",
                        "Name": "Driveway",
                        "Function": "Monitor",
                        "Type": "Ffmpeg",
                        "Width": "1920",
                        "Height": "1080",
                    }
                }
            },
        )
        mocked.post(f"{ZM}/api/monitors/1.json?token=token", callback=_capture)

        await client.set_monitor_state(1, analysing="Always", recording="Always")

    assert posted["Monitor[Analysing]"] == "Always"
    assert posted["Monitor[Recording]"] == "Always"
    # Capturing was left alone, so it keeps the monitor's current value.
    assert posted["Monitor[Capturing]"] == "Always"
    assert posted["Monitor[Function]"] == "Mocord"


async def test_reauthenticates_once_on_401(hass: HomeAssistant) -> None:
    """An expired token is refreshed and the request retried."""
    client = make_client(hass)
    with aioresponses() as mocked:
        _login(mocked)
        mocked.get(f"{ZM}/api/host/getVersion.json?token=token", status=401)
        mocked.get(
            f"{ZM}/api/host/getVersion.json?token=token",
            payload={"version": "1.36.33"},
        )
        assert await client.get_version() == "1.36.33"
