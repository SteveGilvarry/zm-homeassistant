# SPDX-License-Identifier: AGPL-3.0-or-later
"""Real-time ZoneMinder events over MQTT.

ZoneMinder publishes one topic per monitor under its ``ZM_MQTT_TOPIC_PREFIX``
and mixes two kinds of payload on it: periodic status lines and event
start/end notices. Only the latter are interesting, and they arrive well under
a second after the event opens, which is what makes motion entities feel
instant instead of poll-shaped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import re
from typing import TYPE_CHECKING, Any

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import SIGNAL_MQTT_EVENT

if TYPE_CHECKING:
    from .coordinator import ZoneMinderDataUpdateCoordinator
    from .data import ZoneMinderConfigEntry

_LOGGER = logging.getLogger(__name__)

#: "event start: 423" / "event end: 423", the payloads ZoneMinder publishes.
_EVENT_PAYLOAD = re.compile(r"^\s*event\s+(start|end)\s*:\s*(\d+)\s*$", re.IGNORECASE)


@dataclass
class ZoneMinderMQTTEvent:
    """A parsed ZoneMinder MQTT notification."""

    monitor_id: int
    event_id: int
    action: str
    cause: str | None = None
    labels: list[str] = field(default_factory=list)

    @property
    def started(self) -> bool:
        """Return True when this marks the start of an event."""
        return self.action == "start"


class ZoneMinderMQTTListener:
    """Subscribe to ZoneMinder's MQTT topics and fan events out to entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ZoneMinderConfigEntry,
        coordinator: ZoneMinderDataUpdateCoordinator,
        topic_prefix: str,
    ) -> None:
        """Initialize the listener."""
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self.topic_prefix = topic_prefix.rstrip("/")
        self._unsubscribe: Any = None
        self._topic_pattern = re.compile(
            re.escape(self.topic_prefix) + r"/monitor/(\d+)\b"
        )

    @property
    def topic(self) -> str:
        """Return the wildcard topic this listener subscribes to."""
        return f"{self.topic_prefix}/monitor/+"

    async def async_setup(self) -> bool:
        """Subscribe, if Home Assistant has a working MQTT connection."""
        try:
            if not await mqtt.async_wait_for_mqtt_client(self.hass):
                _LOGGER.warning(
                    "The MQTT integration is not available, so ZoneMinder "
                    "real-time events are disabled"
                )
                return False
        except KeyError:
            # The MQTT integration is not set up at all.
            _LOGGER.warning(
                "The MQTT integration is not set up, so ZoneMinder real-time "
                "events are disabled"
            )
            return False

        self._unsubscribe = await mqtt.async_subscribe(
            self.hass, self.topic, self._async_message_received, qos=1
        )
        _LOGGER.info("Subscribed to ZoneMinder MQTT topic %s", self.topic)
        return True

    async def async_unsubscribe(self) -> None:
        """Stop listening."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    @callback
    def _async_message_received(self, msg: mqtt.ReceiveMessage) -> None:
        """Handle one MQTT message."""
        event = self.parse(msg.topic, msg.payload)
        if event is None:
            return

        _LOGGER.debug(
            "ZoneMinder MQTT: monitor %d event %d %s",
            event.monitor_id,
            event.event_id,
            event.action,
        )

        async_dispatcher_send(
            self.hass, SIGNAL_MQTT_EVENT.format(event.monitor_id), event
        )

        # Pull the full event record so attributes catch up with the state we
        # have already published. Tied to the entry so it dies on unload.
        self.entry.async_create_background_task(
            self.hass,
            self.coordinator.async_request_refresh(),
            name=f"zoneminder refresh after event {event.event_id}",
        )

    def parse(self, topic: str, payload: str | bytes) -> ZoneMinderMQTTEvent | None:
        """Parse a ZoneMinder MQTT message, or return None if it is not one.

        Handles both the plain ``event start: <id>`` lines ZoneMinder emits and
        the JSON payloads produced by zmeventnotification, which carry object
        detection labels.
        """
        monitor_match = self._topic_pattern.match(topic)
        if not monitor_match:
            return None
        monitor_id = int(monitor_match.group(1))

        if isinstance(payload, bytes):
            try:
                payload = payload.decode()
            except UnicodeDecodeError:
                return None

        if (match := _EVENT_PAYLOAD.match(payload)) is not None:
            return ZoneMinderMQTTEvent(
                monitor_id=monitor_id,
                event_id=int(match.group(2)),
                action=match.group(1).lower(),
            )

        stripped = payload.strip()
        if stripped.startswith("{"):
            return self._parse_json(monitor_id, stripped)

        # Status chatter such as "Capturing at 10.03 fps". Nothing to do.
        return None

    def _parse_json(self, monitor_id: int, payload: str) -> ZoneMinderMQTTEvent | None:
        """Parse a zmeventnotification JSON payload."""
        try:
            data = json.loads(payload)
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None

        event_id = data.get("eventid") or data.get("event_id") or data.get("EventId")
        if event_id is None:
            return None
        try:
            event_id = int(event_id)
        except (TypeError, ValueError):
            return None

        state = str(data.get("state") or data.get("status") or "start").lower()
        action = "end" if state in ("end", "stop", "ended") else "start"

        return ZoneMinderMQTTEvent(
            monitor_id=monitor_id,
            event_id=event_id,
            action=action,
            cause=data.get("cause") or data.get("name"),
            labels=_extract_labels(data),
        )


def _extract_labels(data: dict[str, Any]) -> list[str]:
    """Pull object detection labels out of a zmeventnotification payload.

    The hook scripts have used several shapes over the years, so this accepts
    a list of strings, a list of ``{"label": ...}`` objects, or a comma
    separated string, and ignores anything else.
    """
    raw = data.get("detection") or data.get("detections") or data.get("labels")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    if not isinstance(raw, list):
        return []

    labels = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            labels.append(item.strip())
        elif isinstance(item, dict):
            label = item.get("label") or item.get("name") or item.get("type")
            if isinstance(label, str) and label.strip():
                labels.append(label.strip())
    return labels
