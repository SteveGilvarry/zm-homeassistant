"""Tests for the card's websocket commands."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator


async def test_events_feed_the_card(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A camera's events come back oldest first, with proxied media links."""
    client = await hass_ws_client(hass)
    with patch(
        "custom_components.zoneminder.websocket_api.dt_util.utcnow",
        return_value=datetime(2026, 8, 23, 9, tzinfo=UTC),
    ):
        await client.send_json_auto_id(
            {"type": "zoneminder/events", "entity_id": "camera.back_door"}
        )
        msg = await client.receive_json()

    assert msg["success"], msg
    events = msg["result"]["events"]
    assert {e["id"] for e in events} == {297, 298}
    first = events[0]
    assert first["max_score"] == 42
    secret = setup_integration.runtime_data.proxy_secret
    assert first["video"].startswith(f"/api/zoneminder/{setup_integration.entry_id}/")
    assert secret in first["thumbnail"]


async def test_events_reject_other_entities(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Asking about something that isn't a ZoneMinder camera is an error."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "zoneminder/events", "entity_id": "camera.nope"}
    )
    msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "not_found"
