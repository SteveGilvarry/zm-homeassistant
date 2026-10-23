"""Tests for the per-event links put in notifications."""

from __future__ import annotations

from aioresponses import aioresponses
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zoneminder.const import CONF_NOTIFY_KEY, SIGNAL_MQTT_EVENT
from custom_components.zoneminder.mqtt import ZoneMinderMQTTEvent
from custom_components.zoneminder.notify_media import async_event_media_urls

from .const import HOST


async def test_events_carry_their_own_links(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Start and end both fire, each with links that open only that event."""
    async_dispatcher_send(
        hass,
        SIGNAL_MQTT_EVENT.format(2),
        ZoneMinderMQTTEvent(monitor_id=2, event_id=298, action="start"),
    )
    await hass.async_block_till_done()
    started = hass.states.get("event.back_door_event").attributes

    assert started["event_type"] == "motion"
    assert started["thumbnail_url"].startswith(
        f"/api/zoneminder/event/{setup_integration.entry_id}/298/"
    )
    # The live-stream proxy secret must never leave Home Assistant in a link.
    secret = setup_integration.runtime_data.proxy_secret
    assert secret not in started["thumbnail_url"]
    assert secret not in started["clip_url"]

    async_dispatcher_send(
        hass,
        SIGNAL_MQTT_EVENT.format(2),
        ZoneMinderMQTTEvent(monitor_id=2, event_id=298, action="end"),
    )
    await hass.async_block_till_done()
    ended = hass.states.get("event.back_door_event").attributes
    assert ended["event_type"] == "ended"
    assert ended["clip_url"] == started["clip_url"]


async def test_links_survive_a_restart(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The signing key is stored, so links in old notifications keep working."""
    key = setup_integration.data[CONF_NOTIFY_KEY]
    before = async_event_media_urls(setup_integration, 298)

    assert await hass.config_entries.async_reload(setup_integration.entry_id)
    await hass.async_block_till_done()

    assert setup_integration.data[CONF_NOTIFY_KEY] == key
    assert async_event_media_urls(setup_integration, 298) == before


async def test_a_signed_link_serves_its_event_only(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    zm_api: aioresponses,
    hass_client_no_auth,
) -> None:
    """The phone needs no login; a wrong or reused signature gets nothing."""
    zm_api.get(
        f"{HOST}/api/v3/events/298/thumbnail",
        body=b"\xff\xd8jpeg",
        content_type="image/jpeg",
        repeat=True,
    )
    client = await hass_client_no_auth()
    good = async_event_media_urls(setup_integration, 298)["thumbnail_url"]

    response = await client.get(good)
    assert response.status == 200
    assert await response.read() == b"\xff\xd8jpeg"

    # Event 298's signature does not open event 297.
    assert (await client.get(good.replace("/298/", "/297/"))).status == 404
    assert (await client.get(good.replace("thumbnail.jpg", "secrets"))).status == 404
    tampered = good.rsplit("/", 2)
    assert (
        await client.get(f"{tampered[0]}/AAAA{tampered[1][4:]}/{tampered[2]}")
    ).status == 404
