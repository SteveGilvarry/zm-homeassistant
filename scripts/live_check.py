#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Check a real ZoneMinder server against everything the integration needs.

This is the script that proves a server will work before you spend time
debugging Home Assistant. It exercises the same client code the integration
uses, then serves the live stream through the same proxy logic and asks ffmpeg
whether it plays.

    ZM_HOST=http://192.168.0.45:8080 ZM_USERNAME=admin ZM_PASSWORD=secret \
        python scripts/live_check.py

Add --backend legacy for a stock ZoneMinder install.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
import sys
from urllib.parse import unquote

import aiohttp
from aiohttp import web

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from custom_components.zoneminder.api import build_client  # noqa: E402
from custom_components.zoneminder.const import PROXY_URL_BASE  # noqa: E402
from custom_components.zoneminder.http import (  # noqa: E402
    _ALLOWED_PATHS,
    _rewrite_playlist,
)

OK, BAD, INFO = "  ok  ", " FAIL ", "      "
PROXY_PORT = 8199
ENTRY, SECRET = "livecheck", "livecheck"


def report(passed: bool, message: str) -> bool:
    """Print one check result and pass its outcome back."""
    print(f"[{OK if passed else BAD}] {message}")
    return passed


async def check_api(client) -> list:
    """Exercise the read side of the API and return the monitors found."""
    version = await client.get_version()
    report(True, f"connected to ZoneMinder {version}")

    info = await client.get_server_info()
    report(
        info.daemons_total == 0 or info.daemons_running == info.daemons_total,
        f"daemons running: {info.daemons_running}/{info.daemons_total}",
    )
    if info.storage:
        used = info.total_disk_space / 1e9
        report(True, f"storage: {used:.1f} GB across {len(info.storage)} area(s)")

    monitors = await client.get_monitors()
    report(bool(monitors), f"monitors: {len(monitors)}")

    statuses = await client.get_monitor_statuses()
    for monitor in monitors:
        status = statuses.get(monitor.id)
        state = status.status if status else "unknown"
        fps = f"{status.capture_fps:.1f} fps" if status else "no stats"
        print(
            f"{INFO}  {monitor.id}: {monitor.name[:28]:28} {state:12} {fps:10}"
            f" capturing={monitor.capturing} analysing={monitor.analysing}"
            f" recording={monitor.recording}"
        )
        if not monitor.is_analysing:
            print(
                f"{INFO}     motion detection is off, so this monitor cannot "
                "report motion"
            )

    events = await client.get_events(limit=50)
    alarms = [e for e in events if e.is_alarm]
    report(True, f"events: {len(events)} recent, {len(alarms)} with motion")

    configs = await client.get_configs()
    prefix = configs.get("ZM_MQTT_TOPIC_PREFIX")
    report(bool(prefix), f"MQTT topic prefix: {prefix or 'not set in ZoneMinder'}")
    publishing = [m.id for m in monitors if m.mqtt_enabled]
    report(
        bool(publishing),
        f"monitors publishing over MQTT: {publishing or 'none, so motion will be slow'}",
    )

    return monitors


async def check_stream(client, monitor_id: int) -> bool:
    """Serve one monitor through the proxy and let ffmpeg decide."""
    path = client.get_live_media_path(monitor_id)
    if path is None:
        source = await client.get_stream_source(monitor_id)
        return report(bool(source), f"stream source: {source}")

    await client.async_prepare_live(monitor_id)
    await asyncio.sleep(4)

    async def handler(request: web.Request) -> web.StreamResponse:
        upstream = unquote(request.match_info["upstream"])
        if not any(pattern.match(upstream) for pattern in _ALLOWED_PATHS):
            return web.Response(status=403)
        async with client.async_stream_media(upstream) as response:
            if response.status >= 400:
                return web.Response(status=response.status)
            if upstream.endswith(".m3u8"):
                body = _rewrite_playlist(await response.text(), upstream, ENTRY, SECRET)
                return web.Response(
                    body=body.encode(), content_type="application/vnd.apple.mpegurl"
                )
            return web.Response(
                body=await response.read(),
                content_type=response.content_type or "application/octet-stream",
            )

    app = web.Application()
    # Mounted under the integration's real prefix, because the rewritten
    # playlists point back at it.
    app.router.add_get(PROXY_URL_BASE + "/{entry}/{secret}/{upstream:.*}", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", PROXY_PORT).start()

    url = f"http://127.0.0.1:{PROXY_PORT}{PROXY_URL_BASE}/{ENTRY}/{SECRET}/{path}"
    try:
        process = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v",
            "error",
            "-rw_timeout",
            "20000000",
            "-show_entries",
            "stream=codec_name,width,height",
            "-of",
            "default=nw=1",
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=90)
    except FileNotFoundError:
        return report(False, "ffprobe is not installed, cannot verify the stream")
    except TimeoutError:
        return report(False, f"monitor {monitor_id}: the stream did not start")
    finally:
        await runner.cleanup()

    if process.returncode == 0:
        summary = " ".join(stdout.decode().split())
        return report(True, f"monitor {monitor_id} live stream plays: {summary}")
    return report(False, f"monitor {monitor_id}: {stderr.decode().strip()[:200]}")


async def main() -> int:
    """Run every check and return a shell exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("v3", "legacy"), default="v3")
    parser.add_argument("--monitor", type=int, help="only test this monitor's stream")
    args = parser.parse_args()

    try:
        host = os.environ["ZM_HOST"]
        username = os.environ["ZM_USERNAME"]
        password = os.environ["ZM_PASSWORD"]
    except KeyError as err:
        print(f"Set {err.args[0]} in the environment or in .env")
        return 2

    async with aiohttp.ClientSession() as session:
        client = build_client(args.backend, host, username, password, session)
        try:
            await client.authenticate()
        except Exception as err:  # noqa: BLE001
            report(False, f"could not authenticate: {err}")
            return 1

        monitors = await check_api(client)
        print()

        targets = [args.monitor] if args.monitor else [m.id for m in monitors[:1]]
        results = [await check_stream(client, monitor_id) for monitor_id in targets]

        await client.close()

    print()
    if all(results):
        print("Everything the integration needs is working.")
        return 0
    print("Some checks failed. See the lines marked FAIL above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
