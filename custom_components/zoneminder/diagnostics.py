# SPDX-License-Identifier: AGPL-3.0-or-later
"""Diagnostics for the ZoneMinder integration."""

from __future__ import annotations

from dataclasses import asdict
import re
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .data import ZoneMinderConfigEntry

#: Config entry keys never included in a diagnostics download.
REDACT_CONFIG = {CONF_USERNAME, CONF_PASSWORD}

#: ZoneMinder configuration keys that hold secrets.
REDACT_CONFIG_KEYS = re.compile(r"PASS|SECRET|KEY|TOKEN|CREDENTIAL|USER", re.IGNORECASE)

#: Credentials embedded in a source URL, for example an RTSP camera password.
_URL_CREDENTIALS = re.compile(r"(?<=://)[^/@\s]+:[^/@\s]+(?=@)")


def _scrub(value: Any) -> Any:
    """Strip embedded credentials from a monitor's source address."""
    if not isinstance(value, str):
        return value
    return _URL_CREDENTIALS.sub("**redacted**", value)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ZoneMinderConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data

    monitors = []
    for monitor in data.monitors.values():
        record = asdict(monitor)
        # Ffmpeg monitors keep the camera's RTSP URL, password and all, in
        # these fields.
        for field in ("host", "path", "protocol"):
            record[field] = _scrub(record.get(field))
        record["function"] = monitor.function
        record["orientation_label"] = monitor.orientation_label
        monitors.append(record)

    statuses = [asdict(status) for status in data.statuses.values()]
    summaries = [asdict(summary) for summary in data.summaries.values()]

    events = [
        {
            "id": event.id,
            "monitor_id": event.monitor_id,
            "cause": event.cause,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat() if event.end_time else None,
            "length": event.length,
            "frames": event.frames,
            "alarm_frames": event.alarm_frames,
            "is_alarm": event.is_alarm,
            "in_progress": event.in_progress,
        }
        for bucket in data.events.values()
        for event in bucket[:3]
    ]

    configs = {
        name: ("**redacted**" if REDACT_CONFIG_KEYS.search(name) else _scrub(value))
        for name, value in data.configs.items()
    }

    listener = entry.runtime_data.mqtt_listener

    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "data": async_redact_data(dict(entry.data), REDACT_CONFIG),
            "options": dict(entry.options),
        },
        "backend": coordinator.api.backend,
        "server": {
            **asdict(data.server),
            "storage": [asdict(area) for area in data.server.storage],
        },
        "coordinator": {
            "update_interval": str(coordinator.update_interval),
            "last_update_success": coordinator.last_update_success,
        },
        "mqtt": {
            "enabled": listener is not None,
            "topic": listener.topic if listener else None,
            "monitors_publishing": [
                monitor.id for monitor in data.monitors.values() if monitor.mqtt_enabled
            ],
        },
        "monitors": monitors,
        "monitor_status": statuses,
        "event_summaries": summaries,
        "recent_events": events,
        "zoneminder_config": configs,
    }
