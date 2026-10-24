# SPDX-License-Identifier: AGPL-3.0-or-later
"""Event entities for the ZoneMinder integration.

An event entity is the natural shape for "something happened at this time":
automations trigger on it directly and get the event id, cause and any object
labels as typed attributes, instead of templating over a binary sensor's
attributes.
"""

from __future__ import annotations

import logging

from aiozoneminder import Monitor
from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SIGNAL_MQTT_EVENT
from .coordinator import ZoneMinderDataUpdateCoordinator
from .data import ZoneMinderConfigEntry
from .entity import ZoneMinderMonitorEntity
from .mqtt import ZoneMinderMQTTEvent
from .notify_media import async_event_media_urls

_LOGGER = logging.getLogger(__name__)

EVENT_MOTION = "motion"
EVENT_RECORDING = "recording"
#: Fired when an event closes, so a notification can be updated with its clip.
EVENT_ENDED = "ended"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZoneMinderConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one event entity per monitor."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        ZoneMinderEventEntity(coordinator, entry, monitor)
        for monitor in coordinator.data.monitors.values()
    )


class ZoneMinderEventEntity(ZoneMinderMonitorEntity, EventEntity):
    """Fires when ZoneMinder opens an event on a monitor."""

    _attr_device_class = EventDeviceClass.MOTION
    _attr_event_types = [EVENT_MOTION, EVENT_RECORDING, EVENT_ENDED]
    _attr_translation_key = "event"

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
        monitor: Monitor,
    ) -> None:
        """Initialize the event entity."""
        super().__init__(coordinator, entry, monitor, "event")

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT notifications for this monitor."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_MQTT_EVENT.format(self._monitor_id),
                self._handle_mqtt_event,
            )
        )

    @callback
    def _handle_mqtt_event(self, event: ZoneMinderMQTTEvent) -> None:
        """Fire when an event opens, and again when it closes."""
        attributes = {
            "event_id": event.event_id,
            "monitor_id": event.monitor_id,
            "cause": event.cause,
            "detected_objects": event.labels,
            **async_event_media_urls(self.entry, event.event_id),
        }
        if event.started:
            monitor = self.monitor
            analysing = monitor.is_analysing if monitor else False
            continuous = (event.cause or "").lower() == "continuous"
            event_type = (
                EVENT_MOTION if analysing and not continuous else EVENT_RECORDING
            )
        elif event.action == "end":
            event_type = EVENT_ENDED
        else:
            return
        self._trigger_event(event_type, attributes)
        self.async_write_ha_state()
