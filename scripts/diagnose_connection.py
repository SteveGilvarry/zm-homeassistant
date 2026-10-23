#!/usr/bin/env python3
"""Diagnose ZoneMinder connection issues."""

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


async def diagnose():
    """Run diagnostic tests."""
    host = os.getenv("ZM_HOST", "http://localhost")

    print("="*60)
    print("ZoneMinder Connection Diagnostic")
    print("="*60)
    print(f"\nTesting host: {host}\n")

    async with aiohttp.ClientSession() as session:
        # Test 1: Basic connectivity
        print("Test 1: Basic HTTP connectivity")
        print("-" * 40)
        try:
            async with session.get(host, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                print(f"✓ Host is reachable")
                print(f"  Status: {resp.status}")
                print(f"  Final URL: {resp.url}")
                if resp.status == 200:
                    content_type = resp.headers.get('Content-Type', 'unknown')
                    print(f"  Content-Type: {content_type}")
        except Exception as e:
            print(f"✗ Cannot reach host: {e}")
            return

        print()

        # Test 2: ZoneMinder web interface
        print("Test 2: ZoneMinder web interface")
        print("-" * 40)
        zm_paths = ["/zm", "/zm/", "/zoneminder", "/"]
        found_zm = False
        for path in zm_paths:
            url = f"{host}{path}"
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        if "ZoneMinder" in text or "console" in text.lower():
                            print(f"✓ Found ZoneMinder at: {url}")
                            found_zm = True
                            break
            except:
                pass

        if not found_zm:
            print("✗ Could not find ZoneMinder web interface")
            print("  Check your ZM_HOST setting")

        print()

        # Test 3: API endpoints
        print("Test 3: API endpoints")
        print("-" * 40)
        api_paths = [
            "/api/host/getVersion.json",
            "/zm/api/host/getVersion.json",
            "/zoneminder/api/host/getVersion.json",
        ]

        for api_path in api_paths:
            url = f"{host}{api_path}"
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    print(f"Testing: {api_path}")
                    print(f"  Status: {resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"  ✓ API works! Version: {data.get('version', 'unknown')}")
                        print(f"\n✓✓✓ Use this as your API base: {host}{api_path.replace('/host/getVersion.json', '')}")
                        break
                    elif resp.status == 401:
                        print(f"  ⚠ API found but requires authentication")
                        print(f"  Try this as your API base: {host}{api_path.replace('/host/getVersion.json', '')}")
                        break
                    else:
                        text = await resp.text()
                        print(f"  Response: {text[:100]}")
            except Exception as e:
                print(f"  ✗ {type(e).__name__}: {e}")
            print()

        # Test 4: Authentication endpoint
        print("Test 4: Authentication endpoint")
        print("-" * 40)
        username = os.getenv("ZM_USERNAME", "admin")
        password = os.getenv("ZM_PASSWORD", "")

        if not password:
            print("⚠ No password in .env, skipping auth test")
        else:
            login_paths = [
                "/api/host/login.json",
                "/zm/api/host/login.json",
                "/zoneminder/api/host/login.json",
            ]

            for login_path in login_paths:
                url = f"{host}{login_path}"
                try:
                    async with session.post(
                        url,
                        data={"username": username, "password": password},
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        print(f"Testing: {login_path}")
                        print(f"  Status: {resp.status}")
                        if resp.status == 200:
                            data = await resp.json()
                            print(f"  ✓ Authentication successful!")
                            if 'access_token' in data:
                                print(f"  Token: {data['access_token'][:20]}...")
                            print(f"\n✓✓✓ Your API is working! Update ZM_HOST to use this base.")
                            break
                        else:
                            text = await resp.text()
                            print(f"  Response: {text[:200]}")
                except Exception as e:
                    print(f"  ✗ {type(e).__name__}: {str(e)[:100]}")
                print()

    print("\n" + "="*60)
    print("Diagnostic complete")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(diagnose())
