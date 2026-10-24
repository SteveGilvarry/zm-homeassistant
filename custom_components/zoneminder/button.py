# SPDX-License-Identifier: AGPL-3.0-or-later
"""Buttons for the ZoneMinder integration.

Alarm buttons exist for every monitor. PTZ buttons are only created for
monitors ZoneMinder marks as controllable, so fixed cameras do not end up with
a row of controls that quietly do nothing.
"""

from __future__ import annotations

import logging

from aiozoneminder import Monitor
from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ZoneMinderDataUpdateCoordinator
from .data import ZoneMinderConfigEntry
from .entity import ZoneMinderMonitorEntity
from .exceptions import ha_errors

_LOGGER = logging.getLogger(__name__)

#: PTZ commands worth a dedicated button. Continuous movement belongs in the
#: ptz service, where an automation can pair it with a stop.
_PTZ_BUTTONS: tuple[tuple[str, str], ...] = (
    ("home", "ptz_home"),
    ("stop", "ptz_stop"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZoneMinderConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the ZoneMinder buttons."""
    coordinator = entry.runtime_data.coordinator
    presets = entry.runtime_data.ptz_presets

    entities: list[ButtonEntity] = []
    for monitor in coordinator.data.monitors.values():
        entities.append(ZoneMinderTriggerAlarmButton(coordinator, entry, monitor))
        entities.append(ZoneMinderCancelAlarmButton(coordinator, entry, monitor))

        if not monitor.controllable:
            continue

        entities.extend(
            ZoneMinderPTZButton(coordinator, entry, monitor, command, translation_key)
            for command, translation_key in _PTZ_BUTTONS
        )
        entities.extend(
            ZoneMinderPTZPresetButton(coordinator, entry, monitor, number, label)
            for number, label in sorted(presets.get(monitor.id, {}).items())
        )

    async_add_entities(entities)


class ZoneMinderTriggerAlarmButton(ZoneMinderMonitorEntity, ButtonEntity):
    """Force a monitor into alarm state."""

    entity_description = ButtonEntityDescription(
        key="trigger_alarm", translation_key="trigger_alarm"
    )

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
        monitor: Monitor,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry, monitor, "trigger_alarm")

    async def async_press(self) -> None:
        """Trigger the alarm."""
        async with ha_errors():
            await self.coordinator.async_trigger_alarm(
                self._monitor_id, "Home Assistant"
            )


class ZoneMinderCancelAlarmButton(ZoneMinderMonitorEntity, ButtonEntity):
    """Clear a forced alarm."""

    entity_description = ButtonEntityDescription(
        key="cancel_alarm",
        translation_key="cancel_alarm",
        entity_category=EntityCategory.CONFIG,
    )

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
        monitor: Monitor,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry, monitor, "cancel_alarm")

    async def async_press(self) -> None:
        """Cancel the alarm."""
        async with ha_errors():
            await self.coordinator.async_cancel_alarm(self._monitor_id)


class ZoneMinderPTZButton(ZoneMinderMonitorEntity, ButtonEntity):
    """A one-shot PTZ command."""

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
        monitor: Monitor,
        command: str,
        translation_key: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry, monitor, translation_key)
        self._command = command
        self._attr_translation_key = translation_key

    async def async_press(self) -> None:
        """Send the PTZ command."""
        async with ha_errors():
            await self.coordinator.api.ptz(self._monitor_id, self._command)


class ZoneMinderPTZPresetButton(ZoneMinderMonitorEntity, ButtonEntity):
    """Recall a stored PTZ preset."""

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
        monitor: Monitor,
        preset: int,
        label: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry, monitor, f"preset_{preset}")
        self._preset = preset
        self._attr_name = label

    async def async_press(self) -> None:
        """Move the camera to the preset."""
        async with ha_errors():
            await self.coordinator.api.ptz(
                self._monitor_id, "preset", preset=self._preset
            )
