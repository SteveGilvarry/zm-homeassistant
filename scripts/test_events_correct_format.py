#!/usr/bin/env python3
"""Test events API using the CORRECT format from official documentation."""

import asyncio
import logging
import os
import sys
from pathlib import Path
import aiohttp

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)


async def test_events_correct_format(host: str, username: str, password: str):
    """Test events API using official ZM documentation format."""

    _LOGGER.info("=" * 80)
    _LOGGER.info("Testing Events API - Official Documentation Format")
    _LOGGER.info("=" * 80)

    session = aiohttp.ClientSession()

    try:
        # Step 1: Login
        _LOGGER.info("\nStep 1: Login and get JWT token")
        login_url = f"{host}/api/host/login.json"
        async with session.post(
            login_url,
            data={"user": username, "pass": password}
        ) as response:
            result = await response.json()
            access_token = result.get("access_token")
            refresh_token = result.get("refresh_token")
            _LOGGER.info("✓ Got access token: %s...", access_token[:30])
            _LOGGER.info("✓ Got refresh token: %s...", refresh_token[:30])

        # Step 2: Test basic events endpoint (per documentation)
        _LOGGER.info("\nStep 2: Get events - Basic endpoint")
        _LOGGER.info("URL: /api/events.json?token=...")
        try:
            # According to docs: curl -XGET http://server/zm/api/events.json?token=<access_token>
            url = f"{host}/api/events.json"
            async with session.get(
                url,
                params={"token": access_token},  # Token as query param (per docs)
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                _LOGGER.info("Status: %d", response.status)
                if response.status == 200:
                    result = await response.json()
                    events = result.get("events", [])
                    pagination = result.get("pagination", {})
                    _LOGGER.info("✓ SUCCESS! Got %d events", len(events))
                    _LOGGER.info("Pagination: %s", pagination)
                    return True
                else:
                    text = await response.text()
                    _LOGGER.error("Failed: %s", text[:500])
        except Exception as e:
            _LOGGER.exception("Exception: %s", e)

        # Step 3: Try the index endpoint format (from docs)
        _LOGGER.info("\nStep 3: Get events - Index format with MonitorId")
        _LOGGER.info("URL: /api/events/index/MonitorId:4.json?token=...")
        try:
            # From docs: /events/index/MonitorId:5.json
            url = f"{host}/api/events/index/MonitorId:4.json"
            async with session.get(
                url,
                params={"token": access_token},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                _LOGGER.info("Status: %d", response.status)
                if response.status == 200:
                    result = await response.json()
                    events = result.get("events", [])
                    _LOGGER.info("✓ SUCCESS! Got %d events for monitor 4", len(events))
                    return True
                else:
                    text = await response.text()
                    _LOGGER.error("Failed: %s", text[:500])
        except Exception as e:
            _LOGGER.exception("Exception: %s", e)

        # Step 4: Try WITHOUT token parameter at all
        _LOGGER.info("\nStep 4: Get events - Using session authentication (no token param)")
        try:
            url = f"{host}/api/events.json"
            async with session.get(
                url,
                # No token parameter!
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                _LOGGER.info("Status: %d", response.status)
                if response.status == 200:
                    result = await response.json()
                    events = result.get("events", [])
                    _LOGGER.info("✓ SUCCESS! Got %d events", len(events))
                    return True
                else:
                    text = await response.text()
                    _LOGGER.info("Failed (expected): %s", text[:200])
        except Exception as e:
            _LOGGER.debug("Exception (expected): %s", e)

        # Step 5: Try with page parameter in URL path (not query)
        _LOGGER.info("\nStep 5: Get events - Page in URL path")
        _LOGGER.info("URL: /api/events/index/page:1.json?token=...")
        try:
            url = f"{host}/api/events/index/page:1.json"
            async with session.get(
                url,
                params={"token": access_token},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                _LOGGER.info("Status: %d", response.status)
                if response.status == 200:
                    result = await response.json()
                    events = result.get("events", [])
                    _LOGGER.info("✓ SUCCESS! Got %d events", len(events))
                    return True
                else:
                    text = await response.text()
                    _LOGGER.error("Failed: %s", text[:500])
        except Exception as e:
            _LOGGER.exception("Exception: %s", e)

        # Step 6: Try combined - MonitorId and page in path
        _LOGGER.info("\nStep 6: Get events - MonitorId and page in URL path")
        _LOGGER.info("URL: /api/events/index/MonitorId:4/page:1.json?token=...")
        try:
            url = f"{host}/api/events/index/MonitorId:4/page:1.json"
            async with session.get(
                url,
                params={"token": access_token},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                _LOGGER.info("Status: %d", response.status)
                if response.status == 200:
                    result = await response.json()
                    events = result.get("events", [])
                    pagination = result.get("pagination", {})
                    _LOGGER.info("✓ SUCCESS! Got %d events for monitor 4", len(events))
                    _LOGGER.info("Pagination: %s", pagination)

                    if events:
                        event = events[0].get("Event", {})
                        _LOGGER.info("\nFirst event:")
                        _LOGGER.info("  ID: %s", event.get("Id"))
                        _LOGGER.info("  Monitor: %s", event.get("MonitorId"))
                        _LOGGER.info("  Cause: %s", event.get("Cause"))
                        _LOGGER.info("  Start: %s", event.get("StartDateTime"))

                    return True
                else:
                    text = await response.text()
                    _LOGGER.error("Failed: %s", text[:500])
        except Exception as e:
            _LOGGER.exception("Exception: %s", e)

        # Step 7: Check what happens with sort/direction as query params
        _LOGGER.info("\nStep 7: Get events - With sort in query params")
        _LOGGER.info("URL: /api/events/index/MonitorId:4.json?token=...&sort=StartDateTime&direction=desc")
        try:
            url = f"{host}/api/events/index/MonitorId:4.json"
            async with session.get(
                url,
                params={
                    "token": access_token,
                    "sort": "StartDateTime",
                    "direction": "desc"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                _LOGGER.info("Status: %d", response.status)
                if response.status == 200:
                    result = await response.json()
                    events = result.get("events", [])
                    _LOGGER.info("✓ SUCCESS! Got %d sorted events", len(events))
                    return True
                else:
                    text = await response.text()
                    _LOGGER.error("Failed: %s", text[:500])
        except Exception as e:
            _LOGGER.exception("Exception: %s", e)

    finally:
        await session.close()

    return False


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
        print("ERROR: Missing credentials")
        return 1

    success = await test_events_correct_format(host, username, password)

    _LOGGER.info("\n" + "=" * 80)
    if success:
        _LOGGER.info("✓✓✓ FOUND WORKING FORMAT! ✓✓✓")
        _LOGGER.info("Will update API client with correct endpoint format")
    else:
        _LOGGER.info("✗ All documented formats failed")
        _LOGGER.info("This confirms a ZoneMinder server bug")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
