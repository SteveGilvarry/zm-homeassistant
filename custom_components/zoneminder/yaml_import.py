# SPDX-License-Identifier: Apache-2.0
"""Move the core integration's YAML into config entries.

Core configured ZoneMinder in two places: the ``zoneminder:`` server list,
and per-platform blocks such as ``sensor: - platform: zoneminder``. Both are
read here and imported once per server. The YAML stays valid afterwards, so
nothing breaks while people get round to deleting it.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config import config_per_platform
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import config_validation as cv, issue_registry as ir
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import (
    CONF_EVENT_PERIODS,
    CONF_FUNCTION_OFF,
    CONF_FUNCTION_ON,
    CONF_INCLUDE_ARCHIVED,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

#: What core's sensor platform counted when monitored_conditions was unset.
_DEFAULT_PERIODS = ["all"]
#: Platform keys with nothing to map to. Reported, then ignored.
_UNSUPPORTED = ("entity_namespace",)


def platform_options(config: ConfigType) -> dict[str, Any]:
    """Turn the zoneminder platform blocks into config entry options.

    Core applied platform settings to every server, so the result is the
    same for each one.
    """
    options: dict[str, Any] = {}
    intervals: list[int] = []
    unsupported: set[str] = set()

    for domain in ("camera", "sensor", "switch", "binary_sensor"):
        for platform, block in config_per_platform(config, domain):
            if platform != DOMAIN:
                continue
            unsupported.update(
                key for key in _UNSUPPORTED if block.get(key) not in (None, False)
            )
            if (interval := block.get(CONF_SCAN_INTERVAL)) is not None:
                intervals.append(_seconds(interval))
            if domain == "sensor":
                periods = options.setdefault(CONF_EVENT_PERIODS, [])
                for period in block.get("monitored_conditions") or _DEFAULT_PERIODS:
                    if period not in periods:
                        periods.append(period)
                # Core's sensors left archived events out unless asked.
                options[CONF_INCLUDE_ARCHIVED] = options.get(
                    CONF_INCLUDE_ARCHIVED, False
                ) or bool(block.get(CONF_INCLUDE_ARCHIVED, False))
            elif domain == "switch":
                for key, option in (
                    ("command_on", CONF_FUNCTION_ON),
                    ("command_off", CONF_FUNCTION_OFF),
                ):
                    if block.get(key):
                        options[option] = str(block[key])

    if intervals:
        options[CONF_SCAN_INTERVAL] = min(intervals)
    if unsupported:
        _LOGGER.warning(
            "Ignoring %s from the old ZoneMinder YAML: this integration has no "
            "equivalent setting",
            ", ".join(sorted(unsupported)),
        )
    return options


def _seconds(value: Any) -> int:
    """Parse a YAML scan_interval and keep it within the option's range."""
    try:
        seconds = int(cv.time_period(value).total_seconds())
    except vol.Invalid:
        _LOGGER.warning("Ignoring unreadable scan_interval %r", value)
        return MAX_SCAN_INTERVAL
    return max(MIN_SCAN_INTERVAL, min(MAX_SCAN_INTERVAL, seconds))


async def async_import_server(
    hass: HomeAssistant, server: dict[str, Any], options: dict[str, Any]
) -> None:
    """Import one server, then say what to do with the YAML.

    Only a successful (or earlier) import earns the "remove your YAML"
    notice. A server that's down at boot keeps its YAML and is retried at
    the next start.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data={**server, **options}
    )
    host = str(server.get("host", ""))
    if (
        result["type"] is FlowResultType.ABORT
        and result["reason"] != "already_configured"
    ):
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"yaml_import_failed_{host}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="yaml_import_failed",
            translation_placeholders={"host": host, "error": result["reason"]},
        )
        return

    ir.async_delete_issue(hass, DOMAIN, f"yaml_import_failed_{host}")
    ir.async_create_issue(
        hass,
        HOMEASSISTANT_DOMAIN,
        f"deprecated_yaml_{DOMAIN}",
        is_fixable=False,
        issue_domain=DOMAIN,
        severity=ir.IssueSeverity.WARNING,
        translation_key="deprecated_yaml",
        translation_placeholders={"domain": DOMAIN, "integration_title": "ZoneMinder"},
    )
