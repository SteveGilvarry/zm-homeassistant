#!/usr/bin/env python3
"""Test script to verify the integration can be loaded and camera entities created."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from custom_components.zoneminder.coordinator import async_get_coordinator
from custom_components.zoneminder.models import Monitor

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Suppress aiohttp debug logs
logging.getLogger("aiohttp").setLevel(logging.INFO)

_LOGGER = logging.getLogger(__name__)


class MockConfigEntry:
    """Mock Home Assistant ConfigEntry."""

    def __init__(self, data, options):
        self.data = data
        self.options = options
        self.entry_id = "test_entry"


class MockHomeAssistant:
    """Mock Home Assistant instance."""

    def __init__(self):
        self.data = {}


async def test_coordinator():
    """Test that coordinator can be created and fetch data."""
    # Load .env file
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value

    # Get credentials
    host = os.getenv("ZM_HOST")
    username = os.getenv("ZM_USERNAME")
    password = os.getenv("ZM_PASSWORD")

    if not all([host, username, password]):
        _LOGGER.error("Missing credentials in .env file")
        return False

    _LOGGER.info("Testing integration with %s", host)

    # Create mock config entry
    entry = MockConfigEntry(
        data={
            "host": host,
            "username": username,
            "password": password,
        },
        options={
            "mqtt_enabled": True,
            "mqtt_topic": "zoneminder",
        }
    )

    # Create mock hass
    hass = MockHomeAssistant()

    try:
        # Test coordinator creation
        _LOGGER.info("Creating coordinator...")
        coordinator = await async_get_coordinator(hass, entry)

        _LOGGER.info("✓ Coordinator created successfully")
        _LOGGER.info("  Update interval: %s", coordinator.update_interval)

        # Check data
        if not coordinator.data:
            _LOGGER.error("✗ No data in coordinator")
            return False

        monitors = coordinator.data.get("monitors", {})
        events = coordinator.data.get("events", {})

        _LOGGER.info("✓ Coordinator data fetched:")
        _LOGGER.info("  Monitors: %d", len(monitors))
        _LOGGER.info("  Events data for %d monitors", len(events))

        # List monitors and their stream URLs
        for monitor_id, monitor in monitors.items():
            stream_url = coordinator.api.get_stream_url(monitor_id)
            snapshot_url = coordinator.api.get_stream_url(monitor_id, mode="single")

            _LOGGER.info("")
            _LOGGER.info("Monitor: %s (ID: %d)", monitor.name, monitor.id)
            _LOGGER.info("  Function: %s", monitor.function)
            _LOGGER.info("  Enabled: %s", monitor.enabled)
            _LOGGER.info("  Resolution: %dx%d", monitor.width, monitor.height)
            _LOGGER.info("  Type: %s", monitor.type)
            _LOGGER.info("  Stream URL: %s", stream_url)
            _LOGGER.info("  Snapshot URL: %s", snapshot_url)

            monitor_events = events.get(monitor_id, [])
            _LOGGER.info("  Recent events: %d", len(monitor_events))
            if monitor_events:
                latest = monitor_events[0]
                _LOGGER.info("    Latest: Event %d - %s at %s",
                           latest.id, latest.cause, latest.start_time)

        # Test camera entity creation
        _LOGGER.info("")
        _LOGGER.info("Camera entities that would be created:")
        for monitor in monitors.values():
            entity_id = f"camera.{monitor.name.lower().replace(' ', '_')}"
            unique_id = f"{monitor.id}_live"
            _LOGGER.info("  %s (unique_id: %s)", entity_id, unique_id)

        # Cleanup
        await coordinator.api.close()

        _LOGGER.info("")
        _LOGGER.info("✓ All tests passed!")
        return True

    except Exception as err:
        _LOGGER.exception("✗ Test failed: %s", err)
        return False


if __name__ == "__main__":
    success = asyncio.run(test_coordinator())
    sys.exit(0 if success else 1)
