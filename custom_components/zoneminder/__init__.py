"""ZoneMinder integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

__version__ = "0.1.0"

_LOGGER = logging.getLogger(__name__)

# Platforms to forward entry setup to
PLATFORMS: list[Platform] = []  # Will be populated in future phases


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ZoneMinder from a config entry."""
    _LOGGER.info("Setting up ZoneMinder integration for %s", entry.data.get("host"))

    # Store entry data in hass.data for future use
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
    }

    # TODO: Initialize API client and coordinator in Phase 3
    # TODO: Forward to platforms in Phase 3

    _LOGGER.info("ZoneMinder integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading ZoneMinder integration")

    # TODO: Unload platforms in Phase 3
    # TODO: Close API client in Phase 3

    # Remove stored data
    hass.data[DOMAIN].pop(entry.entry_id, None)

    return True
