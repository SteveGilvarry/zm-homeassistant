"""The function switch that replaces the core integration's switch platform."""

from __future__ import annotations

from unittest.mock import patch

from aioresponses import aioresponses
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zoneminder.const import (
    CONF_FUNCTION_OFF,
    CONF_FUNCTION_ON,
    DOMAIN,
)


async def _setup(
    hass: HomeAssistant, entry: MockConfigEntry, **options: str
) -> MockConfigEntry:
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={**entry.options, **options})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_switch_shows_whether_the_on_mode_is_set(
    hass: HomeAssistant, config_entry: MockConfigEntry, zm_api: aioresponses
) -> None:
    """Back door is in Modect; Driveway records continuously."""
    await _setup(
        hass, config_entry, **{CONF_FUNCTION_ON: "Modect", CONF_FUNCTION_OFF: "Monitor"}
    )
    assert hass.states.get("switch.back_door_modect").state == "on"
    assert hass.states.get("switch.driveway_modect").state == "off"


async def test_switch_sets_the_modes(
    hass: HomeAssistant, config_entry: MockConfigEntry, zm_api: aioresponses
) -> None:
    entry = await _setup(
        hass, config_entry, **{CONF_FUNCTION_ON: "Modect", CONF_FUNCTION_OFF: "Monitor"}
    )
    api = entry.runtime_data.coordinator.api
    with patch.object(api, "set_monitor_state") as set_state:
        await hass.services.async_call(
            "switch",
            "turn_on",
            {ATTR_ENTITY_ID: "switch.driveway_modect"},
            blocking=True,
        )
        await hass.services.async_call(
            "switch",
            "turn_off",
            {ATTR_ENTITY_ID: "switch.back_door_modect"},
            blocking=True,
        )
    assert [
        call.args + tuple(sorted(call.kwargs.items()))
        for call in set_state.await_args_list
    ] == [
        (
            1,
            ("analysing", "Always"),
            ("capturing", "Always"),
            ("recording", "OnMotion"),
        ),
        (2, ("analysing", "None"), ("capturing", "Always"), ("recording", "None")),
    ]


async def test_no_switch_without_the_options(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Most people never had the core switch, so it's opt-in."""
    assert not hass.states.async_entity_ids("switch")


async def test_set_monitor_state_takes_a_function(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Core-era modes like Mocord work in the service too."""
    api = setup_integration.runtime_data.coordinator.api
    with patch.object(api, "set_monitor_state") as set_state:
        await hass.services.async_call(
            DOMAIN,
            "set_monitor_state",
            {ATTR_ENTITY_ID: "camera.driveway", "function": "Mocord"},
            blocking=True,
        )
    set_state.assert_awaited_once_with(
        1, capturing="Always", analysing="Always", recording="Always"
    )
