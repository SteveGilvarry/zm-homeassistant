# SPDX-License-Identifier: AGPL-3.0-or-later
"""Websocket commands for the ZoneMinder card.

The card draws a camera's day as a strip of events and plays a clip when one
is picked. It needs the raw numbers (start, length, alarm score), which the
media browser only offers as display strings, so they are served here.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from aiozoneminder import ZMError
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util
import voluptuous as vol

from .const import DOMAIN
from .http import async_proxy_path
from .services import _monitor_id_from_device

#: The longest window the card may ask for in one go.
MAX_HOURS = 7 * 24


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    """Register the websocket commands once per Home Assistant instance."""
    if hass.data.get(f"{DOMAIN}_ws_registered"):
        return
    websocket_api.async_register_command(hass, ws_events)
    hass.data[f"{DOMAIN}_ws_registered"] = True


@websocket_api.websocket_command(
    {
        vol.Required("type"): "zoneminder/events",
        vol.Required("entity_id"): str,
        vol.Optional("hours", default=24): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=MAX_HOURS)
        ),
    }
)
@websocket_api.async_response
async def ws_events(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return one camera's events for the last few hours, oldest first."""
    entity = er.async_get(hass).async_get(msg["entity_id"])
    if entity is None or entity.platform != DOMAIN or entity.device_id is None:
        connection.send_error(
            msg["id"], "not_found", f"{msg['entity_id']} is not a ZoneMinder camera"
        )
        return

    entry = hass.config_entries.async_get_entry(entity.config_entry_id or "")
    runtime = getattr(entry, "runtime_data", None)
    device = dr.async_get(hass).async_get(entity.device_id)
    monitor_id = _monitor_id_from_device(entry, device) if entry and device else None
    if runtime is None or monitor_id is None:
        connection.send_error(
            msg["id"], "not_ready", "That ZoneMinder server is not loaded"
        )
        return

    end = dt_util.utcnow()
    start = end - timedelta(hours=msg["hours"])
    api = runtime.coordinator.api
    try:
        events = await api.get_events_between(monitor_id, start, end)
    except ZMError as err:
        connection.send_error(msg["id"], "zoneminder_error", str(err))
        return

    secret = runtime.proxy_secret

    def proxied(path: str | None) -> str | None:
        return async_proxy_path(entry.entry_id, secret, path) if path else None

    connection.send_result(
        msg["id"],
        {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "events": [
                {
                    "id": event.id,
                    "start": event.start_time.isoformat(),
                    "end": event.end_time.isoformat() if event.end_time else None,
                    "length": event.length,
                    "cause": event.cause,
                    "notes": event.notes,
                    "alarm_frames": event.alarm_frames,
                    "max_score": event.max_score,
                    "in_progress": event.in_progress,
                    "thumbnail": proxied(api.get_event_thumbnail_path(event.id)),
                    "video": proxied(api.get_event_media_path(event.id))
                    if event.has_video
                    else None,
                }
                for event in sorted(events, key=lambda e: e.start_time)
            ],
        },
    )
