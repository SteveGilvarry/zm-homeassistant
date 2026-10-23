# SPDX-License-Identifier: AGPL-3.0-or-later
"""The ZoneMinder integration."""

from __future__ import annotations

import logging

from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import client_from_entry_data
from .const import (
    CONF_MQTT_ENABLED,
    CONF_MQTT_TOPIC,
    CONFIG_MQTT_TOPIC_PREFIX,
    DEFAULT_MQTT_TOPIC,
    DOMAIN,
)
from .coordinator import ZoneMinderDataUpdateCoordinator
from .data import ZoneMinderConfigEntry, ZoneMinderRuntimeData
from .exceptions import ZMApiError, ZMAuthenticationError, ZMConnectionError
from .http import async_register_proxy, generate_proxy_secret
from .mqtt import ZoneMinderMQTTListener
from .repairs import async_check_issues
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CAMERA,
    Platform.EVENT,
    Platform.SELECT,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ZoneMinderConfigEntry) -> bool:
    """Set up ZoneMinder from a config entry."""
    session = async_get_clientsession(hass)
    api = client_from_entry_data(entry.data, session)

    try:
        await api.authenticate()
    except ZMAuthenticationError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except (ZMConnectionError, ZMApiError) as err:
        raise ConfigEntryNotReady(
            f"Could not reach ZoneMinder at {entry.data[CONF_HOST]}: {err}"
        ) from err

    coordinator = ZoneMinderDataUpdateCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = ZoneMinderRuntimeData(
        coordinator=coordinator,
        proxy_secret=generate_proxy_secret(),
    )

    async_register_proxy(hass)
    await _async_load_ptz_presets(entry)

    if entry.options.get(CONF_MQTT_ENABLED, True):
        listener = ZoneMinderMQTTListener(
            hass, entry, coordinator, _resolve_mqtt_topic(entry, coordinator)
        )
        if await listener.async_setup():
            entry.runtime_data.mqtt_listener = listener
        else:
            _LOGGER.warning(
                "Real-time events are unavailable, falling back to polling every %s",
                coordinator.update_interval,
            )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_setup_services(hass)
    async_check_issues(hass, entry)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.info(
        "ZoneMinder %s ready at %s with %d monitors",
        coordinator.data.server.version,
        entry.data[CONF_HOST],
        len(coordinator.data.monitors),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ZoneMinderConfigEntry) -> bool:
    """Unload a config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    runtime = entry.runtime_data
    if runtime.mqtt_listener is not None:
        await runtime.mqtt_listener.async_unsubscribe()
    await runtime.coordinator.api.close()
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ZoneMinderConfigEntry) -> None:
    """Reload the entry after its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_load_ptz_presets(entry: ZoneMinderConfigEntry) -> None:
    """Cache the PTZ presets of every controllable monitor."""
    coordinator = entry.runtime_data.coordinator
    for monitor in coordinator.data.monitors.values():
        if not monitor.controllable:
            continue
        presets = await coordinator.api.get_ptz_presets(monitor.id)
        if presets:
            entry.runtime_data.ptz_presets[monitor.id] = presets


def _resolve_mqtt_topic(
    entry: ZoneMinderConfigEntry, coordinator: ZoneMinderDataUpdateCoordinator
) -> str:
    """Work out the MQTT topic prefix to subscribe to.

    An explicit option wins. Otherwise we use the prefix ZoneMinder itself
    reports, which saves the user from having to match its capitalisation by
    hand, and fall back to the documented default.
    """
    if configured := entry.options.get(CONF_MQTT_TOPIC):
        return str(configured)
    if discovered := coordinator.data.configs.get(CONFIG_MQTT_TOPIC_PREFIX):
        _LOGGER.debug("Using MQTT topic prefix reported by ZoneMinder: %s", discovered)
        return str(discovered)
    return DEFAULT_MQTT_TOPIC


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ZoneMinderConfigEntry, device_entry
) -> bool:
    """Allow removing a device whose monitor no longer exists."""
    monitor_ids = {
        str(monitor_id) for monitor_id in entry.runtime_data.coordinator.data.monitors
    }
    return not any(
        identifier[1] in monitor_ids
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN
    )
