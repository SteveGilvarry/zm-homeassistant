"""Tests for the run state select (Home, Away and so on)."""

from __future__ import annotations

from unittest.mock import patch

from aioresponses import aioresponses
from aiozoneminder import RunState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zoneminder.const import DOMAIN

from .const import HOST


def test_both_definition_formats_parse() -> None:
    """1.37+ stores split modes; older servers store Function and Enabled."""
    new = RunState(1, "Away", "1:Always:Always:OnMotion,2:None:None:None", False)
    assert new.monitor_modes() == {
        1: ("Always", "Always", "OnMotion"),
        2: ("None", "None", "None"),
    }

    old = RunState(2, "Night", "1:Modect:1,2:Record:1,3:Monitor:0", False)
    assert old.monitor_modes() == {
        1: ("Always", "Always", "OnMotion"),
        2: ("Always", "Always", "Always"),
        3: ("None", "None", "None"),
    }


async def test_run_state_select_shows_the_active_state(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The server device gets one select listing ZoneMinder's run states."""
    state = hass.states.get("select.zoneminder_test_run_state")
    assert state.state == "Home"
    assert state.attributes["options"] == ["default", "Home", "Away"]


async def test_switching_run_state_updates_only_what_differs(
    hass: HomeAssistant, setup_integration: MockConfigEntry, zm_api: aioresponses
) -> None:
    """Away arms analysis; monitors already matching are left alone."""
    zm_api.patch(f"{HOST}/api/v3/monitors/1", payload={}, repeat=True)
    zm_api.patch(f"{HOST}/api/v3/monitors/2", payload={}, repeat=True)
    zm_api.patch(f"{HOST}/api/v3/monitors/3", payload={}, repeat=True)
    zm_api.patch(f"{HOST}/api/v3/states/2", payload={}, repeat=True)
    zm_api.patch(f"{HOST}/api/v3/states/3", payload={}, repeat=True)

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.zoneminder_test_run_state", "option": "Away"},
        blocking=True,
    )

    patched = {
        str(url): [c.kwargs.get("json") for c in calls]
        for (method, url), calls in zm_api.requests.items()
        if method == "PATCH"
    }
    # Monitor 2 already matches Away, so it is left alone.
    assert patched[f"{HOST}/api/v3/monitors/1"] == [
        {"capturing": "Always", "analysing": "Always", "recording": "Always"}
    ]
    assert f"{HOST}/api/v3/monitors/2" not in patched
    assert patched[f"{HOST}/api/v3/states/3"] == [{"is_active": 1}]
    assert patched[f"{HOST}/api/v3/states/2"] == [{"is_active": 0}]


async def test_save_run_state_snapshots_the_cameras(
    hass: HomeAssistant, setup_integration: MockConfigEntry, zm_api: aioresponses
) -> None:
    """Saving "Night" stores every camera's current modes in ZoneMinder."""
    zm_api.post(f"{HOST}/api/v3/states", payload={}, repeat=True)

    await hass.services.async_call(
        "zoneminder", "save_run_state", {"name": "Night"}, blocking=True
    )

    posted = [
        c.kwargs["json"]
        for (method, url), calls in zm_api.requests.items()
        if method == "POST" and str(url) == f"{HOST}/api/v3/states"
        for c in calls
    ]
    assert posted == [
        {
            "name": "Night",
            "definition": (
                "1:Always:None:Always,2:Always:Always:OnMotion,3:Always:None:Always"
            ),
        }
    ]


async def test_no_select_until_there_is_a_choice(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """A server with only ZoneMinder's "default" state gets no run state select."""
    from .conftest import _url, register_zm_api
    from .const import RUN_STATES, paginated

    with aioresponses(passthrough=["http://127.0.0.1"]) as mocked:
        mocked.get(
            _url("api/v3/states"), payload=paginated(RUN_STATES[:1]), repeat=True
        )
        register_zm_api(mocked)
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get("select.zoneminder_test_run_state") is None


# -- zoneminder.set_run_state, as the core integration offered it ------------------


async def _set_run_state(hass: HomeAssistant, **data: str) -> None:
    await hass.services.async_call(DOMAIN, "set_run_state", data, blocking=True)


async def test_set_run_state_service_switches_by_name(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Core's service keeps working, so old automations don't break."""
    coordinator = setup_integration.runtime_data.coordinator
    with patch.object(coordinator, "async_set_run_state") as switch:
        await _set_run_state(hass, name="Away")
    switch.assert_awaited_once_with("Away")


async def test_set_run_state_service_matches_the_old_server_id(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Core identified servers by their YAML host, which `id` still accepts."""
    coordinator = setup_integration.runtime_data.coordinator
    with patch.object(coordinator, "async_set_run_state") as switch:
        await _set_run_state(hass, id="192.168.0.45:8080", name="Home")
    switch.assert_awaited_once_with("Home")

    with pytest.raises(ServiceValidationError) as err:
        await _set_run_state(hass, id="elsewhere.local", name="Home")
    assert err.value.translation_key == "unknown_server"


@pytest.mark.parametrize("action", ["stop", "restart", "start"])
async def test_set_run_state_service_controls_zoneminder(
    hass: HomeAssistant, setup_integration: MockConfigEntry, action: str
) -> None:
    """zmpkg.pl took start, stop and restart as state names, so core did too."""
    api = setup_integration.runtime_data.coordinator.api
    with patch.object(api, "server_control") as control:
        await _set_run_state(hass, name=action)
    control.assert_awaited_once_with(action)


async def test_set_run_state_service_rejects_unknown_states(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    with pytest.raises(ServiceValidationError) as err:
        await _set_run_state(hass, name="Holiday")
    assert err.value.translation_key == "unknown_run_state"
    assert err.value.translation_placeholders == {
        "name": "Holiday",
        "options": "default, Home, Away",
    }
