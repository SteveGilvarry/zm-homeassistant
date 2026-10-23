"""Tests for parsing ZoneMinder's MQTT messages."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from custom_components.zoneminder.mqtt import ZoneMinderMQTTListener


@pytest.fixture
def listener() -> ZoneMinderMQTTListener:
    """Return a listener with ZoneMinder's default topic prefix."""
    return ZoneMinderMQTTListener(MagicMock(), MagicMock(), MagicMock(), "ZoneMinder")


def test_parses_event_start(listener: ZoneMinderMQTTListener) -> None:
    """The payload ZoneMinder actually publishes is understood."""
    event = listener.parse("ZoneMinder/monitor/4", "event start: 423")
    assert event is not None
    assert (event.monitor_id, event.event_id, event.action) == (4, 423, "start")
    assert event.started is True


def test_parses_event_end(listener: ZoneMinderMQTTListener) -> None:
    """End messages close the event they name."""
    event = listener.parse("ZoneMinder/monitor/4", "event end: 423")
    assert event is not None
    assert event.action == "end"
    assert event.started is False


@pytest.mark.parametrize(
    "payload",
    [
        "Capturing at 10.03 fps, Analysing at 0.00 fps",
        "",
        "event start:",
        "something else entirely",
    ],
)
def test_ignores_status_chatter(listener: ZoneMinderMQTTListener, payload: str) -> None:
    """ZoneMinder mixes status lines onto the same topic."""
    assert listener.parse("ZoneMinder/monitor/4", payload) is None


def test_ignores_other_topics(listener: ZoneMinderMQTTListener) -> None:
    """Messages from another prefix are not ours."""
    assert listener.parse("SomethingElse/monitor/4", "event start: 1") is None


def test_topic_prefix_is_configurable() -> None:
    """The prefix was hardcoded before, so a custom one never matched."""
    listener = ZoneMinderMQTTListener(
        MagicMock(), MagicMock(), MagicMock(), "cameras/zm"
    )
    assert listener.topic == "cameras/zm/monitor/+"
    event = listener.parse("cameras/zm/monitor/7", "event start: 9")
    assert event is not None
    assert event.monitor_id == 7


def test_parses_bytes_payload(listener: ZoneMinderMQTTListener) -> None:
    """MQTT payloads can arrive as bytes."""
    event = listener.parse("ZoneMinder/monitor/2", b"event start: 55")
    assert event is not None
    assert event.event_id == 55


def test_parses_object_detection_json(listener: ZoneMinderMQTTListener) -> None:
    """zmeventnotification publishes JSON carrying detection labels."""
    payload = json.dumps(
        {
            "eventid": "812",
            "name": "Front door",
            "cause": "Motion",
            "detection": [{"label": "person", "confidence": "97%"}, {"label": "car"}],
        }
    )
    event = listener.parse("ZoneMinder/monitor/1", payload)
    assert event is not None
    assert event.event_id == 812
    assert event.labels == ["person", "car"]
    assert event.cause == "Motion"


def test_parses_comma_separated_labels(listener: ZoneMinderMQTTListener) -> None:
    """Older hook scripts send the labels as one string."""
    payload = json.dumps({"eventid": 5, "detection": "person, dog"})
    event = listener.parse("ZoneMinder/monitor/1", payload)
    assert event is not None
    assert event.labels == ["person", "dog"]


def test_ignores_json_without_an_event_id(listener: ZoneMinderMQTTListener) -> None:
    """A JSON payload we cannot tie to an event is not actionable."""
    assert listener.parse("ZoneMinder/monitor/1", '{"foo": "bar"}') is None
