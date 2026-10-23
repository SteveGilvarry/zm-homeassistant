#!/usr/bin/env python3
"""Diagnose ZoneMinder MQTT connection issues."""

import asyncio
import logging
import os
import sys
from pathlib import Path
import aiohttp

logging.basicConfig(level=logging.INFO, format='%(message)s')
_LOGGER = logging.getLogger(__name__)


async def diagnose_mqtt(host: str, username: str, password: str):
    """Comprehensive MQTT connection diagnostics."""

    _LOGGER.info("=" * 80)
    _LOGGER.info("ZoneMinder MQTT Connection Diagnostics")
    _LOGGER.info("=" * 80)

    session = aiohttp.ClientSession()

    try:
        # Step 1: Authenticate
        _LOGGER.info("\n[1/6] Authenticating to ZoneMinder...")
        login_url = f"{host}/api/host/login.json"
        async with session.post(
            login_url,
            data={"user": username, "pass": password}
        ) as response:
            result = await response.json()
            access_token = result.get("access_token")
            _LOGGER.info("    ✓ Authenticated successfully")

        # Step 2: Check MQTT configuration
        _LOGGER.info("\n[2/6] Checking MQTT configuration...")
        config_url = f"{host}/api/configs.json"
        async with session.get(
            config_url,
            params={"token": access_token}
        ) as response:
            result = await response.json()
            configs = result.get("configs", [])

            mqtt_settings = {}
            for config in configs:
                cfg = config.get("Config", {})
                name = cfg.get("Name", "")
                if "MQTT" in name.upper():
                    mqtt_settings[name] = cfg.get("Value")

            _LOGGER.info("\n    Current MQTT Settings:")
            for key, value in mqtt_settings.items():
                if "PASSWORD" in key.upper():
                    value = "***" if value else "(empty)"
                _LOGGER.info(f"      {key}: {value}")

            # Check specific settings
            hostname = mqtt_settings.get("ZM_MQTT_HOSTNAME", "NOT SET")
            port = mqtt_settings.get("ZM_MQTT_PORT", "NOT SET")

            if hostname == "mqtt.zoneminder.com":
                _LOGGER.error("\n    ✗ PROBLEM: Still using default hostname 'mqtt.zoneminder.com'")
                _LOGGER.error("      Change this to: 192.168.0.66")
                return False
            elif hostname == "192.168.0.66":
                _LOGGER.info(f"\n    ✓ Hostname correctly set to: {hostname}")
            else:
                _LOGGER.warning(f"\n    ⚠ Hostname is: {hostname}")

            if port == "1883":
                _LOGGER.info(f"    ✓ Port correctly set to: {port}")
            else:
                _LOGGER.warning(f"    ⚠ Port is: {port} (expected 1883)")

        # Step 3: Check ZoneMinder version for MQTT support
        _LOGGER.info("\n[3/6] Checking ZoneMinder version...")
        version_url = f"{host}/api/host/getVersion.json"
        async with session.get(
            version_url,
            params={"token": access_token}
        ) as response:
            result = await response.json()
            version = result.get("version", "unknown")
            _LOGGER.info(f"    ZoneMinder version: {version}")

            # Check if version supports MQTT (1.37+)
            try:
                major, minor = version.split(".")[:2]
                if int(major) >= 1 and int(minor) >= 37:
                    _LOGGER.info("    ✓ Version supports built-in MQTT")
                else:
                    _LOGGER.warning("    ⚠ Version may not have built-in MQTT support")
            except:
                _LOGGER.warning("    ⚠ Could not parse version")

        # Step 4: Check if there are active monitors generating events
        _LOGGER.info("\n[4/6] Checking monitors and events...")
        monitors_url = f"{host}/api/monitors.json"
        async with session.get(
            monitors_url,
            params={"token": access_token}
        ) as response:
            result = await response.json()
            monitors = result.get("monitors", [])
            _LOGGER.info(f"    Total monitors: {len(monitors)}")

            active_monitors = 0
            for mon in monitors:
                m = mon.get("Monitor", {})
                if m.get("Enabled") == "1":
                    active_monitors += 1
                    _LOGGER.info(f"      Monitor {m.get('Id')}: {m.get('Name')} - {m.get('Function')}")

            if active_monitors == 0:
                _LOGGER.warning("    ⚠ No enabled monitors found")
            else:
                _LOGGER.info(f"    ✓ {active_monitors} enabled monitors")

        # Step 5: Check recent events
        _LOGGER.info("\n[5/6] Checking recent events...")
        events_url = f"{host}/api/events.json"
        async with session.get(
            events_url,
            params={"token": access_token, "limit": 5}
        ) as response:
            result = await response.json()
            events = result.get("events", [])

            if events:
                _LOGGER.info(f"    ✓ Found {len(events)} recent events:")
                for evt in events[:3]:
                    e = evt.get("Event", {})
                    _LOGGER.info(f"      Event {e.get('Id')}: Monitor {e.get('MonitorId')} - {e.get('Cause')} at {e.get('StartDateTime')}")
            else:
                _LOGGER.warning("    ⚠ No recent events found")
                _LOGGER.info("      Trigger an event to test MQTT")

        # Step 6: Network connectivity check
        _LOGGER.info("\n[6/6] Troubleshooting steps...")

        _LOGGER.info("""
    To verify MQTT connectivity from ZoneMinder server:

    1. SSH to ZoneMinder server (192.168.0.45):
       ssh user@192.168.0.45

    2. Test network connection to MQTT broker:
       telnet 192.168.0.66 1883
       (Press Ctrl+] then type 'quit' to exit)

       Expected: Connection established (proves network path works)
       If fails: Check firewall on your Mac

    3. Test MQTT publish manually:
       mosquitto_pub -h 192.168.0.66 -p 1883 -t 'test/topic' -m 'Hello from ZM server'

       Expected: No error (message sent successfully)
       If fails: MQTT client not installed or network issue

    4. Check ZoneMinder MQTT daemon/process:
       ps aux | grep -i mqtt

       Expected: See ZoneMinder MQTT process running
       If not running: MQTT may be disabled or not started

    5. Check ZoneMinder logs for MQTT errors:
       tail -f /var/log/zm/zmpkg.log | grep -i mqtt
       tail -f /var/log/syslog | grep -i mqtt

       Expected: See MQTT initialization messages
       Look for: Connection errors, authentication failures, etc.

    6. Restart ZoneMinder completely:
       sudo systemctl restart zoneminder

       Then check logs immediately after restart for MQTT startup
        """)

        _LOGGER.info("\n" + "=" * 80)
        _LOGGER.info("Next Steps:")
        _LOGGER.info("=" * 80)

        if hostname != "192.168.0.66":
            _LOGGER.info("""
1. Fix MQTT hostname configuration:
   - Go to: http://192.168.0.45/zm
   - Options → System → MQTT section
   - Change ZM_MQTT_HOSTNAME to: 192.168.0.66
   - Save and restart ZoneMinder
            """)
        else:
            _LOGGER.info("""
1. Configuration looks correct. Check network connectivity:
   - Can ZoneMinder server reach 192.168.0.66:1883?
   - Check firewall on Mac (System Settings → Network → Firewall)
   - Try telnet test from ZoneMinder server (see above)

2. Check ZoneMinder MQTT is actually running:
   - SSH to 192.168.0.45
   - Check processes: ps aux | grep mqtt
   - Check logs: tail -f /var/log/zm/zmpkg.log | grep -i mqtt

3. Restart ZoneMinder:
   - sudo systemctl restart zoneminder
   - Watch logs for MQTT initialization
            """)

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

    await diagnose_mqtt(host, username, password)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
