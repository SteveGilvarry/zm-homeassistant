"""Tests for the ZoneMinder media proxy."""

from __future__ import annotations

from http import HTTPStatus

from aioresponses import aioresponses
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.zoneminder.http import _rewrite_playlist, async_proxy_path

from .const import HOST

ENTRY = "abc123"
SECRET = "s3cret"

# The master playlist zm-api actually returns: a child playlist referenced by
# absolute path, which ffmpeg resolves without carrying the query string.
MASTER = (
    "#EXTM3U\n"
    "#EXT-X-VERSION:6\n"
    '#EXT-X-STREAM-INF:BANDWIDTH=5000000,CODECS="avc1.42e01e"\n'
    "/api/v3/live/1/hls/live.m3u8\n"
)

# The child playlist: an init segment in an attribute, then relative segments.
CHILD = (
    "#EXTM3U\n"
    "#EXT-X-TARGETDURATION:4\n"
    '#EXT-X-MAP:URI="init.mp4"\n'
    "#EXTINF:2.000,\n"
    "segment_00000.m4s\n"
    "#EXTINF:2.000,\n"
    "segment_00001.m4s\n"
)


def test_master_playlist_child_is_proxied() -> None:
    """An absolute child path must come back through the proxy, not to zm-api."""
    result = _rewrite_playlist(MASTER, "api/v3/live/1/hls/master.m3u8", ENTRY, SECRET)
    uris = [line for line in result.splitlines() if line and not line.startswith("#")]

    assert uris == [f"/api/zoneminder/{ENTRY}/{SECRET}/api/v3/live/1/hls/live.m3u8"]


def test_prefixed_paths_behind_a_proxy_are_proxied() -> None:
    """zm-api behind /zm (server.public_prefix) writes paths that carry the prefix.

    They must come back as the same api/v3 paths the proxy allows, not zm/api/v3
    (refused, so live video never started).
    """
    master = MASTER.replace(
        "/api/v3/live/1/hls/live.m3u8", "/zm/api/v3/live/1/hls/live.m3u8"
    )
    result = _rewrite_playlist(
        master, "api/v3/live/1/hls/master.m3u8", ENTRY, SECRET, base_path="/zm"
    )
    uris = [line for line in result.splitlines() if line and not line.startswith("#")]

    assert uris == [f"/api/zoneminder/{ENTRY}/{SECRET}/api/v3/live/1/hls/live.m3u8"]


def test_relative_segments_are_proxied() -> None:
    """Relative segment names resolve against the playlist, then get proxied."""
    result = _rewrite_playlist(CHILD, "api/v3/live/1/hls/live.m3u8", ENTRY, SECRET)
    base = f"/api/zoneminder/{ENTRY}/{SECRET}/api/v3/live/1/hls"

    assert f'#EXT-X-MAP:URI="{base}/init.mp4"' in result
    assert f"{base}/segment_00000.m4s" in result
    assert f"{base}/segment_00001.m4s" in result


def test_comments_and_blank_lines_survive() -> None:
    """Rewriting must not mangle the rest of the playlist."""
    result = _rewrite_playlist(CHILD, "api/v3/live/1/hls/live.m3u8", ENTRY, SECRET)
    assert result.startswith("#EXTM3U\n")
    assert "#EXT-X-TARGETDURATION:4" in result
    assert "#EXTINF:2.000," in result


def test_absolute_urls_are_left_alone() -> None:
    """A fully qualified URI is already reachable and should not be rewritten."""
    playlist = "#EXTM3U\nhttps://cdn.example/seg.m4s\n"
    result = _rewrite_playlist(playlist, "api/v3/live/1/hls/live.m3u8", ENTRY, SECRET)
    assert "https://cdn.example/seg.m4s" in result
    assert "/api/zoneminder" not in result


async def test_proxy_serves_media(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    hass_client: ClientSessionGenerator,
    zm_api: aioresponses,
) -> None:
    """A valid proxy URL returns the upstream body."""
    zm_api.get(
        f"{HOST}/api/v3/events/299/thumbnail",
        body=b"\xff\xd8jpeg-bytes",
        headers={"Content-Type": "image/jpeg"},
    )

    client = await hass_client()
    path = async_proxy_path(
        setup_integration.entry_id,
        setup_integration.runtime_data.proxy_secret,
        "api/v3/events/299/thumbnail",
    )
    response = await client.get(path)

    assert response.status == HTTPStatus.OK
    assert await response.read() == b"\xff\xd8jpeg-bytes"


async def test_proxy_rewrites_live_playlist(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    hass_client: ClientSessionGenerator,
    zm_api: aioresponses,
) -> None:
    """The live playlist is served rewritten, so segments stay authenticated."""
    zm_api.get(
        f"{HOST}/api/v3/live/1/hls/master.m3u8",
        body=MASTER,
        headers={"Content-Type": "application/vnd.apple.mpegurl"},
    )

    client = await hass_client()
    secret = setup_integration.runtime_data.proxy_secret
    response = await client.get(
        async_proxy_path(
            setup_integration.entry_id, secret, "api/v3/live/1/hls/master.m3u8"
        )
    )

    assert response.status == HTTPStatus.OK
    body = await response.text()
    assert f"/api/zoneminder/{setup_integration.entry_id}/{secret}/" in body


async def test_proxy_rejects_a_wrong_secret(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    hass_client: ClientSessionGenerator,
) -> None:
    """The secret is what authorises an unauthenticated request."""
    client = await hass_client()
    response = await client.get(
        async_proxy_path(
            setup_integration.entry_id, "not-the-secret", "api/v3/events/1/thumbnail"
        )
    )
    assert response.status == HTTPStatus.NOT_FOUND


async def test_proxy_refuses_paths_outside_the_allowlist(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    hass_client: ClientSessionGenerator,
) -> None:
    """A leaked URL must not become a tunnel into the rest of the API."""
    client = await hass_client()
    secret = setup_integration.runtime_data.proxy_secret

    for path in ("api/v3/users", "api/v3/configs", "api/v3/monitors/1"):
        response = await client.get(
            async_proxy_path(setup_integration.entry_id, secret, path)
        )
        assert response.status == HTTPStatus.FORBIDDEN, path
