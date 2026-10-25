# SPDX-License-Identifier: Apache-2.0
"""Config entry migrations.

Version 2 exists to adopt entries made by nabbi/ha-zoneminder, a config flow
fork of the core integration, which uses the same domain. Its entries store
a bare host (no scheme), name entities after the host, and speak only
ZoneMinder's built-in API.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from aiozoneminder.const import BACKEND_LEGACY
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import (
    CONF_BACKEND,
    CONF_EVENT_PERIODS,
    CONF_FUNCTION_OFF,
    CONF_FUNCTION_ON,
    CONF_INCLUDE_ARCHIVED,
    CONF_MQTT_ENABLED,
    CONF_STREAM_MAXFPS,
    CONF_STREAM_SCALE,
    CONF_VERIFY_SSL,
    CONF_ZMS_PATH,
    DOMAIN,
)
from .data import ZoneMinderConfigEntry

_LOGGER = logging.getLogger(__name__)

CURRENT_VERSION = 2
CURRENT_MINOR_VERSION = 2

#: nabbi's option names, and ours.
_OPTIONS = {
    "include_archived": CONF_INCLUDE_ARCHIVED,
    "monitored_conditions": CONF_EVENT_PERIODS,
    "command_on": CONF_FUNCTION_ON,
    "command_off": CONF_FUNCTION_OFF,
    "stream_scale": CONF_STREAM_SCALE,
    "stream_maxfps": CONF_STREAM_MAXFPS,
}

#: nabbi's per-monitor unique id suffixes, and our entity keys. His events
#: sensors are keyed by period.
_MONITOR_KEYS = {
    "": "camera",
    "status": "mode",
    "capturing": "capturing",
    "analysing": "analysing",
    "recording": "recording",
    "switch": "function",
    "events_all": "events_total",
    "events_hour": "events_hour",
    "events_day": "events_today",
    "events_week": "events_week",
    "events_month": "events_month",
}
_SERVER_KEYS = {"run_state_select": "run_state", "availability": "running"}


def is_nabbi_entry(data: dict[str, Any]) -> bool:
    """Whether entry data came from nabbi's integration: a host with no scheme."""
    return "://" not in str(data.get(CONF_HOST, "")) and CONF_BACKEND not in data


async def async_migrate(hass: HomeAssistant, entry: ZoneMinderConfigEntry) -> bool:
    """Bring an entry up to the current version."""
    if entry.version > CURRENT_VERSION:
        return False
    if entry.version == 1 and is_nabbi_entry(dict(entry.data)):
        _adopt_nabbi_entry(hass, entry)
    if (entry.version, entry.minor_version) < (CURRENT_VERSION, CURRENT_MINOR_VERSION):
        # Earlier versions used the server URL (or nabbi's bare host) as the
        # unique id, which Home Assistant doesn't allow. Duplicates are
        # caught by address in the config flow instead.
        hass.config_entries.async_update_entry(entry, unique_id=None)
    hass.config_entries.async_update_entry(
        entry, version=CURRENT_VERSION, minor_version=CURRENT_MINOR_VERSION
    )
    return True


@callback
def _adopt_nabbi_entry(hass: HomeAssistant, entry: ZoneMinderConfigEntry) -> None:
    """Rewrite a nabbi entry, and its entities and devices, into our shape."""
    old = dict(entry.data)
    old_host = str(old[CONF_HOST])
    scheme = "https" if old.get("ssl") else "http"
    path = "/" + str(old.get("path") or "/zm/").strip("/")
    host = f"{scheme}://{old_host}{path}".rstrip("/")

    data: dict[str, Any] = {
        CONF_BACKEND: BACKEND_LEGACY,
        CONF_HOST: host,
        CONF_USERNAME: old.get(CONF_USERNAME) or "",
        CONF_PASSWORD: old.get(CONF_PASSWORD) or "",
        CONF_VERIFY_SSL: old.get(CONF_VERIFY_SSL, True),
    }
    if zms_path := old.get(CONF_ZMS_PATH):
        data[CONF_ZMS_PATH] = zms_path

    # ha-zoneminder left archived events out of its counts unless asked.
    options: dict[str, Any] = {CONF_MQTT_ENABLED: True, CONF_INCLUDE_ARCHIVED: False}
    for theirs, ours in _OPTIONS.items():
        if entry.options.get(theirs) not in (None, ""):
            options[ours] = entry.options[theirs]

    _move_entities(hass, entry, old_host)
    _move_devices(hass, entry, old_host)
    hass.config_entries.async_update_entry(entry, data=data, options=options)
    _LOGGER.info("Adopted the ha-zoneminder entry for %s as %s", old_host, host)


@callback
def _move_entities(
    hass: HomeAssistant, entry: ZoneMinderConfigEntry, old_host: str
) -> None:
    """Give the old entities our unique ids, so their entity ids carry on."""
    registry = er.async_get(hass)
    monitor = re.compile(rf"^{re.escape(old_host)}_(\d+)(?:_(.+))?$")
    server = re.compile(rf"^{re.escape(old_host)}_(.+)$")
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        new_id: str | None = None
        if match := monitor.match(entity.unique_id):
            key = _MONITOR_KEYS.get(match.group(2) or "")
            if key:
                new_id = f"{entry.entry_id}_{match.group(1)}_{key}"
        elif (match := server.match(entity.unique_id)) and (
            key := _SERVER_KEYS.get(match.group(1))
        ):
            new_id = f"{entry.entry_id}_server_{key}"
        if new_id is None:
            _LOGGER.debug("No replacement for %s, leaving it", entity.entity_id)
            continue
        registry.async_update_entity(entity.entity_id, new_unique_id=new_id)


@callback
def _move_devices(
    hass: HomeAssistant, entry: ZoneMinderConfigEntry, old_host: str
) -> None:
    """Re-key the server and camera devices to our identifiers."""
    registry = dr.async_get(hass)
    camera = re.compile(rf"^{re.escape(old_host)}_(\d+)$")
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        identifiers = set()
        for domain, identifier in device.identifiers:
            if domain == DOMAIN and identifier == old_host:
                identifier = entry.entry_id
            elif domain == DOMAIN and (match := camera.match(identifier)):
                identifier = f"{entry.entry_id}_{match.group(1)}"
            identifiers.add((domain, identifier))
        if identifiers != device.identifiers:
            registry.async_update_device(device.id, new_identifiers=identifiers)
