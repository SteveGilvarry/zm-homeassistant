"""Moving the core integration's YAML, platforms included, into a config entry."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from aiozoneminder import ZMConnectionError
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zoneminder.const import (
    CONF_EVENT_PERIODS,
    CONF_FUNCTION_OFF,
    CONF_FUNCTION_ON,
    CONF_MQTT_ENABLED,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)

SERVER = {"host": "zm.local", "username": "admin", "password": "hunter2"}

#: A typical core setup: the server, plus the platforms that went with it.
CORE_YAML: dict[str, Any] = {
    DOMAIN: [SERVER],
    "camera": [{"platform": DOMAIN}],
    "sensor": [
        {
            "platform": DOMAIN,
            "include_archived": True,
            "monitored_conditions": ["hour", "day", "all"],
            "scan_interval": 60,
        }
    ],
    "switch": [{"platform": DOMAIN, "command_on": "Modect", "command_off": "Monitor"}],
}

VALID = {"version": "1.36.33", "monitor_count": 2}


def _validate(result: Any = VALID, side_effect: Exception | None = None) -> Any:
    return patch(
        "custom_components.zoneminder.config_flow._async_validate",
        return_value=result,
        side_effect=side_effect,
    )


def _skip_setup() -> Any:
    return patch("custom_components.zoneminder.async_setup_entry", return_value=True)


async def _setup(hass: HomeAssistant, config: dict[str, Any]) -> None:
    assert await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()


async def test_platform_settings_become_options(hass: HomeAssistant) -> None:
    """Sensor periods, switch commands and polling carry over."""
    with _validate(), _skip_setup():
        await _setup(hass, CORE_YAML)

    (entry,) = hass.config_entries.async_entries(DOMAIN)
    assert entry.options == {
        CONF_MQTT_ENABLED: True,
        CONF_EVENT_PERIODS: ["hour", "day", "all"],
        CONF_FUNCTION_ON: "Modect",
        CONF_FUNCTION_OFF: "Monitor",
        CONF_SCAN_INTERVAL: 60,
    }


async def test_sensor_platform_defaults_to_all_events(hass: HomeAssistant) -> None:
    """Core's monitored_conditions defaulted to `all`."""
    with _validate(), _skip_setup():
        await _setup(hass, {DOMAIN: [SERVER], "sensor": [{"platform": DOMAIN}]})

    (entry,) = hass.config_entries.async_entries(DOMAIN)
    assert entry.options[CONF_EVENT_PERIODS] == ["all"]
    assert CONF_FUNCTION_ON not in entry.options


@pytest.mark.parametrize(
    ("raw", "seconds"), [("00:02:00", 120), (2, 5), (7200, 3600), ({"minutes": 1}, 60)]
)
async def test_scan_interval_is_parsed_and_clamped(
    hass: HomeAssistant, raw: Any, seconds: int
) -> None:
    yaml = {DOMAIN: [SERVER], "sensor": [{"platform": DOMAIN, "scan_interval": raw}]}
    with _validate(), _skip_setup():
        await _setup(hass, yaml)
    (entry,) = hass.config_entries.async_entries(DOMAIN)
    assert entry.options[CONF_SCAN_INTERVAL] == seconds


async def test_unsupported_keys_are_reported(hass: HomeAssistant) -> None:
    with (
        _validate(),
        _skip_setup(),
        patch("custom_components.zoneminder.yaml_import._LOGGER") as logger,
    ):
        await _setup(hass, CORE_YAML)
    warnings = " ".join(str(call.args) for call in logger.warning.call_args_list)
    assert "include_archived" in warnings


async def test_platform_yaml_raises_no_platform_errors(hass: HomeAssistant) -> None:
    """The platforms accept their old YAML quietly; the import handles it."""
    with _validate(), _skip_setup():
        await _setup(hass, CORE_YAML)
        for platform in ("camera", "sensor", "switch"):
            assert await async_setup_component(hass, platform, CORE_YAML)
        await hass.async_block_till_done()

    issues = ir.async_get(hass).issues
    assert not [key for key in issues if "platform_integration_no_support" in key[1]]
    assert ("homeassistant", f"deprecated_yaml_{DOMAIN}") in issues


async def test_failed_import_keeps_the_yaml(hass: HomeAssistant) -> None:
    """A server that's down at boot is not told to delete its config."""
    with _validate(side_effect=ZMConnectionError("refused")), _skip_setup():
        await _setup(hass, CORE_YAML)

    assert not hass.config_entries.async_entries(DOMAIN)
    issues = ir.async_get(hass).issues
    assert ("homeassistant", f"deprecated_yaml_{DOMAIN}") not in issues
    issue = issues[(DOMAIN, "yaml_import_failed_zm.local")]
    assert issue.translation_placeholders == {
        "host": "zm.local",
        "error": "cannot_connect",
    }


async def test_already_imported_entry_gains_platform_options(
    hass: HomeAssistant,
) -> None:
    """An entry imported before platforms were read picks up their settings.

    Options the user has since set are kept.
    """
    MockConfigEntry(
        domain=DOMAIN,
        data={"backend": "legacy", "host": "http://zm.local/zm"},
        options={CONF_MQTT_ENABLED: False, CONF_SCAN_INTERVAL: 15},
    ).add_to_hass(hass)

    with _validate(), _skip_setup():
        await _setup(hass, CORE_YAML)

    (entry,) = hass.config_entries.async_entries(DOMAIN)
    assert entry.options == {
        CONF_MQTT_ENABLED: False,
        CONF_SCAN_INTERVAL: 15,
        CONF_EVENT_PERIODS: ["hour", "day", "all"],
        CONF_FUNCTION_ON: "Modect",
        CONF_FUNCTION_OFF: "Monitor",
    }
    assert ("homeassistant", f"deprecated_yaml_{DOMAIN}") in ir.async_get(hass).issues
