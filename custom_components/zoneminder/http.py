# SPDX-License-Identifier: Apache-2.0
"""An authenticating media proxy for ZoneMinder.

zm-api protects its HLS playlists, segments, event clips and thumbnails with a
bearer token. Neither Home Assistant's stream component (which shells out to
ffmpeg and only accepts three fixed options, none of them headers) nor a
browser ``<video>`` element can attach that token, and ffmpeg drops the query
string when it resolves relative segment URIs.

This view sits in between: Home Assistant fetches an unauthenticated proxy URL,
the proxy adds the bearer token upstream, and playlist bodies are rewritten so
that every URI they reference also points back through the proxy.
"""

from __future__ import annotations

from collections.abc import Callable
from http import HTTPStatus
import logging
import re
import secrets
from typing import TYPE_CHECKING
from urllib.parse import quote, unquote, urljoin

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .const import DOMAIN, PROXY_URL_BASE

if TYPE_CHECKING:
    from .coordinator import ZoneMinderDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

#: Upstream paths the proxy is willing to fetch. Anything else is refused, so a
#: leaked proxy URL cannot be turned into a general-purpose tunnel into zm-api
#: with the integration's credentials.
_ALLOWED_PATHS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^api/v3/live/\d+/hls/[A-Za-z0-9_.-]+$"),
    re.compile(r"^api/v3/events/\d+/(video|thumbnail)$"),
    re.compile(r"^api/v3/events/\d+/stream/[A-Za-z0-9_./-]+$"),
    re.compile(r"^api/v3/monitors/\d+/snapshot$"),
)

#: Response headers copied verbatim from upstream.
_PASSTHROUGH_HEADERS = (
    "Content-Type",
    "Content-Range",
    "Accept-Ranges",
    "Cache-Control",
    "Last-Modified",
    "ETag",
)

_PLAYLIST_TYPES = ("application/vnd.apple.mpegurl", "application/x-mpegurl")
_CHUNK = 64 * 1024

#: Matches the ``URI="..."`` attribute used by EXT-X-MAP and EXT-X-KEY.
_URI_ATTR = re.compile(r'URI="([^"]+)"')


def generate_proxy_secret() -> str:
    """Return a fresh per-entry secret for proxy URLs."""
    return secrets.token_urlsafe(32)


@callback
def async_proxy_path(entry_id: str, secret: str, upstream_path: str) -> str:
    """Return the Home Assistant path that proxies an upstream zm-api path."""
    return f"{PROXY_URL_BASE}/{entry_id}/{secret}/{quote(upstream_path)}"


@callback
def async_proxy_url(
    hass: HomeAssistant, entry_id: str, secret: str, upstream_path: str
) -> str | None:
    """Return an absolute proxy URL, for consumers outside the frontend.

    ffmpeg runs in Home Assistant's own process space but resolves the URL
    itself, so it needs a fully qualified address rather than a path.
    """
    path = async_proxy_path(entry_id, secret, upstream_path)
    try:
        base = get_url(hass, prefer_external=False, allow_ip=True)
    except NoURLAvailableError:
        _LOGGER.error(
            "No internal Home Assistant URL is configured, so ZoneMinder cannot "
            "build a stream URL. Set one under Settings > System > Network"
        )
        return None
    return f"{base}{path}"


class ZoneMinderMediaProxyView(HomeAssistantView):
    """Serve ZoneMinder media, adding credentials on the way upstream."""

    url = PROXY_URL_BASE + "/{entry_id}/{secret}/{upstream:.*}"
    name = "api:zoneminder:media"
    # ffmpeg and <video> elements cannot present a Home Assistant token, so the
    # per-entry secret in the path is what authorises the request.
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    def _coordinator(
        self, entry_id: str, secret: str
    ) -> ZoneMinderDataUpdateCoordinator | None:
        """Return the coordinator for an entry when the secret matches."""
        entry = self.hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            return None
        runtime = getattr(entry, "runtime_data", None)
        if runtime is None:
            return None
        if not secrets.compare_digest(runtime.proxy_secret, secret):
            return None
        return runtime.coordinator

    async def get(
        self, request: web.Request, entry_id: str, secret: str, upstream: str
    ) -> web.StreamResponse:
        """Proxy one media request upstream."""
        coordinator = self._coordinator(entry_id, secret)
        if coordinator is None:
            return web.Response(status=HTTPStatus.NOT_FOUND)

        upstream_path = unquote(upstream)
        if not any(pattern.match(upstream_path) for pattern in _ALLOWED_PATHS):
            _LOGGER.warning("Refusing to proxy disallowed path: %s", upstream_path)
            return web.Response(status=HTTPStatus.FORBIDDEN)

        return await async_stream_upstream(
            request,
            coordinator,
            upstream_path,
            rewrite=lambda body: _rewrite_playlist(
                body, upstream_path, entry_id, secret
            ),
        )


async def async_stream_upstream(
    request: web.Request,
    coordinator: ZoneMinderDataUpdateCoordinator,
    upstream_path: str,
    rewrite: Callable[[str], str] | None = None,
) -> web.StreamResponse:
    """Relay one authenticated upstream response to the client.

    Playlists are passed through ``rewrite`` so the URIs inside them can be
    pointed back at Home Assistant. Everything else streams as it arrives.
    """
    headers = {}
    if (range_header := request.headers.get("Range")) is not None:
        headers["Range"] = range_header

    try:
        async with coordinator.api.async_stream_media(
            upstream_path, headers
        ) as upstream_response:
            if upstream_response.status >= 400:
                _LOGGER.debug(
                    "Upstream returned %s for %s",
                    upstream_response.status,
                    upstream_path,
                )
                return web.Response(status=upstream_response.status)

            _LOGGER.debug(
                "Proxying %s (%s, %s)",
                upstream_path,
                upstream_response.status,
                upstream_response.content_type,
            )
            content_type = (upstream_response.content_type or "").lower()
            is_playlist = content_type in _PLAYLIST_TYPES or upstream_path.endswith(
                ".m3u8"
            )
            if is_playlist and rewrite is not None:
                body = await upstream_response.text()
                return web.Response(
                    body=rewrite(body).encode(),
                    status=upstream_response.status,
                    content_type="application/vnd.apple.mpegurl",
                )

            response = web.StreamResponse(
                status=upstream_response.status,
                headers={
                    name: value
                    for name in _PASSTHROUGH_HEADERS
                    if (value := upstream_response.headers.get(name))
                },
            )
            await response.prepare(request)
            async for chunk in upstream_response.content.iter_chunked(_CHUNK):
                await response.write(chunk)
            await response.write_eof()
            return response

    except (TimeoutError, ConnectionResetError):
        # The client hung up mid-stream, or upstream stalled. Nothing to say.
        return web.Response(status=HTTPStatus.GATEWAY_TIMEOUT)
    except Exception as err:  # noqa: BLE001 - never leak a traceback to the client
        _LOGGER.error("Proxying %s failed: %s", upstream_path, err)
        return web.Response(status=HTTPStatus.BAD_GATEWAY)


def _rewrite_playlist(body: str, upstream_path: str, entry_id: str, secret: str) -> str:
    """Point every URI in an HLS playlist back through the proxy.

    Playlist URIs are a mix of absolute paths (``/api/v3/live/1/hls/live.m3u8``)
    and names relative to the playlist (``segment_00000.m4s``). Both are
    resolved against the upstream playlist path before being re-emitted, so the
    whole chain stays authenticated.
    """
    base = f"http://zoneminder.invalid/{upstream_path}"

    def to_proxy(uri: str) -> str:
        if uri.startswith(("http://", "https://", "data:")):
            return uri
        resolved = urljoin(base, uri)
        target = resolved.split("http://zoneminder.invalid/", 1)[-1]
        return async_proxy_path(entry_id, secret, target)

    lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append(line)
        elif stripped.startswith("#"):
            lines.append(_URI_ATTR.sub(lambda m: f'URI="{to_proxy(m.group(1))}"', line))
        else:
            lines.append(to_proxy(stripped))
    return "\n".join(lines) + "\n"


@callback
def async_register_proxy(hass: HomeAssistant) -> None:
    """Register the media proxy view once per Home Assistant instance."""
    if hass.data.get(f"{DOMAIN}_proxy_registered"):
        return
    hass.http.register_view(ZoneMinderMediaProxyView(hass))
    hass.data[f"{DOMAIN}_proxy_registered"] = True
    _LOGGER.debug("ZoneMinder media proxy registered at %s", PROXY_URL_BASE)
