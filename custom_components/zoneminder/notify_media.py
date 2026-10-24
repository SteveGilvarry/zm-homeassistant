# SPDX-License-Identifier: Apache-2.0
"""Signed links to one event's picture and clip, for phone notifications.

A notification leaves Home Assistant: it sits on a phone, in a notification
history, maybe in a screenshot. So each link opens exactly one event and
nothing else. The signature covers the entry and event id, the key lives in
the config entry so links keep working across restarts, and the general media
proxy's secret (which reaches every live stream) is never put in one.

    /api/zoneminder/event/{entry_id}/{event_id}/{signature}/thumbnail.jpg
    /api/zoneminder/event/{entry_id}/{event_id}/{signature}/clip.mp4
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from http import HTTPStatus
import secrets

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback

from .const import CONF_NOTIFY_KEY, DOMAIN
from .data import ZoneMinderConfigEntry
from .http import async_stream_upstream

EVENT_URL_BASE = f"/api/{DOMAIN}/event"
THUMBNAIL = "thumbnail.jpg"
CLIP = "clip.mp4"


def generate_notify_key() -> str:
    """Return a fresh signing key for an entry."""
    return secrets.token_urlsafe(32)


def _signature(key: str, entry_id: str, event_id: int) -> str:
    digest = hmac.new(
        key.encode(), f"{entry_id}/{event_id}".encode(), hashlib.sha256
    ).digest()
    return base64.urlsafe_b64encode(digest[:18]).decode()


@callback
def async_event_media_urls(
    entry: ZoneMinderConfigEntry, event_id: int
) -> dict[str, str]:
    """Return the notification links for one event."""
    key = entry.data.get(CONF_NOTIFY_KEY)
    if not key:
        return {}
    signature = _signature(key, entry.entry_id, event_id)
    base = f"{EVENT_URL_BASE}/{entry.entry_id}/{event_id}/{signature}"
    return {"thumbnail_url": f"{base}/{THUMBNAIL}", "clip_url": f"{base}/{CLIP}"}


class ZoneMinderEventMediaView(HomeAssistantView):
    """Serve one event's thumbnail or clip to a holder of its signed link."""

    url = EVENT_URL_BASE + "/{entry_id}/{event_id:\\d+}/{signature}/{name}"
    name = "api:zoneminder:event"
    # Phones fetch notification attachments without a Home Assistant session;
    # the per-event signature is the credential.
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def get(
        self,
        request: web.Request,
        entry_id: str,
        event_id: str,
        signature: str,
        name: str,
    ) -> web.StreamResponse:
        """Relay the requested media if the signature checks out."""
        entry = self.hass.config_entries.async_get_entry(entry_id)
        runtime = getattr(entry, "runtime_data", None)
        key = entry.data.get(CONF_NOTIFY_KEY) if entry else None
        if entry is None or entry.domain != DOMAIN or runtime is None or not key:
            return web.Response(status=HTTPStatus.NOT_FOUND)

        expected = _signature(key, entry_id, int(event_id))
        if not secrets.compare_digest(expected, signature):
            return web.Response(status=HTTPStatus.NOT_FOUND)

        api = runtime.coordinator.api
        if name == THUMBNAIL:
            path = api.get_event_thumbnail_path(int(event_id))
        elif name == CLIP:
            path = api.get_event_media_path(int(event_id))
        else:
            return web.Response(status=HTTPStatus.NOT_FOUND)
        if path is None:
            return web.Response(status=HTTPStatus.NOT_IMPLEMENTED)

        return await async_stream_upstream(request, runtime.coordinator, path)


@callback
def async_register_event_media(hass: HomeAssistant) -> None:
    """Register the view once per Home Assistant instance."""
    if hass.data.get(f"{DOMAIN}_event_media_registered"):
        return
    hass.http.register_view(ZoneMinderEventMediaView(hass))
    hass.data[f"{DOMAIN}_event_media_registered"] = True
