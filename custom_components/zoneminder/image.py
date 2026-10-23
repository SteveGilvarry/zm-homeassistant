# SPDX-License-Identifier: AGPL-3.0-or-later
"""The latest event's picture, per camera.

Handy on a dashboard ("what set it off?") and as a notification attachment.
On cameras that analyse it shows the latest motion; elsewhere the latest
recording.
"""

from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ZoneMinderDataUpdateCoordinator
from .data import ZoneMinderConfigEntry
from .entity import ZoneMinderMonitorEntity
from .exceptions import ZMApiError, ZMConnectionError
from .models import Event, Monitor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZoneMinderConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one latest-event image per camera, where thumbnails exist."""
    coordinator = entry.runtime_data.coordinator
    if coordinator.api.get_event_thumbnail_path(0) is None:
        return
    async_add_entities(
        ZoneMinderLatestEventImage(hass, coordinator, entry, monitor)
        for monitor in coordinator.data.monitors.values()
    )


class ZoneMinderLatestEventImage(ZoneMinderMonitorEntity, ImageEntity):
    """The thumbnail of a camera's most recent event."""

    _attr_translation_key = "latest_event"
    _attr_content_type = "image/jpeg"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
        monitor: Monitor,
    ) -> None:
        """Initialize the image entity."""
        ZoneMinderMonitorEntity.__init__(
            self, coordinator, entry, monitor, "latest_event"
        )
        ImageEntity.__init__(self, hass)
        self._event_id: int | None = None
        self._update_from_data()

    def _latest(self) -> Event | None:
        data = self.coordinator.data
        monitor = self.monitor
        if monitor is not None and monitor.is_analysing:
            if (alarm := data.latest_alarm(self._monitor_id)) is not None:
                return alarm
        return data.latest_event(self._monitor_id)

    def _update_from_data(self) -> None:
        event = self._latest()
        if event is None or event.id == self._event_id:
            return
        self._event_id = event.id
        self._attr_image_last_updated = event.start_time
        self._cached_image = None

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_from_data()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Unavailable until the camera has an event to show."""
        return super().available and self._event_id is not None

    @property
    def image_last_updated(self) -> datetime | None:
        """Return when the shown event started."""
        return self._attr_image_last_updated

    @property
    def extra_state_attributes(self) -> dict[str, int | str]:
        """Say which event is shown."""
        event = self._latest()
        if event is None:
            return {}
        return {"event_id": event.id, "cause": event.cause}

    async def async_image(self) -> bytes | None:
        """Fetch the event's thumbnail from ZoneMinder."""
        if self._event_id is None:
            return None
        api = self.coordinator.api
        path = api.get_event_thumbnail_path(self._event_id)
        if path is None:
            return None
        try:
            async with api.async_stream_media(path) as response:
                if response.status >= 400:
                    return None
                return await response.read()
        except (ZMApiError, ZMConnectionError, TimeoutError) as err:
            _LOGGER.debug("Thumbnail for event %d failed: %s", self._event_id, err)
            return None
