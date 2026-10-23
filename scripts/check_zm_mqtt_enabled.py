#!/usr/bin/env python3
"""Check if ZoneMinder MQTT is actually enabled."""

import asyncio
import logging
import os
import sys
from pathlib import Path
import aiohttp

logging.basicConfig(level=logging.INFO, format='%(message)s')
_LOGGER = logging.getLogger(__name__)


async def check_mqtt_enabled(host: str, username: str, password: str):
    """Check for MQTT enable flags."""

    _LOGGER.info("Checking for MQTT enable configuration...")

    session = aiohttp.ClientSession()

    try:
        # Authenticate
        login_url = f"{host}/api/host/login.json"
        async with session.post(
            login_url,
            data={"user": username, "pass": password}
        ) as response:
            result = await response.json()
            access_token = result.get("access_token")

        # Get ALL config values
        config_url = f"{host}/api/configs.json"
        async with session.get(
            config_url,
            params={"token": access_token}
        ) as response:
            result = await response.json()
            configs = result.get("configs", [])

            # Look for ANY config that might enable/disable MQTT
            mqtt_related = []
            for config in configs:
                cfg = config.get("Config", {})
                name = cfg.get("Name", "")
                value = cfg.get("Value", "")
                category = cfg.get("Category", "")

                # Check if it's MQTT-related
                if any(keyword in name.upper() for keyword in ["MQTT", "MESSAGE", "PUBLISH", "BROKER"]):
                    mqtt_related.append({
                        "name": name,
                        "value": value,
                        "category": category,
                        "type": cfg.get("Type", ""),
                    })

            _LOGGER.info(f"\nFound {len(mqtt_related)} MQTT-related configuration options:\n")

            for cfg in mqtt_related:
                value = cfg["value"]
                if "PASSWORD" in cfg["name"].upper():
                    value = "***" if value else "(empty)"

                _LOGGER.info(f"  {cfg['name']}")
                _LOGGER.info(f"    Value: {value}")
                _LOGGER.info(f"    Type: {cfg['type']}")
                _LOGGER.info(f"    Category: {cfg['category']}")
                _LOGGER.info("")

            # Check for enable flag
            enable_flags = [c for c in mqtt_related if "ENABLE" in c["name"].upper()]

            if not enable_flags:
                _LOGGER.warning("⚠ WARNING: No ZM_MQTT_ENABLE or similar flag found!")
                _LOGGER.info("\n   This might mean:")
                _LOGGER.info("   1. MQTT is always on (no enable/disable toggle)")
                _LOGGER.info("   2. MQTT needs to be enabled differently")
                _LOGGER.info("   3. ZoneMinder needs additional configuration")
                _LOGGER.info("\n   Check ZoneMinder documentation for your version:")
                _LOGGER.info("   https://zoneminder.readthedocs.io/en/stable/")
            else:
                _LOGGER.info("✓ Found MQTT enable flags:")
                for flag in enable_flags:
                    _LOGGER.info(f"   {flag['name']}: {flag['value']}")

    finally:
        await session.close()


async def main():
    """Main entry point."""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value

    host = os.getenv("ZM_HOST")
    username = os.getenv("ZM_USERNAME")
    password = os.getenv("ZM_PASSWORD")

    if not all([host, username, password]):
        print("ERROR: Missing credentials")
        return 1

    await check_mqtt_enabled(host, username, password)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
