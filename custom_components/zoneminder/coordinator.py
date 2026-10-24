# SPDX-License-Identifier: AGPL-3.0-or-later
"""Polling coordinator for the ZoneMinder integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

from aiozoneminder import (
    Event,
    EventSummary,
    Monitor,
    MonitorStatus,
    RunState,
    ServerInfo,
    ZMApiError,
    ZMAuthenticationError,
    ZMConnectionError,
    ZoneMinderClient,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_MQTT_ENABLED,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_FETCH_LIMIT,
    EVENTS_PER_MONITOR,
    MQTT_SCAN_INTERVAL,
    SERVER_INFO_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ZoneMinderData:
    """One snapshot of everything the entities read from."""

    monitors: dict[int, Monitor] = field(default_factory=dict)
    statuses: dict[int, MonitorStatus] = field(default_factory=dict)
    events: dict[int, list[Event]] = field(default_factory=dict)
    summaries: dict[int, EventSummary] = field(default_factory=dict)
    server: ServerInfo = field(default_factory=ServerInfo)
    configs: dict[str, str] = field(default_factory=dict)
    run_states: list[RunState] = field(default_factory=list)

    def latest_event(self, monitor_id: int) -> Event | None:
        """Return the most recent event for a monitor."""
        events = self.events.get(monitor_id)
        return events[0] if events else None

    def latest_alarm(self, monitor_id: int) -> Event | None:
        """Return the most recent event that actually contained motion.

        Continuous recording produces a constant stream of alarm-free events,
        so motion entities need the newest *alarmed* event, not the newest one.
        """
        for event in self.events.get(monitor_id, []):
            if event.is_alarm:
                return event
        return None


class ZoneMinderDataUpdateCoordinator(DataUpdateCoordinator[ZoneMinderData]):
    """Fetch monitors, capture status and recent events on a schedule."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry,
        api: ZoneMinderClient,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        self.entry = entry
        self._last_server_info: datetime | None = None
        self._server_info = ServerInfo()
        self._configs: dict[str, str] = {}
        self._run_states: list[RunState] = []

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.data[CONF_HOST]}",
            update_interval=_resolve_interval(entry),
            config_entry=entry,
        )

    def async_update_interval(self) -> None:
        """Re-read the polling interval after the options change."""
        interval = _resolve_interval(self.entry)
        if interval != self.update_interval:
            _LOGGER.debug("Polling interval changed to %s", interval)
            self.update_interval = interval

    async def _async_update_data(self) -> ZoneMinderData:
        """Fetch the current state of every monitor."""
        try:
            monitors = await self.api.get_monitors()
            monitors_by_id = {monitor.id: monitor for monitor in monitors}

            statuses = await self.api.get_monitor_statuses()
            events = await self._async_fetch_events(monitors_by_id)
            summaries = await self._async_fetch_server_extras(monitors_by_id)

            return ZoneMinderData(
                monitors=monitors_by_id,
                statuses=statuses,
                events=events,
                summaries=summaries,
                server=self._server_info,
                configs=self._configs,
                run_states=self._run_states,
            )

        except ZMAuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (ZMConnectionError, ZMApiError) as err:
            raise UpdateFailed(str(err)) from err

    async def _async_fetch_events(
        self, monitors: dict[int, Monitor]
    ) -> dict[int, list[Event]]:
        """Fetch recent events for every monitor.

        One bulk request covers all monitors. Only monitors that the bulk
        window missed entirely get a follow-up request, so a busy camera can
        never starve a quiet one of its last known event.
        """
        events: dict[int, list[Event]] = {monitor_id: [] for monitor_id in monitors}

        for event in await self.api.get_events(limit=EVENT_FETCH_LIMIT):
            bucket = events.get(event.monitor_id)
            if bucket is not None and len(bucket) < EVENTS_PER_MONITOR:
                bucket.append(event)

        for monitor_id, bucket in events.items():
            if bucket:
                continue
            try:
                events[monitor_id] = await self.api.get_events(
                    monitor_id=monitor_id, limit=EVENTS_PER_MONITOR
                )
            except (ZMConnectionError, ZMApiError) as err:
                _LOGGER.debug("Events for monitor %d failed: %s", monitor_id, err)

        return events

    async def _async_fetch_server_extras(
        self, monitors: dict[int, Monitor]
    ) -> dict[int, EventSummary]:
        """Refresh slow-moving server data on its own, longer cycle."""
        now = datetime.now()
        if (
            self._last_server_info is not None
            and now - self._last_server_info < SERVER_INFO_INTERVAL
        ):
            return getattr(self.data, "summaries", {}) if self.data else {}

        self._last_server_info = now

        try:
            self._server_info = await self.api.get_server_info()
        except (ZMConnectionError, ZMApiError) as err:
            _LOGGER.debug("Server info unavailable: %s", err)

        if not self._configs:
            try:
                self._configs = await self.api.get_configs()
            except (ZMConnectionError, ZMApiError) as err:
                _LOGGER.debug("Configuration unavailable: %s", err)

        await self._async_fetch_run_states()

        summaries: dict[int, EventSummary] = {}
        for monitor_id in monitors:
            summary = await self.api.get_event_summary(monitor_id)
            if summary is not None:
                summaries[monitor_id] = summary
        return summaries

    async def _async_fetch_run_states(self) -> None:
        try:
            self._run_states = await self.api.get_run_states()
        except (ZMConnectionError, ZMApiError) as err:
            _LOGGER.debug("Run states unavailable: %s", err)

    # -- Commands ------------------------------------------------------------

    async def async_save_run_state(self, name: str) -> None:
        """Save every monitor's current modes as a named run state."""
        definition = ",".join(
            f"{m.id}:{m.capturing}:{m.analysing}:{m.recording}"
            for m in sorted(self.data.monitors.values(), key=lambda m: m.id)
        )
        had_select = len(self._run_states) >= 2
        await self.api.save_run_state(name, definition)
        await self._async_fetch_run_states()
        if not had_select and len(self._run_states) >= 2:
            # The run state select only exists once there is a choice to make.
            self.hass.config_entries.async_schedule_reload(self.entry.entry_id)
        else:
            await self.async_request_refresh()

    async def async_set_run_state(self, name: str) -> None:
        """Switch the server to a named run state and refresh."""
        state = next((s for s in self._run_states if s.name == name), None)
        if state is None:
            raise ZMApiError(f"No run state called {name}")
        await self.api.set_run_state(state)
        await self._async_fetch_run_states()
        await self.async_request_refresh()

    async def async_set_monitor_state(self, monitor_id: int, **fields: str) -> None:
        """Change a monitor's mode and refresh."""
        await self.api.set_monitor_state(monitor_id, **fields)
        await self.async_request_refresh()

    async def async_trigger_alarm(self, monitor_id: int, cause: str) -> None:
        """Force a monitor into alarm state."""
        await self.api.trigger_alarm(monitor_id, cause)
        await self.async_request_refresh()

    async def async_cancel_alarm(self, monitor_id: int) -> None:
        """Clear a forced alarm."""
        await self.api.cancel_alarm(monitor_id)
        await self.async_request_refresh()


def _resolve_interval(entry) -> timedelta:
    """Work out how often to poll.

    MQTT delivers events within a second, so polling only needs to catch
    configuration drift and act as a safety net. Without it, polling is the
    only source of event data and has to be much more frequent.
    """
    if (configured := entry.options.get(CONF_SCAN_INTERVAL)) is not None:
        return timedelta(seconds=int(configured))
    if entry.options.get(CONF_MQTT_ENABLED, True):
        return MQTT_SCAN_INTERVAL
    return DEFAULT_SCAN_INTERVAL
