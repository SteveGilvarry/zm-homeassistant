#!/usr/bin/env python3
"""Test events API with proper session handling."""

import asyncio
import logging
import os
import sys
from pathlib import Path
import aiohttp

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)


async def test_events_with_session(host: str, username: str, password: str):
    """Test events API with proper session cookie handling."""

    _LOGGER.info("Testing events API with session management")
    _LOGGER.info("=" * 80)

    # Create session with cookie jar
    jar = aiohttp.CookieJar()
    session = aiohttp.ClientSession(cookie_jar=jar)

    try:
        # Step 1: Login
        _LOGGER.info("\nStep 1: Login")
        login_url = f"{host}/api/host/login.json"

        async with session.post(
            login_url,
            data={"username": username, "password": password}
        ) as response:
            _LOGGER.info("Login status: %d", response.status)
            result = await response.json()
            auth_token = result.get("access_token") or result.get("credentials")
            _LOGGER.info("Token: %s...", auth_token[:30] if auth_token else "None")

            # Check cookies
            _LOGGER.info("Cookies after login:")
            for cookie in jar:
                _LOGGER.info("  %s = %s", cookie.key, cookie.value[:50])

        # Step 2: Try events WITHOUT token param (rely on session)
        _LOGGER.info("\nStep 2: Get events (session-based, no token param)")
        try:
            async with session.get(
                f"{host}/api/events.json",
                params={"limit": 1},  # NO token param!
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                _LOGGER.info("Status: %d", response.status)

                if response.status == 200:
                    result = await response.json()
                    events = result.get("events", [])
                    _LOGGER.info("✓ SUCCESS! Got %d events", len(events))

                    if events:
                        event = events[0].get("Event", {})
                        _LOGGER.info("\nFirst event details:")
                        _LOGGER.info("  ID: %s", event.get("Id"))
                        _LOGGER.info("  Monitor ID: %s", event.get("MonitorId"))
                        _LOGGER.info("  Cause: %s", event.get("Cause"))
                        _LOGGER.info("  Start Time: %s", event.get("StartDateTime"))
                        _LOGGER.info("  End Time: %s", event.get("EndDateTime"))
                        _LOGGER.info("  Frames: %s", event.get("Frames"))

                    return True
                else:
                    text = await response.text()
                    _LOGGER.error("Failed: %s", text[:500])

                    # Try to parse error
                    try:
                        error = await response.json()
                        exception = error.get("data", {}).get("exception", {})
                        _LOGGER.error("Exception: %s", exception.get("message"))
                        _LOGGER.error("SQL Error Code: %s", exception.get("code"))
                    except:
                        pass

        except Exception as e:
            _LOGGER.exception("Exception: %s", e)

        # Step 3: Try with token in header
        _LOGGER.info("\nStep 3: Get events (with auth token)")
        try:
            async with session.get(
                f"{host}/api/events.json",
                params={"limit": 1, "token": auth_token},  # Include token
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

    success = await test_events_with_session(host, username, password)

    _LOGGER.info("\n" + "=" * 80)
    if success:
        _LOGGER.info("✓ SOLUTION FOUND!")
        _LOGGER.info("Will update API client to avoid passing 'token' as query param")
    else:
        _LOGGER.info("✗ Events API appears to be broken in this ZM version")
        _LOGGER.info("This is a ZoneMinder bug - not our integration issue")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
