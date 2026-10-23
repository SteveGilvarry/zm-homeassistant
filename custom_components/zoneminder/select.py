# SPDX-License-Identifier: AGPL-3.0-or-later
"""Select entities for a monitor's capture, analysis and recording mode.

ZoneMinder 1.37 replaced the single "Function" dropdown with three independent
settings, so this exposes the three real fields rather than a lossy
reconstruction of the old one.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ANALYSING_OPTIONS,
    CAPTURING_OPTIONS,
    DECODING_OPTIONS,
    RECORDING_OPTIONS,
)
from .coordinator import ZoneMinderDataUpdateCoordinator
from .data import ZoneMinderConfigEntry
from .entity import ZoneMinderMonitorEntity, ZoneMinderServerEntity
from .models import Monitor

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ZoneMinderSelectDescription(SelectEntityDescription):
    """Describes one monitor state field exposed as a select."""

    field: str


SELECTS: tuple[ZoneMinderSelectDescription, ...] = (
    ZoneMinderSelectDescription(
        key="capturing",
        field="capturing",
        translation_key="capturing",
        options=CAPTURING_OPTIONS,
    ),
    ZoneMinderSelectDescription(
        key="analysing",
        field="analysing",
        translation_key="analysing",
        options=ANALYSING_OPTIONS,
    ),
    ZoneMinderSelectDescription(
        key="recording",
        field="recording",
        translation_key="recording",
        options=RECORDING_OPTIONS,
    ),
    ZoneMinderSelectDescription(
        key="decoding",
        field="decoding",
        translation_key="decoding",
        options=DECODING_OPTIONS,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZoneMinderConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the monitor mode selects."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SelectEntity] = [
        ZoneMinderModeSelect(coordinator, entry, monitor, description)
        for monitor in coordinator.data.monitors.values()
        for description in SELECTS
    ]
    # ZoneMinder always has "default"; a select with one option is noise.
    if len(coordinator.data.run_states) >= 2:
        entities.append(ZoneMinderRunStateSelect(coordinator, entry))
    async_add_entities(entities)


class ZoneMinderRunStateSelect(ZoneMinderServerEntity, SelectEntity):
    """The server's run state: a saved set of modes, such as Home or Away.

    Switching it changes every camera at once, which is what presence-based
    arming automations want.
    """

    _attr_translation_key = "run_state"

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator, entry, "run_state")

    @property
    def options(self) -> list[str]:
        """Return the saved run states."""
        return [state.name for state in self.coordinator.data.run_states]

    @property
    def current_option(self) -> str | None:
        """Return the active run state, if ZoneMinder marks one."""
        return next(
            (s.name for s in self.coordinator.data.run_states if s.active), None
        )

    async def async_select_option(self, option: str) -> None:
        """Switch run state."""
        await self.coordinator.async_set_run_state(option)


class ZoneMinderModeSelect(ZoneMinderMonitorEntity, SelectEntity):
    """One of a monitor's mode fields."""

    entity_description: ZoneMinderSelectDescription

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
        monitor: Monitor,
        description: ZoneMinderSelectDescription,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator, entry, monitor, description.key)
        self.entity_description = description

    @property
    def options(self) -> list[str]:
        """Return the selectable modes."""
        options: Sequence[str] = self.entity_description.options or []
        return list(options)

    @property
    def current_option(self) -> str | None:
        """Return the monitor's current mode for this field."""
        monitor = self.monitor
        if monitor is None:
            return None
        value = getattr(monitor, self.entity_description.field, None)
        return value if value in self.options else None

    async def async_select_option(self, option: str) -> None:
        """Change the monitor's mode.

        Any failure propagates so the user sees it, rather than the UI showing
        a change ZoneMinder rejected.
        """
        await self.coordinator.async_set_monitor_state(
            self._monitor_id, **{self.entity_description.field: option}
        )
