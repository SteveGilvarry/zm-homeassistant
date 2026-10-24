# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sensors for the ZoneMinder integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from aiozoneminder import Monitor
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfDataRate, UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ZoneMinderData, ZoneMinderDataUpdateCoordinator
from .data import ZoneMinderConfigEntry
from .entity import ZoneMinderMonitorEntity, ZoneMinderServerEntity

_LOGGER = logging.getLogger(__name__)

type StateType = str | int | float | datetime | None


@dataclass(frozen=True, kw_only=True)
class ZoneMinderMonitorSensorDescription(SensorEntityDescription):
    """Describes a per-monitor sensor."""

    value_fn: Callable[[ZoneMinderData, int], StateType]
    attrs_fn: Callable[[ZoneMinderData, int], dict[str, Any]] | None = None


@dataclass(frozen=True, kw_only=True)
class ZoneMinderServerSensorDescription(SensorEntityDescription):
    """Describes a server-wide sensor."""

    value_fn: Callable[[ZoneMinderData], StateType]


def _last_event_attrs(data: ZoneMinderData, monitor_id: int) -> dict[str, Any]:
    """Return details of a monitor's most recent event."""
    event = data.latest_event(monitor_id)
    if event is None:
        return {}
    return {
        "event_id": event.id,
        "cause": event.cause,
        "length": event.length,
        "frames": event.frames,
        "alarm_frames": event.alarm_frames,
        "max_score": event.max_score,
        "in_progress": event.in_progress,
    }


MONITOR_SENSORS: tuple[ZoneMinderMonitorSensorDescription, ...] = (
    ZoneMinderMonitorSensorDescription(
        key="last_event",
        translation_key="last_event",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data, mid: (
            event.start_time if (event := data.latest_event(mid)) else None
        ),
        attrs_fn=_last_event_attrs,
    ),
    ZoneMinderMonitorSensorDescription(
        key="last_motion",
        translation_key="last_motion",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data, mid: (
            event.start_time if (event := data.latest_alarm(mid)) else None
        ),
    ),
    ZoneMinderMonitorSensorDescription(
        key="events_today",
        translation_key="events_today",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="events",
        value_fn=lambda data, mid: (
            summary.day_events if (summary := data.summaries.get(mid)) else None
        ),
    ),
    ZoneMinderMonitorSensorDescription(
        key="disk_usage",
        translation_key="disk_usage",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, mid: (
            summary.total_disk_space if (summary := data.summaries.get(mid)) else None
        ),
    ),
    ZoneMinderMonitorSensorDescription(
        key="capture_fps",
        translation_key="capture_fps",
        native_unit_of_measurement="fps",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, mid: (
            status.capture_fps if (status := data.statuses.get(mid)) else None
        ),
    ),
    ZoneMinderMonitorSensorDescription(
        key="analysis_fps",
        translation_key="analysis_fps",
        native_unit_of_measurement="fps",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data, mid: (
            status.analysis_fps if (status := data.statuses.get(mid)) else None
        ),
    ),
    ZoneMinderMonitorSensorDescription(
        key="capture_bandwidth",
        translation_key="capture_bandwidth",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.KILOBYTES_PER_SECOND,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, mid: (
            status.capture_bandwidth if (status := data.statuses.get(mid)) else None
        ),
    ),
    ZoneMinderMonitorSensorDescription(
        key="mode",
        translation_key="mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, mid: (
            monitor.function if (monitor := data.monitors.get(mid)) else None
        ),
    ),
)

SERVER_SENSORS: tuple[ZoneMinderServerSensorDescription, ...] = (
    ZoneMinderServerSensorDescription(
        key="disk_usage",
        translation_key="server_disk_usage",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.server.total_disk_space,
    ),
    ZoneMinderServerSensorDescription(
        key="events_today",
        translation_key="server_events_today",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="events",
        value_fn=lambda data: sum(
            summary.day_events for summary in data.summaries.values()
        ),
    ),
    ZoneMinderServerSensorDescription(
        key="monitors",
        translation_key="server_monitors",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="monitors",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: len(data.monitors),
    ),
    ZoneMinderServerSensorDescription(
        key="version",
        translation_key="server_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.server.version,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZoneMinderConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the ZoneMinder sensors."""
    coordinator = entry.runtime_data.coordinator

    entities: list[SensorEntity] = [
        ZoneMinderServerSensor(coordinator, entry, description)
        for description in SERVER_SENSORS
    ]
    entities.extend(
        ZoneMinderMonitorSensor(coordinator, entry, monitor, description)
        for monitor in coordinator.data.monitors.values()
        for description in MONITOR_SENSORS
    )
    async_add_entities(entities)


class ZoneMinderMonitorSensor(ZoneMinderMonitorEntity, SensorEntity):
    """A sensor describing one monitor."""

    entity_description: ZoneMinderMonitorSensorDescription

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
        monitor: Monitor,
        description: ZoneMinderMonitorSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, monitor, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data, self._monitor_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes, if this sensor supplies any."""
        if self.entity_description.attrs_fn is None:
            return {}
        return self.entity_description.attrs_fn(self.coordinator.data, self._monitor_id)


class ZoneMinderServerSensor(ZoneMinderServerEntity, SensorEntity):
    """A sensor describing the ZoneMinder server."""

    entity_description: ZoneMinderServerSensorDescription

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
        description: ZoneMinderServerSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)
