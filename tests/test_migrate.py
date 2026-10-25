"""Moving entries made by nabbi/ha-zoneminder onto this integration."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zoneminder.const import (
    CONF_EVENT_PERIODS,
    CONF_FUNCTION_OFF,
    CONF_FUNCTION_ON,
    CONF_MQTT_ENABLED,
    CONF_STREAM_MAXFPS,
    CONF_STREAM_SCALE,
    DOMAIN,
)

from .const import ENTRY_DATA, ENTRY_OPTIONS

#: What nabbi's config flow (and core's short-lived 2020 one) stored.
NABBI_DATA = {
    "host": "zm.example.com",
    "ssl": True,
    "path": "/zm/",
    "path_zms": "/zm/cgi-bin/nph-zms",
    "verify_ssl": False,
    "username": "admin",
    "password": "hunter2",
}
NABBI_OPTIONS = {
    "include_archived": False,
    "monitored_conditions": ["all", "day"],
    "command_on": "Modect",
    "command_off": "Monitor",
    "stream_scale": 50,
    "stream_maxfps": 5.0,
}


def _nabbi_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        title="zm.example.com",
        unique_id="zm.example.com",
        data=NABBI_DATA,
        options=NABBI_OPTIONS,
    )
    entry.add_to_hass(hass)
    return entry


async def _migrate(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    with patch("custom_components.zoneminder.async_setup_entry", return_value=True):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def test_nabbi_entry_becomes_an_api_v2_entry(hass: HomeAssistant) -> None:
    entry = _nabbi_entry(hass)
    await _migrate(hass, entry)

    assert entry.version == 2
    assert entry.unique_id is None
    assert entry.data == {
        "backend": "legacy",
        "host": "https://zm.example.com/zm",
        "username": "admin",
        "password": "hunter2",
        "verify_ssl": False,
        "path_zms": "/zm/cgi-bin/nph-zms",
    }
    assert entry.options == {
        CONF_MQTT_ENABLED: True,
        CONF_EVENT_PERIODS: ["all", "day"],
        CONF_FUNCTION_ON: "Modect",
        CONF_FUNCTION_OFF: "Monitor",
        CONF_STREAM_SCALE: 50,
        CONF_STREAM_MAXFPS: 5.0,
    }


async def test_nabbi_entities_and_devices_keep_their_history(
    hass: HomeAssistant,
) -> None:
    """Unique ids and device identifiers move to ours, so entity ids survive."""
    entry = _nabbi_entry(hass)
    entities = er.async_get(hass)
    devices = dr.async_get(hass)
    server = devices.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "zm.example.com")}
    )
    camera = devices.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "zm.example.com_3")}
    )
    old_to_new = {
        ("camera", "zm.example.com_3"): f"{entry.entry_id}_3_camera",
        ("sensor", "zm.example.com_3_status"): f"{entry.entry_id}_3_mode",
        ("sensor", "zm.example.com_3_events_all"): f"{entry.entry_id}_3_events_total",
        ("sensor", "zm.example.com_3_events_day"): f"{entry.entry_id}_3_events_today",
        ("select", "zm.example.com_3_recording"): f"{entry.entry_id}_3_recording",
        ("switch", "zm.example.com_3_switch"): f"{entry.entry_id}_3_function",
        ("select", "zm.example.com_run_state_select"): (
            f"{entry.entry_id}_server_run_state"
        ),
        ("binary_sensor", "zm.example.com_availability"): (
            f"{entry.entry_id}_server_running"
        ),
    }
    created = {
        key: entities.async_get_or_create(
            key[0], DOMAIN, key[1], config_entry=entry, suggested_object_id=key[1]
        ).entity_id
        for key in old_to_new
    }
    # Nothing here replaces the force alarm switch, so it's left alone.
    force_alarm = entities.async_get_or_create(
        "switch", DOMAIN, "zm.example.com_3_force_alarm", config_entry=entry
    )

    await _migrate(hass, entry)

    for (platform, _old), new in old_to_new.items():
        entity_id = entities.async_get_entity_id(platform, DOMAIN, new)
        assert entity_id == created[(platform, _old)]
    assert entities.async_get(force_alarm.entity_id).unique_id == (
        "zm.example.com_3_force_alarm"
    )
    assert devices.async_get(server.id).identifiers == {(DOMAIN, entry.entry_id)}
    assert devices.async_get(camera.id).identifiers == {(DOMAIN, f"{entry.entry_id}_3")}


async def test_our_own_entries_lose_their_url_unique_id(hass: HomeAssistant) -> None:
    """Version 1 used the server URL as unique id, which HA doesn't allow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id="http://192.168.0.45:8080",
        data=ENTRY_DATA,
        options=ENTRY_OPTIONS,
    )
    entry.add_to_hass(hass)
    await _migrate(hass, entry)
    assert entry.version == 2
    assert entry.unique_id is None
    assert entry.data == ENTRY_DATA
    assert entry.options == ENTRY_OPTIONS


async def test_entries_from_a_newer_version_are_refused(hass: HomeAssistant) -> None:
    """A downgrade must not load an entry it doesn't understand."""
    entry = MockConfigEntry(domain=DOMAIN, version=3, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    with patch("custom_components.zoneminder.async_setup_entry", return_value=True):
        assert not await hass.config_entries.async_setup(entry.entry_id)


async def test_early_version_2_entries_lose_their_url_unique_id(
    hass: HomeAssistant,
) -> None:
    """Version 2.1 entries kept the URL unique id; 2.2 drops it."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        minor_version=1,
        unique_id="http://192.168.0.45:8080",
        data=ENTRY_DATA,
        options=ENTRY_OPTIONS,
    )
    entry.add_to_hass(hass)
    await _migrate(hass, entry)
    assert (entry.version, entry.minor_version) == (2, 2)
    assert entry.unique_id is None
