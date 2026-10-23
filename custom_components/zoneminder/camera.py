# SPDX-License-Identifier: AGPL-3.0-or-later
"""Camera platform for the ZoneMinder integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import BACKEND_LEGACY, STREAM_TYPE_MJPEG
from .coordinator import ZoneMinderDataUpdateCoordinator
from .data import ZoneMinderConfigEntry
from .entity import ZoneMinderMonitorEntity
from .http import async_proxy_url
from .models import Monitor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZoneMinderConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one camera per ZoneMinder monitor."""
    coordinator = entry.runtime_data.coordinator

    if coordinator.api.backend == BACKEND_LEGACY:
        # Resolve go2rtc up front so each camera knows whether it has a real
        # stream before it reports its supported features.
        await coordinator.api.check_go2rtc()

    async_add_entities(
        ZoneMinderCamera(coordinator, entry, monitor)
        for monitor in coordinator.data.monitors.values()
    )


class ZoneMinderCamera(ZoneMinderMonitorEntity, Camera):
    """Live view of a ZoneMinder monitor."""

    _attr_name = None

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
        monitor: Monitor,
    ) -> None:
        """Initialize the camera."""
        ZoneMinderMonitorEntity.__init__(self, coordinator, entry, monitor, "camera")
        Camera.__init__(self)

        self._stream_type = coordinator.api.get_stream_type(monitor.id)
        # An MJPEG URL is not something Home Assistant's stream component can
        # do anything useful with, so those monitors fall back to still images
        # rather than advertising a stream that never plays.
        if self._stream_type != STREAM_TYPE_MJPEG:
            self._attr_supported_features = CameraEntityFeature.STREAM

    @property
    def available(self) -> bool:
        """Return True while the monitor exists.

        A monitor that is not capturing can still be present and worth showing,
        so availability tracks existence rather than capture state.
        """
        return super().available

    @property
    def is_streaming(self) -> bool:
        """Return True when ZoneMinder is capturing from this monitor."""
        monitor = self.monitor
        return bool(monitor and monitor.enabled)

    @property
    def is_recording(self) -> bool:
        """Return True when ZoneMinder is writing events for this monitor."""
        monitor = self.monitor
        return bool(monitor and monitor.is_recording)

    @property
    def motion_detection_enabled(self) -> bool:
        """Return True when ZoneMinder is analysing this monitor for motion."""
        monitor = self.monitor
        return bool(monitor and monitor.is_analysing)

    @property
    def brand(self) -> str:
        """Return the brand shown in the more-info dialog."""
        return "ZoneMinder"

    @property
    def model(self) -> str | None:
        """Return the monitor's source type."""
        monitor = self.monitor
        return monitor.type if monitor else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return monitor state that cards and automations can use."""
        monitor = self.monitor
        if monitor is None:
            return {}

        attrs: dict[str, Any] = {
            "monitor_id": monitor.id,
            "capturing": monitor.capturing,
            "analysing": monitor.analysing,
            "recording": monitor.recording,
            "function": monitor.function,
            "width": monitor.width,
            "height": monitor.height,
            "orientation": monitor.orientation_label,
            "orientation_degrees": monitor.orientation_degrees,
            "stream_type": self._stream_type,
            "controllable": monitor.controllable,
        }

        if (status := self.coordinator.data.statuses.get(monitor.id)) is not None:
            attrs["status"] = status.status
            attrs["capture_fps"] = status.capture_fps
            attrs["analysis_fps"] = status.analysis_fps

        # Exposed so the companion card can answer zm-api's WebRTC offer
        # directly from the browser, which Home Assistant core cannot do.
        if signaling := self.coordinator.api.get_webrtc_signaling_url(monitor.id):
            attrs["webrtc_signaling_url"] = signaling

        if (event := self.coordinator.data.latest_event(monitor.id)) is not None:
            attrs["last_event_id"] = event.id
            attrs["last_event_cause"] = event.cause
            attrs["last_event_time"] = event.start_time.isoformat()
            attrs["last_event_alarm_frames"] = event.alarm_frames

        return attrs

    async def async_refresh_providers(self, *, write_state: bool = True) -> None:
        """Use ZoneMinder's own WebRTC when the server offers WHEP.

        Home Assistant picks a WebRTC provider from an unordered set, so ours
        could lose to its bundled go2rtc. It is attached directly instead,
        which keeps HLS on offer as the fallback.
        """
        provider = self.entry.runtime_data.webrtc_provider
        if provider is not None and await self.coordinator.api.async_supports_whep(
            self._monitor_id
        ):
            if self._webrtc_provider is not provider:
                self._webrtc_provider = provider
                self._invalidate_camera_capabilities_cache()
                if write_state:
                    self.async_write_ha_state()
            return
        await super().async_refresh_providers(write_state=write_state)

    async def stream_source(self) -> str | None:
        """Return a stream URL for Home Assistant's stream component.

        zm-api's signed RTSP link is preferred. Home Assistant's bundled
        go2rtc can turn RTSP into WebRTC (sub-second latency); it can't do that
        with HLS. Without RTSP we fall back to HLS. zm-api needs a live session
        before its playlist exists, and every part of the HLS chain needs a
        bearer token, so that URL points at the integration's media proxy.
        """
        api = self.coordinator.api

        if (rtsp := await api.async_get_rtsp_url(self._monitor_id)) is not None:
            return rtsp

        if (path := api.get_live_media_path(self._monitor_id)) is not None:
            await api.async_prepare_live(self._monitor_id)
            url = async_proxy_url(
                self.hass,
                self.entry.entry_id,
                self.entry.runtime_data.proxy_secret,
                path,
            )
            if url is None:
                _LOGGER.warning(
                    "Monitor %d has no stream URL because Home Assistant has no "
                    "internal URL configured",
                    self._monitor_id,
                )
            return url

        return await api.get_stream_source(self._monitor_id)

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still frame."""
        if self.monitor is None:
            return None
        return await self.coordinator.api.async_get_snapshot(self._monitor_id)
