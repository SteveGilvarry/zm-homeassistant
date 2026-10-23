"""Tests for setting the ZoneMinder integration up and tearing it down."""

from __future__ import annotations

from unittest.mock import patch

from aioresponses import aioresponses
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zoneminder.const import DOMAIN

from .const import HOST


async def test_setup_and_unload(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The entry loads, exposes runtime data and unloads cleanly."""
    assert setup_integration.state is ConfigEntryState.LOADED
    assert setup_integration.runtime_data.coordinator.data.monitors

    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()
    assert setup_integration.state is ConfigEntryState.NOT_LOADED


async def test_setup_fails_when_unreachable(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """An unreachable server leaves the entry retrying rather than broken."""
    config_entry.add_to_hass(hass)
    with aioresponses() as mocked:
        mocked.post(f"{HOST}/api/v3/auth/login", exception=TimeoutError())
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_starts_reauth_on_bad_credentials(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Rejected credentials start a re-authentication flow."""
    config_entry.add_to_hass(hass)
    with aioresponses() as mocked:
        mocked.post(f"{HOST}/api/v3/auth/login", status=401)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(flow["context"]["source"] == "reauth" for flow in flows)


async def test_no_setup_notification(
    hass: HomeAssistant, config_entry: MockConfigEntry, zm_api: aioresponses
) -> None:
    """Setting up must not nag the user on every restart."""
    config_entry.add_to_hass(hass)
    with patch(
        "homeassistant.components.persistent_notification.async_create"
    ) as notify:
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    notify.assert_not_called()


async def test_monitors_hang_off_a_server_device(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Each monitor is a device linked to the ZoneMinder server device."""
    devices = dr.async_get(hass)
    server = devices.async_get_device(
        identifiers={(DOMAIN, setup_integration.entry_id)}
    )
    assert server is not None
    assert server.model == "ZoneMinder server"

    monitor = devices.async_get_device(
        identifiers={(DOMAIN, f"{setup_integration.entry_id}_1")}
    )
    assert monitor is not None
    assert monitor.name == "Driveway"
    assert monitor.via_device_id == server.id


async def test_only_stale_devices_can_be_removed(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Leftovers can be deleted from the UI, live devices can't."""
    from custom_components.zoneminder import async_remove_config_entry_device

    devices = dr.async_get(hass)
    entry = setup_integration

    # A device from the old identifier scheme (bare monitor id 1), whose
    # monitor still exists under the entry-scoped id.
    stale = devices.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "1")}
    )
    # A monitor that has since been deleted in ZoneMinder.
    deleted = devices.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, f"{entry.entry_id}_99")}
    )
    live = devices.async_get_device(identifiers={(DOMAIN, f"{entry.entry_id}_1")})
    server = devices.async_get_device(identifiers={(DOMAIN, entry.entry_id)})

    assert await async_remove_config_entry_device(hass, entry, stale)
    assert await async_remove_config_entry_device(hass, entry, deleted)
    assert not await async_remove_config_entry_device(hass, entry, live)
    assert not await async_remove_config_entry_device(hass, entry, server)


async def test_unique_ids_are_scoped_to_the_entry(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Two ZoneMinder servers must not fight over the same unique ids."""
    entities = er.async_get(hass)
    camera = entities.async_get("camera.driveway")
    assert camera is not None
    assert camera.unique_id.startswith(setup_integration.entry_id)
    assert camera.unique_id == f"{setup_integration.entry_id}_1_camera"


async def test_expected_entities_exist(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The platforms produce the entities the documentation promises."""
    states = hass.states.async_entity_ids()

    assert "camera.driveway" in states
    assert "binary_sensor.driveway_motion" in states
    assert "event.driveway_event" in states
    assert "select.driveway_capturing" in states
    assert "select.driveway_analysing" in states
    assert "select.driveway_recording" in states
    assert "sensor.driveway_last_event" in states
    assert "button.driveway_trigger_alarm" in states


async def test_ptz_entities_only_for_controllable_monitors(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """A fixed camera gets no PTZ buttons that would silently do nothing."""
    states = hass.states.async_entity_ids("button")

    # Monitor 3 ("Gate") is the only controllable one in the fixtures.
    assert any("gate" in entity and "home" in entity for entity in states)
    assert not any("driveway" in entity and "home" in entity for entity in states)


async def test_ptz_presets_become_buttons(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Stored PTZ presets are exposed as buttons."""
    assert setup_integration.runtime_data.ptz_presets == {3: {1: "Front gate"}}
    assert hass.states.get("button.gate_front_gate") is not None


async def test_card_ships_with_the_integration(
    hass: HomeAssistant, config_entry: MockConfigEntry, zm_api, hass_client
) -> None:
    """The card is served and added to every dashboard without a manual resource."""
    from custom_components.zoneminder.frontend import CARD_URL

    hass.config.components.add("frontend")
    config_entry.add_to_hass(hass)
    with patch(
        "homeassistant.components.frontend.add_extra_js_url", create=True
    ) as add_js:
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    add_js.assert_called_once()
    assert add_js.call_args.args[1].startswith(f"{CARD_URL}?v=")

    client = await hass_client()
    response = await client.get(CARD_URL)
    assert response.status == 200
    assert "zoneminder-card" in await response.text()
