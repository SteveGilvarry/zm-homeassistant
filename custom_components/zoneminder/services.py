# SPDX-License-Identifier: Apache-2.0
"""Integration-level services for ZoneMinder."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from urllib.parse import urlsplit

from aiozoneminder import ZMNotSupportedError, function_fields
from aiozoneminder.const import (
    ANALYSING_OPTIONS,
    CAPTURING_OPTIONS,
    DECODING_OPTIONS,
    MONITOR_FUNCTIONS,
    PTZ_COMMANDS,
    RECORDING_OPTIONS,
    SERVER_ACTIONS,
)
from homeassistant.const import ATTR_DEVICE_ID, ATTR_ENTITY_ID, CONF_HOST
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
import voluptuous as vol

from .const import (
    DOMAIN,
    SERVICE_CANCEL_EVENT,
    SERVICE_PTZ,
    SERVICE_PTZ_PRESET,
    SERVICE_SAVE_RUN_STATE,
    SERVICE_SET_MONITOR_STATE,
    SERVICE_SET_RUN_STATE,
    SERVICE_TRIGGER_EVENT,
)
from .coordinator import ZoneMinderDataUpdateCoordinator
from .data import ZoneMinderConfigEntry
from .exceptions import ha_errors

_LOGGER = logging.getLogger(__name__)

ATTR_CAUSE = "cause"
ATTR_COMMAND = "command"
ATTR_PRESET = "preset"
ATTR_DIRECTION = "direction"
ATTR_CAPTURING = "capturing"
ATTR_ANALYSING = "analysing"
ATTR_RECORDING = "recording"
ATTR_DECODING = "decoding"
ATTR_FUNCTION = "function"

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


def _ptz_command(value: object) -> str:
    """Accept up_left as well as up-left, as nabbi/ha-zoneminder spelled it."""
    command = str(value).lower().replace("_", "-")
    if command not in PTZ_COMMANDS:
        raise vol.Invalid(f"value must be one of {sorted(PTZ_COMMANDS)}")
    return command


_PTZ_SCHEMA = vol.Schema(
    vol.All(
        {
            **_TARGET_SCHEMA,
            # `direction` is nabbi/ha-zoneminder's name for the same field.
            vol.Exclusive(ATTR_COMMAND, "command"): _ptz_command,
            vol.Exclusive(ATTR_DIRECTION, "command"): _ptz_command,
            vol.Optional(ATTR_PRESET): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=255)
            ),
        },
        cv.has_at_least_one_key(ATTR_COMMAND, ATTR_DIRECTION),
    )
)

#: nabbi/ha-zoneminder's preset service, where preset 0 is the home position.
_PTZ_PRESET_SCHEMA = vol.Schema(
    {
        **_TARGET_SCHEMA,
        vol.Required(ATTR_PRESET): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
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
            # A pre-1.37 mode, such as Modect, standing for the three above.
            vol.Optional(ATTR_FUNCTION): vol.In(MONITOR_FUNCTIONS),
        },
        cv.has_at_least_one_key(
            ATTR_CAPTURING, ATTR_ANALYSING, ATTR_RECORDING, ATTR_DECODING, ATTR_FUNCTION
        ),
    )
)


_SAVE_RUN_STATE_SCHEMA = vol.Schema(
    {
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=64)),
        vol.Optional("config_entry_id"): cv.string,
    }
)

_SET_RUN_STATE_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        # Core's way of naming the server: its YAML host, such as zm.local.
        vol.Optional("id"): cv.string,
        vol.Optional("config_entry_id"): cv.string,
    }
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


def _pick_server(hass: HomeAssistant, call: ServiceCall) -> ZoneMinderConfigEntry:
    """Find the server a call means, by entry id or by core's `id` (its host)."""
    entries: list[ZoneMinderConfigEntry] = hass.config_entries.async_loaded_entries(
        DOMAIN
    )
    if entry_id := call.data.get("config_entry_id"):
        entries = [entry for entry in entries if entry.entry_id == entry_id]
    if server_id := call.data.get("id"):
        entries = [entry for entry in entries if _is_server(entry, server_id)]
        if not entries:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_server",
                translation_placeholders={"id": server_id},
            )
    if len(entries) != 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="pick_one_server"
        )
    return entries[0]


def _is_server(entry: ZoneMinderConfigEntry, server_id: str) -> bool:
    """Whether core's server id (its YAML host, maybe with a port) is this entry."""
    url = urlsplit(entry.data[CONF_HOST])
    return server_id.lower() in {
        entry.data[CONF_HOST].lower(),
        url.netloc.lower(),
        (url.hostname or "").lower(),
    }


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the ZoneMinder services once per Home Assistant instance."""
    if hass.services.has_service(DOMAIN, SERVICE_TRIGGER_EVENT):
        return

    async def _trigger_event(call: ServiceCall) -> None:
        cause = call.data[ATTR_CAUSE]
        for target in _require_targets(hass, call):
            async with ha_errors():
                await target.coordinator.async_trigger_alarm(target.monitor_id, cause)

    async def _cancel_event(call: ServiceCall) -> None:
        for target in _require_targets(hass, call):
            async with ha_errors():
                await target.coordinator.async_cancel_alarm(target.monitor_id)

    async def _ptz(call: ServiceCall) -> None:
        command = call.data.get(ATTR_COMMAND) or call.data[ATTR_DIRECTION]
        kwargs = {}
        if (preset := call.data.get(ATTR_PRESET)) is not None:
            kwargs["preset"] = preset
        if command == "preset" and ATTR_PRESET not in call.data:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="preset_required"
            )
        for target in _require_targets(hass, call):
            async with ha_errors():
                await target.coordinator.api.ptz(target.monitor_id, command, **kwargs)

    async def _ptz_preset(call: ServiceCall) -> None:
        preset = call.data[ATTR_PRESET]
        command, kwargs = (
            ("home", {}) if preset == 0 else ("preset", {"preset": preset})
        )
        for target in _require_targets(hass, call):
            async with ha_errors():
                await target.coordinator.api.ptz(target.monitor_id, command, **kwargs)

    async def _set_monitor_state(call: ServiceCall) -> None:
        fields: dict[str, str] = {}
        if function := call.data.get(ATTR_FUNCTION):
            fields = dict(
                zip(
                    (ATTR_CAPTURING, ATTR_ANALYSING, ATTR_RECORDING),
                    function_fields(function),
                    strict=True,
                )
            )
        # Fields given explicitly win over the ones a function stands for.
        fields.update(
            {
                key: call.data[key]
                for key in (
                    ATTR_CAPTURING,
                    ATTR_ANALYSING,
                    ATTR_RECORDING,
                    ATTR_DECODING,
                )
                if key in call.data
            }
        )
        for target in _require_targets(hass, call):
            async with ha_errors():
                await target.coordinator.async_set_monitor_state(
                    target.monitor_id, **fields
                )

    async def _save_run_state(call: ServiceCall) -> None:
        entries = [
            entry
            for entry in hass.config_entries.async_loaded_entries(DOMAIN)
            if call.data.get("config_entry_id") in (None, entry.entry_id)
        ]
        if len(entries) != 1:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="pick_one_server"
            )
        try:
            async with ha_errors():
                await entries[0].runtime_data.coordinator.async_save_run_state(
                    call.data["name"]
                )
        except ServiceValidationError as err:
            if not isinstance(err.__cause__, ZMNotSupportedError):
                raise
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="run_states_need_v3"
            ) from err

    async def _set_run_state(call: ServiceCall) -> None:
        entry = _pick_server(hass, call)
        coordinator = entry.runtime_data.coordinator
        name = call.data["name"]
        if name.lower() in SERVER_ACTIONS:
            async with ha_errors():
                await coordinator.api.server_control(name.lower())
            return
        names = [state.name for state in coordinator.data.run_states]
        if name not in names:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_run_state",
                translation_placeholders={"name": name, "options": ", ".join(names)},
            )
        async with ha_errors():
            await coordinator.async_set_run_state(name)

    hass.services.async_register(
        DOMAIN, SERVICE_SAVE_RUN_STATE, _save_run_state, schema=_SAVE_RUN_STATE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_RUN_STATE, _set_run_state, schema=_SET_RUN_STATE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_TRIGGER_EVENT, _trigger_event, schema=_TRIGGER_EVENT_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CANCEL_EVENT, _cancel_event, schema=_CANCEL_EVENT_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_PTZ, _ptz, schema=_PTZ_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_PTZ_PRESET, _ptz_preset, schema=_PTZ_PRESET_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_MONITOR_STATE,
        _set_monitor_state,
        schema=_SET_STATE_SCHEMA,
    )
    _LOGGER.debug("ZoneMinder services registered")
