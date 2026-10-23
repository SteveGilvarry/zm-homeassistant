# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration-level services for ZoneMinder."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.const import ATTR_DEVICE_ID, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
import voluptuous as vol

from .const import (
    ANALYSING_OPTIONS,
    CAPTURING_OPTIONS,
    DECODING_OPTIONS,
    DOMAIN,
    PTZ_COMMANDS,
    RECORDING_OPTIONS,
    SERVICE_CANCEL_EVENT,
    SERVICE_PTZ,
    SERVICE_SET_MONITOR_STATE,
    SERVICE_TRIGGER_EVENT,
)
from .coordinator import ZoneMinderDataUpdateCoordinator
from .data import ZoneMinderConfigEntry

_LOGGER = logging.getLogger(__name__)

ATTR_CAUSE = "cause"
ATTR_COMMAND = "command"
ATTR_PRESET = "preset"
ATTR_CAPTURING = "capturing"
ATTR_ANALYSING = "analysing"
ATTR_RECORDING = "recording"
ATTR_DECODING = "decoding"

_TARGET_SCHEMA = {
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
}

_TRIGGER_EVENT_SCHEMA = vol.Schema(
    {
        **_TARGET_SCHEMA,
        vol.Optional(ATTR_CAUSE, default="Home Assistant"): cv.string,
    }
)

_CANCEL_EVENT_SCHEMA = vol.Schema(_TARGET_SCHEMA)

_PTZ_SCHEMA = vol.Schema(
    {
        **_TARGET_SCHEMA,
        vol.Required(ATTR_COMMAND): vol.In(PTZ_COMMANDS),
        vol.Optional(ATTR_PRESET): vol.All(vol.Coerce(int), vol.Range(min=1, max=255)),
    }
)

_SET_STATE_SCHEMA = vol.Schema(
    vol.All(
        {
            **_TARGET_SCHEMA,
            vol.Optional(ATTR_CAPTURING): vol.In(CAPTURING_OPTIONS),
            vol.Optional(ATTR_ANALYSING): vol.In(ANALYSING_OPTIONS),
            vol.Optional(ATTR_RECORDING): vol.In(RECORDING_OPTIONS),
            vol.Optional(ATTR_DECODING): vol.In(DECODING_OPTIONS),
        },
        cv.has_at_least_one_key(
            ATTR_CAPTURING, ATTR_ANALYSING, ATTR_RECORDING, ATTR_DECODING
        ),
    )
)


@dataclass(frozen=True)
class MonitorTarget:
    """One monitor a service call applies to."""

    coordinator: ZoneMinderDataUpdateCoordinator
    monitor_id: int


@callback
def _resolve_targets(hass: HomeAssistant, call: ServiceCall) -> list[MonitorTarget]:
    """Map the entities and devices a call targets to ZoneMinder monitors."""
    device_reg = dr.async_get(hass)
    entity_reg = er.async_get(hass)

    device_ids: set[str] = set(call.data.get(ATTR_DEVICE_ID) or [])
    for entity_id in call.data.get(ATTR_ENTITY_ID) or []:
        entity = entity_reg.async_get(entity_id)
        if entity is None or entity.platform != DOMAIN:
            _LOGGER.warning("Ignoring non-ZoneMinder entity %s", entity_id)
            continue
        if entity.device_id:
            device_ids.add(entity.device_id)

    targets: list[MonitorTarget] = []
    seen: set[tuple[str, int]] = set()

    for device_id in device_ids:
        device = device_reg.async_get(device_id)
        if device is None:
            continue
        for entry_id in device.config_entries:
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry is None or entry.domain != DOMAIN:
                continue
            runtime = getattr(entry, "runtime_data", None)
            if runtime is None:
                continue
            monitor_id = _monitor_id_from_device(entry, device)
            if monitor_id is None:
                continue
            key = (entry_id, monitor_id)
            if key in seen:
                continue
            seen.add(key)
            targets.append(MonitorTarget(runtime.coordinator, monitor_id))

    return targets


@callback
def _monitor_id_from_device(
    entry: ZoneMinderConfigEntry, device: dr.DeviceEntry
) -> int | None:
    """Extract a monitor id from a device's registry identifiers."""
    prefix = f"{entry.entry_id}_"
    for domain, identifier in device.identifiers:
        if domain != DOMAIN or not identifier.startswith(prefix):
            continue
        suffix = identifier[len(prefix) :]
        if suffix.isdigit():
            return int(suffix)
    return None


def _require_targets(hass: HomeAssistant, call: ServiceCall) -> list[MonitorTarget]:
    """Resolve targets, or explain why the call cannot run."""
    targets = _resolve_targets(hass, call)
    if not targets:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="no_targets"
        )
    return targets


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the ZoneMinder services once per Home Assistant instance."""
    if hass.services.has_service(DOMAIN, SERVICE_TRIGGER_EVENT):
        return

    async def _trigger_event(call: ServiceCall) -> None:
        cause = call.data[ATTR_CAUSE]
        for target in _require_targets(hass, call):
            await target.coordinator.async_trigger_alarm(target.monitor_id, cause)

    async def _cancel_event(call: ServiceCall) -> None:
        for target in _require_targets(hass, call):
            await target.coordinator.async_cancel_alarm(target.monitor_id)

    async def _ptz(call: ServiceCall) -> None:
        command = call.data[ATTR_COMMAND]
        kwargs = {}
        if (preset := call.data.get(ATTR_PRESET)) is not None:
            kwargs["preset"] = preset
        if command == "preset" and ATTR_PRESET not in call.data:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="preset_required"
            )
        for target in _require_targets(hass, call):
            await target.coordinator.api.ptz(target.monitor_id, command, **kwargs)

    async def _set_monitor_state(call: ServiceCall) -> None:
        fields = {
            key: call.data[key]
            for key in (ATTR_CAPTURING, ATTR_ANALYSING, ATTR_RECORDING, ATTR_DECODING)
            if key in call.data
        }
        for target in _require_targets(hass, call):
            await target.coordinator.async_set_monitor_state(
                target.monitor_id, **fields
            )

    hass.services.async_register(
        DOMAIN, SERVICE_TRIGGER_EVENT, _trigger_event, schema=_TRIGGER_EVENT_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CANCEL_EVENT, _cancel_event, schema=_CANCEL_EVENT_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_PTZ, _ptz, schema=_PTZ_SCHEMA)
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_MONITOR_STATE,
        _set_monitor_state,
        schema=_SET_STATE_SCHEMA,
    )
    _LOGGER.debug("ZoneMinder services registered")
