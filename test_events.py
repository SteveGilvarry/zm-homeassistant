#!/usr/bin/env python3
"""Test different event query methods to find what works."""

import asyncio
import os
import sys
from pathlib import Path

import aiohttp

# Load .env
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

sys.path.insert(0, str(Path(__file__).parent))

from custom_components.zoneminder.api import ZoneMinerAPI


async def test_events():
    """Test different event query approaches."""
    host = os.getenv("ZM_HOST")
    username = os.getenv("ZM_USERNAME")
    password = os.getenv("ZM_PASSWORD")

    print("="*60)
    print("ZoneMinder Events API Testing")
    print("="*60)
    print(f"Host: {host}\n")

    async with aiohttp.ClientSession() as session:
        api = ZoneMinerAPI(host, username, password, session)
        await api.authenticate()
        print("✓ Authenticated\n")

        # Get a monitor ID to test with
        monitors = await api.get_monitors()
        if not monitors:
            print("✗ No monitors found!")
            return

        test_monitor = monitors[0]
        print(f"Testing with monitor: {test_monitor.id} - {test_monitor.name}\n")

        # Test 1: Simple request without filters
        print("Test 1: Simple events request (no filters)")
        print("-" * 40)
        try:
            url = api._build_url("api/events.json")
            params = {"token": api._auth_token}
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    event_count = len(data.get("events", []))
                    print(f"✓ Success! Got {event_count} events")
                    if event_count > 0:
                        first_event = data["events"][0]
                        print(f"  First event ID: {first_event.get('Event', {}).get('Id')}")
                else:
                    text = await resp.text()
                    print(f"✗ Error: {text[:200]}")
        except Exception as e:
            print(f"✗ Exception: {e}")
        print()

        # Test 2: With limit only
        print("Test 2: With limit parameter")
        print("-" * 40)
        try:
            url = api._build_url("api/events.json")
            params = {"token": api._auth_token, "limit": 5}
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ Success! Got {len(data.get('events', []))} events")
                else:
                    text = await resp.text()
                    print(f"✗ Error: {text[:200]}")
        except Exception as e:
            print(f"✗ Exception: {e}")
        print()

        # Test 3: With monitor filter (different syntax)
        print("Test 3: Monitor filter (MonitorId syntax)")
        print("-" * 40)
        try:
            url = api._build_url("api/events.json")
            params = {
                "token": api._auth_token,
                "MonitorId": test_monitor.id,
                "limit": 5
            }
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ Success! Got {len(data.get('events', []))} events")
                else:
                    text = await resp.text()
                    print(f"✗ Error: {text[:200]}")
        except Exception as e:
            print(f"✗ Exception: {e}")
        print()

        # Test 4: Without sort/order
        print("Test 4: Without sort/order parameters")
        print("-" * 40)
        try:
            url = api._build_url("api/events.json")
            params = {
                "token": api._auth_token,
                "MonitorId": test_monitor.id,
                "limit": 5
            }
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    events = data.get("events", [])
                    print(f"✓ Success! Got {len(events)} events")
                    if events:
                        for i, evt in enumerate(events[:3], 1):
                            event_info = evt.get("Event", {})
                            print(f"  {i}. Event {event_info.get('Id')}: {event_info.get('Name')} - {event_info.get('StartTime')}")
                else:
                    text = await resp.text()
                    print(f"✗ Error: {text[:200]}")
        except Exception as e:
            print(f"✗ Exception: {e}")
        print()

        # Test 5: Index-based query
        print("Test 5: Using events/index endpoint")
        print("-" * 40)
        try:
            url = api._build_url("api/events/index.json")
            params = {
                "token": api._auth_token,
                "MonitorId": test_monitor.id,
                "limit": 5
            }
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ Success! Response structure: {list(data.keys())}")
                    events = data.get("events", [])
                    print(f"  Got {len(events)} events")
                else:
                    text = await resp.text()
                    print(f"✗ Error: {text[:200]}")
        except Exception as e:
            print(f"✗ Exception: {e}")
        print()

        # Test 6: Events for all monitors (no filter)
        print("Test 6: All events (paginated)")
        print("-" * 40)
        try:
            url = api._build_url("api/events.json")
            params = {
                "token": api._auth_token,
                "page": 1,
                "limit": 10
            }
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    events = data.get("events", [])
                    print(f"✓ Success! Got {len(events)} events")
                    pagination = data.get("pagination", {})
                    if pagination:
                        print(f"  Pagination: {pagination}")
                else:
                    text = await resp.text()
                    print(f"✗ Error: {text[:200]}")
        except Exception as e:
            print(f"✗ Exception: {e}")
        print()

        await api.close()

        print("="*60)
        print("Testing Complete")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(test_events())
