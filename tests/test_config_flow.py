"""Tests for the ZoneMinder config flow."""

from __future__ import annotations

from unittest.mock import patch

from aioresponses import aioresponses
from aiozoneminder import ZMApiError, ZMAuthenticationError, ZMConnectionError
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zoneminder.const import (
    CONF_BACKEND,
    CONF_EVENT_PERIODS,
    CONF_INCLUDE_ARCHIVED,
    CONF_MQTT_ENABLED,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)

from .const import ENTRY_DATA, HOST

USER_INPUT = {
    CONF_BACKEND: "v3",
    CONF_HOST: HOST,
    CONF_USERNAME: "admin",
    CONF_PASSWORD: "hunter2",
}


async def test_user_flow_creates_entry(
    hass: HomeAssistant, zm_api: aioresponses
) -> None:
    """A valid server produces a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == HOST
    assert result["data"][CONF_BACKEND] == "v3"
    # ZoneMinder has no serial number, and HA forbids URLs as unique ids, so
    # duplicates are caught by comparing hosts instead.
    assert result["result"].unique_id is None
    assert result["options"][CONF_MQTT_ENABLED] is True


async def test_user_flow_defaults_to_zm_api(hass: HomeAssistant) -> None:
    """zm-api is the backend a new user gets unless they choose otherwise."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    schema = result["data_schema"].schema
    backend = next(key for key in schema if str(key) == CONF_BACKEND)
    assert backend.default() == "v3"


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ZMAuthenticationError("no"), "invalid_auth"),
        (ZMConnectionError("no"), "cannot_connect"),
        (ZMApiError("no"), "api_error"),
        (RuntimeError("boom"), "unknown"),
    ],
)
async def test_user_flow_errors_recover(
    hass: HomeAssistant, zm_api: aioresponses, error: Exception, expected: str
) -> None:
    """Every failure shows a message and lets the user try again."""
    with patch(
        "custom_components.zoneminder.config_flow._async_validate", side_effect=error
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=USER_INPUT
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_duplicate_server_is_rejected(
    hass: HomeAssistant, zm_api: aioresponses, config_entry: MockConfigEntry
) -> None:
    """The same server cannot be added twice, whatever the URL's casing."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={**USER_INPUT, CONF_HOST: HOST.upper() + "/"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_updates_password(
    hass: HomeAssistant, zm_api: aioresponses, config_entry: MockConfigEntry
) -> None:
    """Re-authenticating stores the new password and reloads."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: "admin", CONF_PASSWORD: "new-password"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_PASSWORD] == "new-password"


async def test_reauth_rejects_bad_password(
    hass: HomeAssistant, zm_api: aioresponses, config_entry: MockConfigEntry
) -> None:
    """A wrong password keeps the user on the form."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)

    with patch(
        "custom_components.zoneminder.config_flow._async_validate",
        side_effect=ZMAuthenticationError("no"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_USERNAME: "admin", CONF_PASSWORD: "wrong"}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reconfigure_changes_host(
    hass: HomeAssistant, zm_api: aioresponses, config_entry: MockConfigEntry
) -> None:
    """Reconfiguring can move the entry to a new address, e.g. the zm-api port."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"

    with patch(
        "custom_components.zoneminder.config_flow._async_validate",
        return_value={"version": "1.39.22", "monitor_count": 3},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {**USER_INPUT, CONF_HOST: "http://new-server:8080/"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data[CONF_HOST] == "http://new-server:8080"
    assert config_entry.unique_id is None
    assert config_entry.title == "ZoneMinder (http://new-server:8080)"


async def test_reconfigure_rejects_address_of_other_entry(
    hass: HomeAssistant, zm_api: aioresponses, config_entry: MockConfigEntry
) -> None:
    """Reconfiguring can't take over an address another entry already uses."""
    config_entry.add_to_hass(hass)
    other = MockConfigEntry(
        domain=DOMAIN,
        data={**USER_INPUT, CONF_HOST: "http://other-server:8080"},
    )
    other.add_to_hass(hass)
    result = await config_entry.start_reconfigure_flow(hass)

    with patch(
        "custom_components.zoneminder.config_flow._async_validate",
        return_value={"version": "1.39.22", "monitor_count": 3},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {**USER_INPUT, CONF_HOST: "http://other-server:8080"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_stores_settings(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Options are saved, and blanks are dropped rather than stored empty."""
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_MQTT_ENABLED: False, CONF_SCAN_INTERVAL: 45, "mqtt_topic": ""},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert setup_integration.options[CONF_SCAN_INTERVAL] == 45
    assert "mqtt_topic" not in setup_integration.options


async def test_options_change_triggers_reload(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Changing the polling interval takes effect without a manual reload."""
    coordinator = setup_integration.runtime_data.coordinator
    assert coordinator.update_interval.total_seconds() != 45

    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_MQTT_ENABLED: False, CONF_SCAN_INTERVAL: 45}
    )
    await hass.async_block_till_done()

    reloaded = setup_integration.runtime_data.coordinator
    assert reloaded.update_interval.total_seconds() == 45


def test_entry_data_shape() -> None:
    """The fixture entry keeps the keys the integration reads."""
    assert set(ENTRY_DATA) >= {CONF_BACKEND, CONF_HOST, CONF_USERNAME, CONF_PASSWORD}


async def test_yaml_from_the_core_integration_is_imported(hass: HomeAssistant) -> None:
    """Old `zoneminder:` YAML becomes a config entry, with a nudge to delete it."""
    from homeassistant.helpers import issue_registry as ir
    from homeassistant.setup import async_setup_component

    with (
        patch(
            "custom_components.zoneminder.config_flow._async_validate",
            return_value={"version": "1.36.33", "monitor_count": 2},
        ),
        patch("custom_components.zoneminder.async_setup_entry", return_value=True),
    ):
        assert await async_setup_component(
            hass,
            DOMAIN,
            {
                DOMAIN: [
                    {
                        "host": "zm.local",
                        "path": "/zm/",
                        "ssl": True,
                        "username": "admin",
                        "password": "hunter2",
                    }
                ]
            },
        )
        await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].data["host"] == "https://zm.local/zm"
    assert entries[0].data["backend"] == "legacy"
    assert ir.async_get(hass).async_get_issue(
        "homeassistant", "deprecated_yaml_zoneminder"
    )


async def test_yaml_zms_path_is_kept(hass: HomeAssistant) -> None:
    """The old integration's path_zms carries over, so streams keep working."""
    from homeassistant.setup import async_setup_component

    with (
        patch(
            "custom_components.zoneminder.config_flow._async_validate",
            return_value={"version": "1.36.33", "monitor_count": 2},
        ),
        patch("custom_components.zoneminder.async_setup_entry", return_value=True),
    ):
        assert await async_setup_component(
            hass,
            DOMAIN,
            {
                DOMAIN: [
                    {
                        "host": "zm.local",
                        "path_zms": "/cgi-bin-zm/nph-zms",
                        "username": "admin",
                        "password": "hunter2",
                    }
                ]
            },
        )
        await hass.async_block_till_done()

    (entry,) = hass.config_entries.async_entries(DOMAIN)
    assert entry.data["path_zms"] == "/cgi-bin-zm/nph-zms"


async def test_stored_zms_path_reaches_the_client(hass: HomeAssistant) -> None:
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from custom_components.zoneminder.api import client_from_entry_data

    client = client_from_entry_data(
        {
            "backend": "legacy",
            CONF_HOST: "http://zm.local/zm",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "hunter2",
            "path_zms": "/cgi-bin-zm/nph-zms",
        },
        async_get_clientsession(hass),
    )
    assert client.get_stream_url(1).startswith("http://zm.local/cgi-bin-zm/nph-zms?")


async def test_options_flow_sets_event_count_periods(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_MQTT_ENABLED: False, CONF_EVENT_PERIODS: ["day", "week"]},
    )
    await hass.async_block_till_done()
    assert setup_integration.options[CONF_EVENT_PERIODS] == ["day", "week"]


async def test_options_flow_sets_include_archived(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_MQTT_ENABLED: False, CONF_INCLUDE_ARCHIVED: False}
    )
    await hass.async_block_till_done()
    assert setup_integration.options[CONF_INCLUDE_ARCHIVED] is False
