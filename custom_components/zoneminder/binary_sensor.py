# SPDX-License-Identifier: Apache-2.0
"""Binary sensors for the ZoneMinder integration."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from aiozoneminder import Monitor
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import MQTT_MOTION_TIMEOUT, SIGNAL_ALARM_STATE, SIGNAL_MQTT_EVENT
from .coordinator import ZoneMinderDataUpdateCoordinator
from .data import ZoneMinderConfigEntry
from .entity import ZoneMinderMonitorEntity, ZoneMinderServerEntity
from .mqtt import ZoneMinderMQTTEvent

_LOGGER = logging.getLogger(__name__)

#: ZoneMinder's cause for events produced by continuous recording rather than
#: by motion analysis.
_CONTINUOUS_CAUSE = "Continuous"
_ALARM_STATES = ("idle", "prealarm", "alarm", "alert")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZoneMinderConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the ZoneMinder binary sensors."""
    coordinator = entry.runtime_data.coordinator

    entities: list[BinarySensorEntity] = [ZoneMinderServerRunning(coordinator, entry)]
    for monitor in coordinator.data.monitors.values():
        entities.append(ZoneMinderMotionSensor(coordinator, entry, monitor))
        entities.append(ZoneMinderConnectivitySensor(coordinator, entry, monitor))

    async_add_entities(entities)


class ZoneMinderMotionSensor(ZoneMinderMonitorEntity, BinarySensorEntity):
    """Motion detected on a monitor.

    MQTT drives the state within a second of an event opening. Polled data is
    the authority: it confirms or corrects what MQTT reported, and it takes
    over entirely if an "event end" message is ever lost.
    """

    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_translation_key = "motion"

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
        monitor: Monitor,
    ) -> None:
        """Initialize the motion sensor."""
        super().__init__(coordinator, entry, monitor, "motion")
        self._attr_is_on = False
        self._mqtt_event_id: int | None = None
        self._mqtt_since: datetime | None = None
        self._labels: list[str] = []
        #: ZoneMinder's own alarm state, when the event stream provides it.
        self._alarm_state: str | None = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to event notices and live alarm state for this monitor."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_MQTT_EVENT.format(self._monitor_id),
                self._handle_mqtt_event,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_ALARM_STATE.format(self._monitor_id),
                self._handle_alarm_state,
            )
        )
        self._recalculate()

    @callback
    def _handle_alarm_state(self, state: str) -> None:
        """Follow ZoneMinder's live alarm state, the most direct motion signal.

        "alert" is the post-alarm countdown, still part of the same motion.
        "unknown" means ZoneMinder can't read the monitor's state right now, so
        the event-based logic takes over again.
        """
        self._alarm_state = state if state in _ALARM_STATES else None
        self._recalculate()
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details of the event that motion is based on."""
        event = self.coordinator.data.latest_alarm(self._monitor_id)
        attrs: dict[str, Any] = {}
        if self._labels:
            attrs["detected_objects"] = self._labels
        if event is None:
            return attrs
        attrs.update(
            {
                "event_id": event.id,
                "cause": event.cause,
                "started_at": event.start_time.isoformat(),
                "alarm_frames": event.alarm_frames,
                "max_score": event.max_score,
                "in_progress": event.in_progress,
            }
        )
        if event.end_time is not None:
            attrs["ended_at"] = event.end_time.isoformat()
        return attrs

    @callback
    def _handle_mqtt_event(self, event: ZoneMinderMQTTEvent) -> None:
        """React to an MQTT notification for this monitor."""
        monitor = self.monitor

        if event.started:
            # ZoneMinder publishes a start for every event it opens, including
            # the ones continuous recording produces. Only a monitor that is
            # actually analysing can report motion, so anything else would be
            # a false positive.
            if event.cause == _CONTINUOUS_CAUSE:
                # A new chunk of continuous recording, not something moving.
                return
            if monitor is not None and not monitor.is_analysing:
                _LOGGER.debug(
                    "Ignoring event %d on monitor %d: motion analysis is off",
                    event.event_id,
                    event.monitor_id,
                )
                return
            self._mqtt_event_id = event.event_id
            self._mqtt_since = dt_util.utcnow()
            self._labels = event.labels
            self._attr_is_on = (
                self._alarm_state in ("alarm", "alert")
                if self._alarm_state is not None
                else True
            )
        elif event.event_id == self._mqtt_event_id:
            self._clear_mqtt_state()
            if self._alarm_state is None:
                self._attr_is_on = False
        else:
            return

        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Reconcile the polled state with whatever MQTT last told us."""
        self._recalculate()
        super()._handle_coordinator_update()

    def _clear_mqtt_state(self) -> None:
        """Forget the MQTT-tracked event."""
        self._mqtt_event_id = None
        self._mqtt_since = None
        self._labels = []

    def _recalculate(self) -> None:
        """Derive motion state from polled data and the MQTT override."""
        if self._alarm_state is not None:
            self._attr_is_on = self._alarm_state in ("alarm", "alert")
            return
        if self._mqtt_event_id is not None:
            if self._mqtt_expired():
                _LOGGER.debug(
                    "No end notification for event %d on monitor %d, falling "
                    "back to polled state",
                    self._mqtt_event_id,
                    self._monitor_id,
                )
                self._clear_mqtt_state()
            elif self._mqtt_event_contradicted():
                _LOGGER.debug(
                    "Event %d on monitor %d turned out to have no motion",
                    self._mqtt_event_id,
                    self._monitor_id,
                )
                self._clear_mqtt_state()
                self._attr_is_on = False
                return
            else:
                self._attr_is_on = True
                return

        event = self.coordinator.data.latest_alarm(self._monitor_id)
        self._attr_is_on = event is not None and event.in_progress

    def _mqtt_expired(self) -> bool:
        """Return True when an MQTT event has outlived its end notification."""
        if self._mqtt_since is None:
            return True
        return dt_util.utcnow() - self._mqtt_since > MQTT_MOTION_TIMEOUT

    def _mqtt_event_contradicted(self) -> bool:
        """Return True when polled data shows the tracked event is not motion.

        Continuous recording opens alarm-free events constantly. Once the poll
        catches up we can tell them apart and drop the provisional state.
        """
        for event in self.coordinator.data.events.get(self._monitor_id, []):
            if event.id != self._mqtt_event_id:
                continue
            if event.is_alarm:
                return False
            # An event that has finished with no alarm frames was never motion.
            # One still running might yet alarm, unless it is plainly
            # continuous recording.
            return not event.in_progress or event.cause == _CONTINUOUS_CAUSE
        return False


class ZoneMinderConnectivitySensor(ZoneMinderMonitorEntity, BinarySensorEntity):
    """Whether ZoneMinder's capture daemon is connected to the camera."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "connectivity"

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
        monitor: Monitor,
    ) -> None:
        """Initialize the connectivity sensor."""
        super().__init__(coordinator, entry, monitor, "connectivity")

    @property
    def is_on(self) -> bool | None:
        """Return True when the capture daemon reports a connection."""
        status = self.coordinator.data.statuses.get(self._monitor_id)
        if status is None:
            return None
        return status.connected

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the raw status string."""
        status = self.coordinator.data.statuses.get(self._monitor_id)
        return {"status": status.status} if status else {}


class ZoneMinderServerRunning(ZoneMinderServerEntity, BinarySensorEntity):
    """Whether the ZoneMinder daemons are running."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "server_running"

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "running")

    @property
    def is_on(self) -> bool:
        """Return True when ZoneMinder reports itself running."""
        return self.coordinator.data.server.running

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the daemon tally."""
        server = self.coordinator.data.server
        return {
            "daemons_running": server.daemons_running,
            "daemons_total": server.daemons_total,
        }
