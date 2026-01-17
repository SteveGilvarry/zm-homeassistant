#!/usr/bin/env python3
"""Test script for ZoneMinder API client.

Usage:
    python test_api.py <zm_host> <username> <password>

Example:
    python test_api.py http://zm.local:8080 admin secretpass

This script will:
1. Test authentication
2. Get ZoneMinder version
3. List all monitors
4. Get recent events
5. Test stream URL generation
6. Test event clip URL generation
"""

import asyncio
import sys
from pprint import pprint

import aiohttp

# Add custom_components to path
sys.path.insert(0, "custom_components/zoneminder")

from api import ZoneMinerAPI
from exceptions import ZMAuthenticationError, ZMConnectionError, ZMApiError


async def test_api(host: str, username: str, password: str):
    """Test the ZoneMinder API client."""
    print(f"\n{'='*60}")
    print("ZoneMinder API Client Test")
    print(f"{'='*60}\n")
    print(f"Host: {host}")
    print(f"Username: {username}")
    print()

    async with aiohttp.ClientSession() as session:
        api = ZoneMinerAPI(host, username, password, session)

        try:
            # Test 1: Authentication
            print("Test 1: Authentication")
            print("-" * 40)
            await api.authenticate()
            print("✓ Authentication successful")
            print(f"  Auth token: {api._auth_token[:20]}..." if api._auth_token else "  No token")
            print()

            # Test 2: Get version
            print("Test 2: Get ZoneMinder version")
            print("-" * 40)
            version = await api.get_version()
            print(f"✓ ZoneMinder version: {version}")
            print()

            # Test 3: Get monitors
            print("Test 3: Get all monitors")
            print("-" * 40)
            monitors = await api.get_monitors()
            print(f"✓ Found {len(monitors)} monitors:")
            for monitor in monitors:
                print(f"  - Monitor {monitor.id}: {monitor.name}")
                print(f"    Function: {monitor.function}, Enabled: {monitor.enabled}")
                print(f"    Type: {monitor.type}, Resolution: {monitor.width}x{monitor.height}")
            print()

            if not monitors:
                print("⚠ No monitors found. Remaining tests will be skipped.")
                return

            # Test 4: Get monitor details
            print("Test 4: Get monitor details")
            print("-" * 40)
            first_monitor = monitors[0]
            monitor_detail = await api.get_monitor(first_monitor.id)
            print(f"✓ Monitor {monitor_detail.id} details:")
            pprint(vars(monitor_detail), indent=2)
            print()

            # Test 5: Get events
            print("Test 5: Get recent events")
            print("-" * 40)
            events = await api.get_events(monitor_id=first_monitor.id, limit=5)
            print(f"✓ Found {len(events)} recent events for monitor {first_monitor.id}:")
            for event in events:
                status = "ACTIVE" if event.is_active else "ENDED"
                print(f"  - Event {event.id}: {event.cause} [{status}]")
                print(f"    Start: {event.start_time}")
                print(f"    Duration: {event.length}s, Frames: {event.frames} ({event.alarm_frames} alarm)")
            print()

            # Test 6: Stream URL
            print("Test 6: Generate stream URL")
            print("-" * 40)
            stream_url = api.get_stream_url(first_monitor.id)
            print(f"✓ Live stream URL for monitor {first_monitor.id}:")
            print(f"  {stream_url}")
            print()

            # Test 7: Event clip URL (if events exist)
            if events:
                print("Test 7: Generate event clip URL")
                print("-" * 40)
                first_event = events[0]
                clip_url = api.get_event_clip_url(first_event.id)
                print(f"✓ Event clip URL for event {first_event.id}:")
                print(f"  {clip_url}")
                print()

            # Test 8: Test alarm trigger (optional, commented out by default)
            # Uncomment to test alarm triggering
            # print("Test 8: Trigger alarm (optional)")
            # print("-" * 40)
            # success = await api.trigger_alarm(first_monitor.id, "API Test")
            # if success:
            #     print(f"✓ Alarm triggered on monitor {first_monitor.id}")
            #     await asyncio.sleep(2)
            #     await api.cancel_alarm(first_monitor.id)
            #     print(f"✓ Alarm cancelled on monitor {first_monitor.id}")
            # print()

            print(f"\n{'='*60}")
            print("All tests completed successfully! ✓")
            print(f"{'='*60}\n")

        except ZMAuthenticationError as err:
            print(f"\n✗ Authentication failed: {err}")
            print("  Please check your username and password.")
            sys.exit(1)

        except ZMConnectionError as err:
            print(f"\n✗ Connection failed: {err}")
            print("  Please check your ZoneMinder host URL.")
            sys.exit(1)

        except ZMApiError as err:
            print(f"\n✗ API error: {err}")
            sys.exit(1)

        except Exception as err:
            print(f"\n✗ Unexpected error: {err}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        finally:
            # Cleanup
            await api.close()
            print("API client closed.")


def main():
    """Main entry point."""
    if len(sys.argv) != 4:
        print("Usage: python test_api.py <zm_host> <username> <password>")
        print("\nExample:")
        print("  python test_api.py http://zm.local:8080 admin secretpass")
        sys.exit(1)

    host = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]

    # Run the async test
    asyncio.run(test_api(host, username, password))


if __name__ == "__main__":
    main()
