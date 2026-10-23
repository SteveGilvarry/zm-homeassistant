# SPDX-License-Identifier: AGPL-3.0-or-later
"""Browse and play ZoneMinder recordings from Home Assistant's media panel.

Recordings show up under Media > ZoneMinder, organised camera by camera and
then day by day, and each one plays in the browser or casts to a display.
Clips are served through the integration's media proxy so the browser never
needs a ZoneMinder token.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.components.media_player import BrowseError, MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .data import ZoneMinderConfigEntry
from .http import async_proxy_path
from .models import Event

_LOGGER = logging.getLogger(__name__)

MIME_TYPE = "video/mp4"
#: How far back the day list goes.
MAX_DAYS = 30
#: Events fetched when working out which days have recordings.
DAY_SCAN_LIMIT = 1000


async def async_get_media_source(hass: HomeAssistant) -> ZoneMinderMediaSource:
    """Set up the ZoneMinder media source."""
    return ZoneMinderMediaSource(hass)


class ZoneMinderMediaSource(MediaSource):
    """Expose ZoneMinder events as browsable media."""

    name = "ZoneMinder"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the media source."""
        super().__init__(DOMAIN)
        self.hass = hass

    # -- Entries -------------------------------------------------------------

    def _entries(self) -> list[ZoneMinderConfigEntry]:
        """Return every loaded ZoneMinder config entry."""
        return [
            entry
            for entry in self.hass.config_entries.async_entries(DOMAIN)
            if getattr(entry, "runtime_data", None) is not None
        ]

    def _entry(self, entry_id: str) -> ZoneMinderConfigEntry:
        """Return one loaded entry, or raise if it is not available."""
        for entry in self._entries():
            if entry.entry_id == entry_id:
                return entry
        raise BrowseError("That ZoneMinder server is not available")

    # -- Resolving -----------------------------------------------------------

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve an event to a playable URL."""
        parts = item.identifier.split("/")
        if len(parts) != 4:
            raise Unresolvable(f"Not a ZoneMinder recording: {item.identifier}")

        entry_id, _monitor_id, _date, event_id = parts
        try:
            entry = self._entry(entry_id)
        except BrowseError as err:
            raise Unresolvable(str(err)) from err
        api = entry.runtime_data.coordinator.api

        path = api.get_event_media_path(int(event_id))
        if path is None:
            raise Unresolvable("This backend cannot serve recordings")

        return PlayMedia(
            async_proxy_path(entry_id, entry.runtime_data.proxy_secret, path),
            MIME_TYPE,
        )

    # -- Browsing ------------------------------------------------------------

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Browse one level of the tree."""
        if not item.identifier:
            return self._browse_root()

        parts = item.identifier.split("/")
        if len(parts) == 1:
            return await self._browse_monitors(parts[0])
        if len(parts) == 2:
            return await self._browse_days(parts[0], int(parts[1]))
        if len(parts) == 3:
            return await self._browse_events(parts[0], int(parts[1]), parts[2])

        raise BrowseError(f"Cannot browse {item.identifier}")

    def _browse_root(self) -> BrowseMediaSource:
        """List the configured ZoneMinder servers."""
        entries = self._entries()

        children = [
            BrowseMediaSource(
                domain=DOMAIN,
                identifier=entry.entry_id,
                media_class=MediaClass.DIRECTORY,
                media_content_type=MediaClass.VIDEO,
                title=entry.title,
                can_play=False,
                can_expand=True,
            )
            for entry in entries
        ]

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaClass.VIDEO,
            title="ZoneMinder",
            can_play=False,
            can_expand=True,
            children=children,
            children_media_class=MediaClass.DIRECTORY,
        )

    async def _browse_monitors(self, entry_id: str) -> BrowseMediaSource:
        """List a server's monitors."""
        entry = self._entry(entry_id)
        coordinator = entry.runtime_data.coordinator

        children = [
            BrowseMediaSource(
                domain=DOMAIN,
                identifier=f"{entry_id}/{monitor.id}",
                media_class=MediaClass.DIRECTORY,
                media_content_type=MediaClass.VIDEO,
                title=monitor.name,
                can_play=False,
                can_expand=True,
            )
            for monitor in coordinator.data.monitors.values()
        ]

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=entry_id,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaClass.VIDEO,
            title=entry.title,
            can_play=False,
            can_expand=True,
            children=children,
            children_media_class=MediaClass.DIRECTORY,
        )

    async def _browse_days(self, entry_id: str, monitor_id: int) -> BrowseMediaSource:
        """List the days a monitor has recordings for."""
        entry = self._entry(entry_id)
        coordinator = entry.runtime_data.coordinator
        monitor = coordinator.data.monitors.get(monitor_id)
        if monitor is None:
            raise BrowseError(f"Unknown monitor {monitor_id}")

        events = await coordinator.api.get_events(
            monitor_id=monitor_id, limit=DAY_SCAN_LIMIT
        )

        counts: dict[str, int] = {}
        for event in events:
            day = dt_util.as_local(event.start_time).strftime("%Y-%m-%d")
            counts[day] = counts.get(day, 0) + 1

        children = [
            BrowseMediaSource(
                domain=DOMAIN,
                identifier=f"{entry_id}/{monitor_id}/{day}",
                media_class=MediaClass.DIRECTORY,
                media_content_type=MediaClass.VIDEO,
                title=f"{_day_title(day)} ({count})",
                can_play=False,
                can_expand=True,
            )
            for day, count in sorted(counts.items(), reverse=True)[:MAX_DAYS]
        ]

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"{entry_id}/{monitor_id}",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaClass.VIDEO,
            title=monitor.name,
            can_play=False,
            can_expand=True,
            children=children,
            children_media_class=MediaClass.DIRECTORY,
        )

    async def _browse_events(
        self, entry_id: str, monitor_id: int, day: str
    ) -> BrowseMediaSource:
        """List a monitor's recordings for one day."""
        entry = self._entry(entry_id)
        coordinator = entry.runtime_data.coordinator
        monitor = coordinator.data.monitors.get(monitor_id)
        if monitor is None:
            raise BrowseError(f"Unknown monitor {monitor_id}")

        try:
            start = dt_util.start_of_local_day(
                datetime.strptime(day, "%Y-%m-%d").date()
            )
        except ValueError as err:
            raise BrowseError(f"Not a date: {day}") from err

        events = await coordinator.api.get_events_between(
            monitor_id, start, start + timedelta(days=1)
        )

        secret = entry.runtime_data.proxy_secret
        api = coordinator.api
        children = []
        for event in events:
            if not event.has_video:
                continue
            thumbnail_path = api.get_event_thumbnail_path(event.id)
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=f"{entry_id}/{monitor_id}/{day}/{event.id}",
                    media_class=MediaClass.VIDEO,
                    media_content_type=MediaType.VIDEO,
                    title=_event_title(event),
                    can_play=True,
                    can_expand=False,
                    thumbnail=(
                        async_proxy_path(entry_id, secret, thumbnail_path)
                        if thumbnail_path
                        else None
                    ),
                )
            )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"{entry_id}/{monitor_id}/{day}",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaClass.VIDEO,
            title=f"{monitor.name} {_day_title(day)}",
            can_play=False,
            can_expand=True,
            children=children,
            children_media_class=MediaClass.VIDEO,
        )


def _day_title(day: str) -> str:
    """Return a friendly label for a day, marking today and yesterday."""
    today = dt_util.now().date()
    try:
        date = datetime.strptime(day, "%Y-%m-%d").date()
    except ValueError:
        return day
    if date == today:
        return "Today"
    if date == today - timedelta(days=1):
        return "Yesterday"
    return date.strftime("%a %d %b %Y")


def _event_title(event: Event) -> str:
    """Return a one-line label for an event."""
    when = dt_util.as_local(event.start_time).strftime("%H:%M:%S")
    parts = [when, event.cause or "Event"]
    if event.length:
        parts.append(f"{event.length:.0f}s")
    if event.alarm_frames:
        parts.append(f"{event.alarm_frames} alarm frames")
    return " - ".join(parts)
