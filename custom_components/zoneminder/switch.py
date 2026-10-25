# SPDX-License-Identifier: Apache-2.0
"""The function switch, replacing the core integration's switch platform.

Core gave each monitor a switch that flipped it between two of the old
single modes, chosen in YAML as command_on and command_off. It only exists
here when those options are set, which the YAML import does.
"""

from __future__ import annotations

from typing import Any

from aiozoneminder import Monitor, function_fields
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    AddEntitiesCallback,
)
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_FUNCTION_OFF, CONF_FUNCTION_ON
from .coordinator import ZoneMinderDataUpdateCoordinator
from .data import ZoneMinderConfigEntry
from .entity import ZoneMinderMonitorEntity
from .exceptions import ha_errors


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Accept the old `switch: - platform: zoneminder` YAML.

    Its settings are imported with the server (see yaml_import.py); this
    only stops Home Assistant reporting the platform as unsupported.
    """


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZoneMinderConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a function switch per monitor, when both modes are configured."""
    on = entry.options.get(CONF_FUNCTION_ON)
    off = entry.options.get(CONF_FUNCTION_OFF)
    if not on or not off:
        return
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        ZoneMinderFunctionSwitch(coordinator, entry, monitor, on, off)
        for monitor in coordinator.data.monitors.values()
    )


class ZoneMinderFunctionSwitch(ZoneMinderMonitorEntity, SwitchEntity):
    """Switches a monitor between two of the old single modes."""

    _attr_translation_key = "function"

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
        monitor: Monitor,
        on: str,
        off: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, monitor, "function")
        self._on = function_fields(on)
        self._off = function_fields(off)
        self._attr_translation_placeholders = {"function": on}

    @property
    def is_on(self) -> bool | None:
        """Return True while the monitor is in the "on" mode."""
        monitor = self.monitor
        if monitor is None:
            return None
        return (monitor.capturing, monitor.analysing, monitor.recording) == self._on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Put the monitor in the "on" mode."""
        await self._async_set(self._on)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Put the monitor in the "off" mode."""
        await self._async_set(self._off)

    async def _async_set(self, fields: tuple[str, str, str]) -> None:
        capturing, analysing, recording = fields
        async with ha_errors():
            await self.coordinator.async_set_monitor_state(
                self._monitor_id,
                capturing=capturing,
                analysing=analysing,
                recording=recording,
            )
