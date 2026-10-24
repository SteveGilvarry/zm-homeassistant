# SPDX-License-Identifier: Apache-2.0
"""Repair issues raised by the ZoneMinder integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .data import ZoneMinderConfigEntry

ISSUE_MQTT_NOT_PUBLISHING = "mqtt_not_publishing"
ISSUE_NO_INTERNAL_URL = "no_internal_url"


@callback
def async_check_issues(hass: HomeAssistant, entry: ZoneMinderConfigEntry) -> None:
    """Raise or clear the issues this integration knows how to explain."""
    _check_mqtt(hass, entry)


@callback
def _check_mqtt(hass: HomeAssistant, entry: ZoneMinderConfigEntry) -> None:
    """Warn when MQTT is on in Home Assistant but off in ZoneMinder.

    Subscribing succeeds either way, so without this the only symptom is
    motion that updates on the polling interval instead of instantly, which is
    easy to mistake for the integration being slow.
    """
    runtime = entry.runtime_data
    issue_id = f"{ISSUE_MQTT_NOT_PUBLISHING}_{entry.entry_id}"

    monitors = runtime.coordinator.data.monitors.values()
    publishing = [monitor for monitor in monitors if monitor.mqtt_enabled]

    if runtime.mqtt_listener is None or not monitors or publishing:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return

    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_MQTT_NOT_PUBLISHING,
        translation_placeholders={
            "name": entry.title,
            "topic": runtime.mqtt_listener.topic,
        },
        learn_more_url="https://github.com/SteveGilvarry/zm-homeassistant#real-time-events-mqtt",
    )


@callback
def async_no_internal_url_issue(
    hass: HomeAssistant, entry: ZoneMinderConfigEntry
) -> None:
    """Explain that live streams need an internal Home Assistant URL."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{ISSUE_NO_INTERNAL_URL}_{entry.entry_id}",
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=ISSUE_NO_INTERNAL_URL,
        translation_placeholders={"name": entry.title},
    )
