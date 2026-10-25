"""Tests for WebRTC straight from ZoneMinder (WHEP)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from aioresponses import CallbackResult, aioresponses
from homeassistant.components.camera.webrtc import WebRTCAnswer, WebRTCError
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from webrtc_models import RTCIceCandidateInit

from .conftest import _url, register_zm_api

OFFER = "v=0\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\na=recvonly\r\n"
ANSWER = "v=0\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\na=sendonly\r\n"
LOCATION = "/api/v3/live/1/webrtc/whep/abc123"


def _whep(url, **kwargs: Any) -> CallbackResult:
    """Answer like zm-api: 415 for the probe, an answer for a real offer."""
    if kwargs["headers"].get("Content-Type") != "application/sdp":
        return CallbackResult(status=415, body="not application/sdp")
    return CallbackResult(
        status=201,
        body=ANSWER,
        content_type="application/sdp",
        headers={"Location": LOCATION},
    )


async def _capabilities(hass: HomeAssistant, hass_ws_client, entity_id: str) -> set:
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "camera/capabilities", "entity_id": entity_id}
    )
    msg = await client.receive_json()
    return set(msg["result"]["frontend_stream_types"])


async def test_without_whep_nothing_changes(
    hass: HomeAssistant, setup_integration: MockConfigEntry, hass_ws_client
) -> None:
    """An older zm-api keeps HLS (and go2rtc, where it's installed)."""
    assert await _capabilities(hass, hass_ws_client, "camera.driveway") == {"hls"}


async def test_whep_adds_webrtc_and_keeps_hls(
    hass: HomeAssistant, config_entry: MockConfigEntry, hass_ws_client
) -> None:
    """WebRTC comes straight from zm-api; HLS stays as the fallback."""
    with aioresponses(passthrough=["http://127.0.0.1"]) as mocked:
        mocked.post(_url(r"api/v3/live/\d+/webrtc/whep"), callback=_whep, repeat=True)
        mocked.patch(_url(r"api/v3/live/1/webrtc/whep/abc123"), status=204, repeat=True)
        mocked.delete(
            _url(r"api/v3/live/1/webrtc/whep/abc123"), status=200, repeat=True
        )
        register_zm_api(mocked)
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        assert await _capabilities(hass, hass_ws_client, "camera.driveway") == {
            "hls",
            "web_rtc",
        }

        provider = config_entry.runtime_data.webrtc_provider
        sent: list = []
        camera = SimpleNamespace(monitor_id=1)
        await provider.async_handle_async_webrtc_offer(camera, OFFER, "s1", sent.append)
        assert sent == [WebRTCAnswer(ANSWER)]

        await provider.async_on_webrtc_candidate(
            "s1",
            RTCIceCandidateInit(
                "candidate:1 1 udp 1 10.0.0.2 5000 typ host", sdp_mid="0"
            ),
        )
        provider.async_close_session("s1")
        await hass.async_block_till_done()

        calls = {
            (method, str(url)): [c.kwargs.get("data") for c in requests]
            for (method, url), requests in mocked.requests.items()
        }

    patched = calls[("PATCH", f"http://192.168.0.45:8080{LOCATION}")]
    assert patched == [b"a=mid:0\r\na=candidate:1 1 udp 1 10.0.0.2 5000 typ host\r\n"]
    assert ("DELETE", f"http://192.168.0.45:8080{LOCATION}") in calls


async def test_whep_errors_reach_the_browser(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """A refused offer explains itself instead of hanging."""
    with aioresponses(passthrough=["http://127.0.0.1"]) as mocked:
        mocked.post(
            _url(r"api/v3/live/\d+/webrtc/whep"), status=406, body="codec", repeat=True
        )
        register_zm_api(mocked)
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        provider = config_entry.runtime_data.webrtc_provider
        sent: list = []
        await provider.async_handle_async_webrtc_offer(
            SimpleNamespace(monitor_id=1), OFFER, "s2", sent.append
        )

    assert isinstance(sent[0], WebRTCError)
    assert "codec" in sent[0].message


async def _provider_with_slow_answer(
    hass: HomeAssistant, config_entry: MockConfigEntry
):
    """Set up the entry and make zm-api's answer wait until released."""
    import asyncio
    from unittest.mock import AsyncMock

    with aioresponses(passthrough=["http://127.0.0.1"]) as mocked:
        register_zm_api(mocked)
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    provider = config_entry.runtime_data.webrtc_provider
    release = asyncio.Event()

    async def slow_offer(_monitor_id: int, _offer: str) -> tuple[str, str]:
        await release.wait()
        return ANSWER, LOCATION

    provider.api.async_whep_offer = slow_offer
    provider.api.async_whep_candidate = AsyncMock()
    provider.api.async_whep_close = AsyncMock()
    return provider, release


async def test_candidates_sent_during_the_offer_are_not_lost(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """The browser trickles candidates while zm-api is still answering the offer."""
    import asyncio

    provider, release = await _provider_with_slow_answer(hass, config_entry)
    sent: list = []
    offer = asyncio.create_task(
        provider.async_handle_async_webrtc_offer(
            SimpleNamespace(monitor_id=1), OFFER, "s3", sent.append
        )
    )
    await asyncio.sleep(0)
    candidate = RTCIceCandidateInit(
        "candidate:1 1 UDP 1 192.0.2.1 5000 typ host", sdp_mid="0"
    )
    await provider.async_on_webrtc_candidate("s3", candidate)
    release.set()
    await offer

    assert isinstance(sent[0], WebRTCAnswer)
    provider.api.async_whep_candidate.assert_awaited_once_with(
        LOCATION, "0", candidate.candidate
    )


async def test_closing_during_the_offer_ends_the_server_session(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """A viewer who leaves before the answer still has its zm-api session closed."""
    import asyncio

    provider, release = await _provider_with_slow_answer(hass, config_entry)
    sent: list = []
    offer = asyncio.create_task(
        provider.async_handle_async_webrtc_offer(
            SimpleNamespace(monitor_id=1), OFFER, "s4", sent.append
        )
    )
    await asyncio.sleep(0)
    provider.async_close_session("s4")
    release.set()
    await offer

    provider.api.async_whep_close.assert_awaited_once_with(LOCATION)
    assert sent == []
