#!/usr/bin/env python3
"""Test alternative authentication methods for events API."""

import asyncio
import logging
import os
import sys
from pathlib import Path
import aiohttp

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)


async def test_auth_methods(host: str, username: str, password: str):
    """Test different authentication methods."""

    _LOGGER.info("Testing authentication methods for events API")
    _LOGGER.info("=" * 80)

    session = aiohttp.ClientSession()

    try:
        # Authenticate and get token
        login_url = f"{host}/api/host/login.json"
        async with session.post(
            login_url,
            data={"username": username, "password": password}
        ) as response:
            result = await response.json()
            auth_token = result.get("access_token") or result.get("credentials")
            _LOGGER.info("✓ Got auth token")

        # Test 1: Token in Authorization header
        _LOGGER.info("\nTest 1: Token in Authorization header")
        try:
            async with session.get(
                f"{host}/api/events.json",
                headers={"Authorization": f"Bearer {auth_token}"},
                params={"limit": 1},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                _LOGGER.info("  Status: %d", response.status)
                if response.status == 200:
                    result = await response.json()
                    events = result.get("events", [])
                    _LOGGER.info("  ✓ SUCCESS! Got %d events", len(events))
                else:
                    text = await response.text()
                    _LOGGER.info("  Failed: %s", text[:200])
        except Exception as e:
            _LOGGER.error("  Exception: %s", e)

        # Test 2: Use session cookies from login
        _LOGGER.info("\nTest 2: Using session cookies (no explicit token)")
        try:
            async with session.get(
                f"{host}/api/events.json",
                params={"limit": 1},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                _LOGGER.info("  Status: %d", response.status)
                if response.status == 200:
                    result = await response.json()
                    events = result.get("events", [])
                    _LOGGER.info("  ✓ SUCCESS! Got %d events", len(events))
                    if events:
                        event = events[0].get("Event", {})
                        _LOGGER.info("  First event ID: %s", event.get("Id"))
                        _LOGGER.info("  First event monitor: %s", event.get("MonitorId"))
                        _LOGGER.info("  First event cause: %s", event.get("Cause"))
                        return True
                else:
                    text = await response.text()
                    _LOGGER.info("  Failed: %s", text[:200])
        except Exception as e:
            _LOGGER.error("  Exception: %s", e)

        # Test 3: Token in path (if ZM supports it)
        _LOGGER.info("\nTest 3: Token in URL path")
        try:
            async with session.get(
                f"{host}/api/events.json",
                params={"limit": 1},
                cookies={"ZMSESSID": auth_token},  # Try as cookie
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                _LOGGER.info("  Status: %d", response.status)
                if response.status == 200:
                    result = await response.json()
                    events = result.get("events", [])
                    _LOGGER.info("  ✓ SUCCESS! Got %d events", len(events))
                else:
                    text = await response.text()
                    _LOGGER.info("  Failed: %s", text[:200])
        except Exception as e:
            _LOGGER.error("  Exception: %s", e)

        # Test 4: Try with user/pass in params
        _LOGGER.info("\nTest 4: User/pass in query params")
        try:
            async with session.get(
                f"{host}/api/events.json",
                params={"limit": 1, "user": username, "pass": password},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                _LOGGER.info("  Status: %d", response.status)
                if response.status == 200:
                    result = await response.json()
                    events = result.get("events", [])
                    _LOGGER.info("  ✓ SUCCESS! Got %d events", len(events))
                else:
                    text = await response.text()
                    _LOGGER.info("  Failed: %s", text[:200])
        except Exception as e:
            _LOGGER.error("  Exception: %s", e)

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

    success = await test_auth_methods(host, username, password)

    if success:
        _LOGGER.info("\n✓ Found working method! Will update API client.")
    else:
        _LOGGER.info("\n✗ No working method found - events API may be broken in ZM 1.37.73")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
