# SPDX-License-Identifier: AGPL-3.0-or-later
"""The ZoneMinder integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PATH,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    issue_registry as ir,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .api import client_from_entry_data
from .const import (
    BACKEND_V3,
    CONF_MQTT_ENABLED,
    CONF_MQTT_TOPIC,
    CONF_NOTIFY_KEY,
    CONFIG_MQTT_TOPIC_PREFIX,
    DEFAULT_MQTT_TOPIC,
    DOMAIN,
)
from .coordinator import ZoneMinderDataUpdateCoordinator
from .data import ZoneMinderConfigEntry, ZoneMinderRuntimeData
from .entity import monitor_device_id, server_device_id, server_device_info
from .event_watcher import ZoneMinderEventWatcher
from .exceptions import ZMApiError, ZMAuthenticationError, ZMConnectionError
from .frontend import async_register_card
from .http import async_register_proxy, generate_proxy_secret
from .mqtt import ZoneMinderMQTTListener
from .notify_media import async_register_event_media, generate_notify_key
from .repairs import async_check_issues
from .services import async_setup_services
from .webrtc import ZoneMinderWebRTCProvider
from .websocket_api import async_setup_websocket

_LOGGER = logging.getLogger(__name__)

#: The old core integration's YAML, accepted only so it can be imported.
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required(CONF_HOST): cv.string,
                        vol.Optional(CONF_PATH, default="/zm/"): cv.string,
                        vol.Optional("path_zms"): cv.string,
                        vol.Optional(CONF_SSL, default=False): cv.boolean,
                        vol.Optional(CONF_VERIFY_SSL, default=True): cv.boolean,
                        vol.Optional(CONF_USERNAME): cv.string,
                        vol.Optional(CONF_PASSWORD): cv.string,
                    },
                    extra=vol.ALLOW_EXTRA,
                )
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CAMERA,
    Platform.EVENT,
    Platform.IMAGE,
    Platform.SELECT,
    Platform.SENSOR,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Import servers from the old core integration's YAML, once."""
    for server in config.get(DOMAIN, []):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=server
            )
        )
    if DOMAIN in config:
        ir.async_create_issue(
            hass,
            HOMEASSISTANT_DOMAIN,
            f"deprecated_yaml_{DOMAIN}",
            is_fixable=False,
            issue_domain=DOMAIN,
            severity=ir.IssueSeverity.WARNING,
            translation_key="deprecated_yaml",
            translation_placeholders={
                "domain": DOMAIN,
                "integration_title": "ZoneMinder",
            },
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ZoneMinderConfigEntry) -> bool:
    """Set up ZoneMinder from a config entry."""
    if CONF_NOTIFY_KEY not in entry.data:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_NOTIFY_KEY: generate_notify_key()}
        )

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

    # Register the server first, so cameras can link to it by its registry id.
    entry.runtime_data.server_device_id = (
        dr.async_get(hass)
        .async_get_or_create(
            config_entry_id=entry.entry_id,
            **server_device_info(entry, coordinator.data.server.version),
        )
        .id
    )

    if coordinator.api.backend == BACKEND_V3:
        entry.runtime_data.webrtc_provider = ZoneMinderWebRTCProvider(hass, api)

    async_register_proxy(hass)
    async_register_event_media(hass)
    await async_register_card(hass)
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

    # Runs alongside MQTT too: it covers a broker that's down or misconfigured.
    watcher = ZoneMinderEventWatcher(hass, entry)
    entry.runtime_data.event_watcher = watcher
    watcher.async_start()
    entry.async_on_unload(watcher.async_stop)
    async_setup_services(hass)
    async_setup_websocket(hass)
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
    """Allow removing any device the integration no longer provides.

    That covers monitors deleted in ZoneMinder and devices left over from
    older identifier schemes (bare monitor ids, before entry-scoped ids).
    """
    live_ids = {server_device_id(entry)} | {
        monitor_device_id(entry, monitor_id)
        for monitor_id in entry.runtime_data.coordinator.data.monitors
    }
    return not any(
        identifier[1] in live_ids
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN
    )
