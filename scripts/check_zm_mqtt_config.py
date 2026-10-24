#!/usr/bin/env python3
"""Check ZoneMinder MQTT configuration."""

import asyncio
import logging
import os
import sys
from pathlib import Path
import aiohttp

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)


async def check_mqtt_config(host: str, username: str, password: str):
    """Check if ZoneMinder has MQTT enabled and configured."""

    _LOGGER.info("=" * 80)
    _LOGGER.info("Checking ZoneMinder MQTT Configuration")
    _LOGGER.info("=" * 80)

    session = aiohttp.ClientSession()

    try:
        # Step 1: Login
        _LOGGER.info("\nStep 1: Authenticating...")
        login_url = f"{host}/api/host/login.json"
        async with session.post(
            login_url,
            data={"user": username, "pass": password}
        ) as response:
            result = await response.json()
            access_token = result.get("access_token")
            _LOGGER.info("✓ Authenticated")

        # Step 2: Check ZoneMinder configuration for MQTT settings
        _LOGGER.info("\nStep 2: Checking MQTT configuration options...")

        # Check for MQTT-related config options
        config_url = f"{host}/api/configs.json"
        async with session.get(
            config_url,
            params={"token": access_token}
        ) as response:
            if response.status == 200:
                result = await response.json()
                configs = result.get("configs", [])

                # Look for MQTT-related settings
                mqtt_configs = {}
                for config in configs:
                    cfg = config.get("Config", {})
                    name = cfg.get("Name", "")
                    if "MQTT" in name.upper() or "ZM_MQTT" in name:
                        mqtt_configs[name] = {
                            "value": cfg.get("Value"),
                            "type": cfg.get("Type"),
                            "category": cfg.get("Category"),
                        }

                if mqtt_configs:
                    _LOGGER.info("\n✓ Found MQTT configuration options:")
                    for name, details in mqtt_configs.items():
                        _LOGGER.info(f"\n  {name}:")
                        _LOGGER.info(f"    Value: {details['value']}")
                        _LOGGER.info(f"    Type: {details['type']}")
                        _LOGGER.info(f"    Category: {details['category']}")
                else:
                    _LOGGER.warning("\n✗ No MQTT configuration options found")
                    _LOGGER.info("  This might mean:")
                    _LOGGER.info("  - MQTT is not enabled in this ZoneMinder version")
                    _LOGGER.info("  - MQTT support not compiled in")
                    _LOGGER.info("  - Configuration might be in zmMqtt.pl or external config")
            else:
                _LOGGER.error(f"Failed to fetch configs: HTTP {response.status}")

        # Step 3: Check if ZoneMinder has EventNotification enabled
        _LOGGER.info("\nStep 3: Checking for EventNotification (zmeventnotification)...")

        # Try to access the event notification server status
        # This is typically used with MQTT in ZoneMinder setups
        try:
            # Check if there's an eventnotification config
            en_configs = [c for c in configs if "EVENT_NOTIFICATION" in c.get("Config", {}).get("Name", "")]
            if en_configs:
                _LOGGER.info("✓ EventNotification settings found:")
                for config in en_configs:
                    cfg = config.get("Config", {})
                    _LOGGER.info(f"  {cfg.get('Name')}: {cfg.get('Value')}")
            else:
                _LOGGER.info("  No EventNotification settings found in API")
        except Exception as e:
            _LOGGER.debug(f"  Could not check EventNotification: {e}")

        # Step 4: Provide guidance
        _LOGGER.info("\n" + "=" * 80)
        _LOGGER.info("MQTT Configuration Guide")
        _LOGGER.info("=" * 80)

        _LOGGER.info("""
ZoneMinder MQTT can be configured in two ways:

1. **Built-in MQTT (ZM 1.37+)**
   - Edit /etc/zm/conf.d/01-system-paths.conf or similar
   - Or use ZoneMinder web UI: Options → System
   - Look for MQTT settings (may vary by ZM version)

2. **EventNotification Server (zmNinja ecosystem)**
   - Install zmeventnotification from: https://github.com/ZoneMinder/zmeventnotification
   - Configure /etc/zm/zmeventnotification.ini
   - Set MQTT broker settings:
     [mqtt]
     enable = yes
     server = localhost:1883
     username = (optional)
     password = (optional)
     topic = zoneminder

3. **Check Current Setup:**
   - SSH to your ZoneMinder server
   - Check if EventNotification is running:
     sudo systemctl status zoneminder-eventnotification
   - Check config:
     cat /etc/zm/zmeventnotification.ini | grep -A 10 mqtt
   - Check MQTT messages:
     mosquitto_sub -h localhost -t 'zoneminder/#' -v

4. **For Docker Mosquitto (from docker-compose.yml):**
   - Your MQTT broker is at: localhost:1883 (from HA perspective)
   - From ZoneMinder server, point to: <HA-HOST-IP>:1883
   - No auth configured currently (add if needed)
        """)

        # Step 5: Test MQTT connection from here
        _LOGGER.info("\nStep 5: Testing MQTT broker (Mosquitto from docker-compose)...")
        try:
            # Note: This would require paho-mqtt library
            _LOGGER.info("  To test MQTT manually, run:")
            _LOGGER.info("    docker exec zm-homeassistant-mosquitto mosquitto_sub -t 'zoneminder/#' -v")
            _LOGGER.info("  Then trigger an event in ZoneMinder and watch for messages")
        except Exception as e:
            _LOGGER.debug(f"  MQTT test: {e}")

    finally:
        await session.close()

    return True


async def main():
    """Main entry point."""
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
        print("ERROR: Missing credentials in .env file")
        return 1

    await check_mqtt_config(host, username, password)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
