# SPDX-License-Identifier: Apache-2.0
"""Notice events opening and closing without MQTT.

MQTT has to be set up on both ZoneMinder and Home Assistant, and when it
isn't, motion sensors, event entities and notifications go quiet without
saying why. So the integration finds out about events itself:

- From API v3's event stream where the server has one: pushed within a
  second, plus each camera's live alarm state.
- Otherwise by asking for the newest events every few seconds.

Both, and MQTT, publish through ``async_publish_event``, which drops whichever
copy of a notice arrives second.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from datetime import timedelta
import logging
import re

import aiohttp
from aiozoneminder import (
    Event,
    ZMApiError,
    ZMAuthenticationError,
    ZMConnectionError,
    ZMNotFoundError,
    ZMNotSupportedError,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from .const import SIGNAL_ALARM_STATE, SIGNAL_MQTT_EVENT
from .data import ZoneMinderConfigEntry
from .mqtt import ZoneMinderMQTTEvent

_LOGGER = logging.getLogger(__name__)

WATCH_INTERVAL = timedelta(seconds=5)
#: While the event stream is up, still check this many ticks apart (30 s): the
#: stream doesn't report the end of an event that was already running when it
#: connected, so those would otherwise only close at the next reconnect.
STREAMING_CHECK_TICKS = 6
#: How long to wait before trying the stream again after it fails.
_STREAM_BACKOFF = (5, 15, 30, 60)
#: Servers without a stream are asked again this often, in case of an upgrade.
_STREAM_RECHECK = 3600
#: Newest events looked at per check. More than enough for a few seconds.
WATCH_WINDOW = 25
#: How many (event, action) pairs to remember for de-duplication.
_PUBLISHED_MEMORY = 1000

#: zmeventnotification writes detections into the notes, e.g.
#: "[a] detected:person:97% car:81% Motion: Front".
_DETECTED = re.compile(r"detected:(.*?)(?:\bMotion:|$)", re.IGNORECASE)


@callback
def async_publish_event(
    hass: HomeAssistant, entry: ZoneMinderConfigEntry, event: ZoneMinderMQTTEvent
) -> bool:
    """Hand an event start or end to the entities, once.

    Returns False when this exact notice was already published by the other
    source.
    """
    published: OrderedDict[tuple[int, str], None] = entry.runtime_data.published
    key = (event.event_id, "start" if event.started else "end")
    if key in published:
        return False
    published[key] = None
    while len(published) > _PUBLISHED_MEMORY:
        published.popitem(last=False)
    async_dispatcher_send(hass, SIGNAL_MQTT_EVENT.format(event.monitor_id), event)
    return True


def labels_from_notes(notes: str | None) -> list[str]:
    """Return the object labels zmeventnotification left in an event's notes."""
    if not notes or not (match := _DETECTED.search(notes)):
        return []
    labels = []
    for token in re.split(r"[\s,]+", match.group(1).strip()):
        label = token.split(":", 1)[0].strip().lower()
        if label and label not in labels:
            labels.append(label)
    return labels


class ZoneMinderEventWatcher:
    """Poll the newest events and publish starts and ends."""

    def __init__(self, hass: HomeAssistant, entry: ZoneMinderConfigEntry) -> None:
        """Initialize the watcher."""
        self.hass = hass
        self.entry = entry
        #: Events seen open, waiting for their end.
        self._open: dict[int, int] = {}
        self._seen: set[int] = set()
        self._primed = False
        self._unsub: CALLBACK_TYPE | None = None
        self._busy = False
        #: True while the event stream is connected; polling pauses then.
        self.streaming = False
        self._last_event_id: int | None = None
        self._streaming_ticks = 0

    @callback
    def async_start(self) -> None:
        """Begin checking on a timer."""
        self._unsub = async_track_time_interval(
            self.hass, self._async_tick, WATCH_INTERVAL, name="zoneminder events"
        )
        self.entry.async_create_background_task(
            self.hass, self._async_run_stream(), name="zoneminder event stream"
        )

    @callback
    def async_stop(self) -> None:
        """Stop the timer."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    async def _async_tick(self, _now) -> None:
        if not self.streaming:
            await self.async_check()
            return
        self._streaming_ticks += 1
        if self._streaming_ticks % STREAMING_CHECK_TICKS == 0:
            await self.async_check()

    async def _async_run_stream(self) -> None:
        """Hold the event stream open, reconnecting for as long as we run."""
        # Prime from a poll first, so the stream resumes after what we know.
        await self.async_check()
        api = self.entry.runtime_data.coordinator.api
        failures = 0
        while self._unsub is not None:
            try:
                async for message_type, data in api.async_event_stream(
                    since=self._last_event_id
                ):
                    if not self.streaming:
                        _LOGGER.debug("ZoneMinder event stream connected")
                        self.streaming = True
                        failures = 0
                    self._handle_stream(message_type, data)
                # A clean end: the token expired. Reconnect straight away.
            except ZMNotSupportedError:
                # API v2 has no event stream; polling carries on alone.
                return
            except ZMNotFoundError:
                _LOGGER.debug("No event stream on this server; polling instead")
                self.streaming = False
                await asyncio.sleep(_STREAM_RECHECK)
                continue
            except (ZMAuthenticationError, ZMConnectionError, ZMApiError) as err:
                _LOGGER.debug("Event stream dropped: %s", err)
            except (aiohttp.ClientError, TimeoutError) as err:
                _LOGGER.debug("Event stream dropped: %s", err)
            self.streaming = False
            await asyncio.sleep(
                _STREAM_BACKOFF[min(failures, len(_STREAM_BACKOFF) - 1)]
            )
            failures += 1
            # Catch anything missed while disconnected.
            await self.async_check()

    @callback
    def _handle_stream(self, message_type: str, data: dict) -> None:
        if message_type == "alarm_state":
            async_dispatcher_send(
                self.hass,
                SIGNAL_ALARM_STATE.format(int(data["monitor_id"])),
                str(data.get("state", "unknown")),
            )
            return
        if message_type not in ("event_start", "event_end"):
            return
        try:
            event = Event.from_v3_dict(
                {**data, "id": data["event_id"], "tot_score": data.get("max_score")}
            )
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.debug("Skipping unreadable stream message: %s", err)
            return
        self._seen.add(event.id)
        self._last_event_id = max(self._last_event_id or 0, event.id)
        if message_type == "event_start":
            if event.in_progress:
                self._open[event.id] = event.monitor_id
            self._publish(event, "start")
        else:
            self._open.pop(event.id, None)
            self._publish(event, "end")

    async def async_check(self) -> None:
        """Look for new and newly finished events."""
        if self._busy:
            return
        self._busy = True
        try:
            await self._async_check()
        except (ZMApiError, ZMConnectionError) as err:
            _LOGGER.debug("Event check failed: %s", err)
        finally:
            self._busy = False

    async def _async_check(self) -> None:
        api = self.entry.runtime_data.coordinator.api
        events = await api.get_events(limit=WATCH_WINDOW)

        if events:
            self._last_event_id = max(
                self._last_event_id or 0, max(event.id for event in events)
            )

        if not self._primed:
            # What already exists at startup is history, not news. Remember
            # it so nothing fires (and no phone buzzes) on a restart.
            for event in events:
                self._seen.add(event.id)
                if event.in_progress:
                    self._open[event.id] = event.monitor_id
            self._primed = True
            return

        changed = False
        by_id = {event.id: event for event in events}
        for event in sorted(events, key=lambda e: e.id):
            if event.id in self._seen:
                continue
            self._seen.add(event.id)
            changed |= self._publish(event, "start")
            if event.in_progress:
                self._open[event.id] = event.monitor_id
            else:
                # Opened and closed between two checks.
                changed |= self._publish(event, "end")

        for event_id in list(self._open):
            event = by_id.get(event_id)
            if event is None:
                # Pushed out of the window by newer events; ask directly.
                try:
                    event = await api.get_event(event_id)
                except ZMApiError:
                    self._open.pop(event_id)
                    continue
            if not event.in_progress:
                self._open.pop(event_id)
                changed |= self._publish(event, "end")

        # Keep memory bounded to roughly what the window can show.
        if len(self._seen) > _PUBLISHED_MEMORY:
            keep = sorted(self._seen)[-WATCH_WINDOW * 4 :]
            self._seen = set(keep) | set(self._open)

        if changed:
            await self.entry.runtime_data.coordinator.async_request_refresh()

    def _publish(self, event: Event, action: str) -> bool:
        return async_publish_event(
            self.hass,
            self.entry,
            ZoneMinderMQTTEvent(
                monitor_id=event.monitor_id,
                event_id=event.id,
                action=action,
                cause=event.cause or None,
                labels=labels_from_notes(event.notes),
            ),
        )
