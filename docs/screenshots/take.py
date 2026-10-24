#!/usr/bin/env python3
"""Regenerate the README screenshots from a running Home Assistant.

    pip install playwright
    HA_TOKEN=... python docs/screenshots/take.py

Needs a Home Assistant with this integration set up and a long-lived access
token (your profile > Security). The token can also go in a git-ignored
`.env` file at the repo root as HA_TOKEN=... It is only used by the browser
and never printed. Uses your installed Google Chrome, so Playwright doesn't
need to download a browser.

What's real and what's staged is described in docs/screenshots/README.md.
Nothing in Home Assistant is changed: the card and the renames exist only in
the browser page, and the setup dialog is closed without being submitted.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re

from playwright.sync_api import Page, sync_playwright

HERE = Path(__file__).parent
REPO = HERE.parents[1]
IMAGES = REPO / "docs" / "images"
FRAMES = HERE / "frames"
CAMERA_IDS = ("driveway", "front_door", "car_park", "back_yard")
TOKEN_LINE = re.compile(r"\s*HA_TOKEN\s*=\s*['\"]?([^'\"\s]+)['\"]?\s*")


def token() -> str:
    """Read the access token from the environment or the repo's .env."""
    if value := os.environ.get("HA_TOKEN"):
        return value
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if match := TOKEN_LINE.fullmatch(line):
                return match.group(1)
    raise SystemExit(
        "Set HA_TOKEN, or add HA_TOKEN=... to .env, with a long-lived token."
    )


def sign_in(page: Page, base: str, access_token: str) -> None:
    """Hand the frontend a token before it loads, as if already logged in."""
    tokens = {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 1800,
        "refresh_token": "",
        "hassUrl": base,
        "clientId": f"{base}/",
        "expires": 4_102_444_800_000,  # 2100: never refresh.
    }
    page.add_init_script(
        f"window.localStorage.setItem('hassTokens', {json.dumps(json.dumps(tokens))});"
    )


def frame(name: str) -> str:
    """A stand-in camera frame as a data URL.

    Handed to the page directly: Home Assistant's service worker answers the
    page's own requests, so a frame fetched by URL would never arrive.
    """
    data = base64.b64encode((FRAMES / f"{name}.jpg").read_bytes()).decode()
    return f"data:image/jpeg;base64,{data}"


def open_page(page: Page, url: str) -> None:
    """Load a frontend page and add the helpers from demo.js."""
    page.goto(url)
    # The integration loads the card on every page, so once it's defined the
    # frontend has finished starting up.
    page.wait_for_function(
        "() => document.querySelector('home-assistant')?.hass?.states"
        " && customElements.get('zoneminder-card')"
    )
    page.add_script_tag(path=str(HERE / "demo.js"))
    # Keep the pointer out of shot.
    page.mouse.move(0, page.viewport_size["height"] - 1)


def shoot_card(page: Page, base: str, dashboard: str) -> None:
    """The card with four made-up cameras and a hover preview."""
    open_page(page, f"{base}{dashboard}")
    frames = {camera: frame(camera) for camera in CAMERA_IDS}
    page.evaluate("frames => zmReadme.mountCard(frames)", frames)
    page.wait_for_function("() => zmReadme.cardReady()", timeout=30_000)
    page.evaluate("() => zmReadme.hoverMotion('front_door', 7)")
    page.wait_for_timeout(800)
    box = page.evaluate(
        """() => {
          const panel = document.getElementById('zm-readme-panel');
          const left = panel.getBoundingClientRect().left;
          const card = window.__zmReadme.card.getBoundingClientRect();
          return {x: left, y: 0, width: card.width + 24, height: card.bottom + 12};
        }"""
    )
    page.screenshot(path=IMAGES / "card.jpg", clip=box, type="jpeg", quality=90)


def shoot_setup(page: Page, base: str) -> None:
    """The first step of adding the integration."""
    open_page(page, f"{base}/config/integrations/dashboard/add?domain=zoneminder")
    page.get_by_role("button", name="OK").click()  # "Do you want to set up ZoneMinder?"
    page.get_by_text("Connect to ZoneMinder").wait_for()
    page.wait_for_timeout(800)
    box = page.evaluate("() => zmReadme.dialogBox()")
    page.screenshot(path=IMAGES / "setup.png", clip=box)
    page.keyboard.press("Escape")  # Closing the dialog abandons the flow.
    page.wait_for_timeout(500)


def shoot_device(page: Page, base: str) -> None:
    """A camera's Controls and Activity cards, renamed."""
    open_page(page, f"{base}/config/integrations/dashboard")
    camera = page.evaluate("() => zmReadme.landscapeCamera()")
    if camera is None:
        raise SystemExit("No ZoneMinder camera without rotation to photograph.")
    host = page.evaluate(
        """() => Object.values(document.querySelector('home-assistant').hass.devices)
              .map(d => d.name || '').find(n => /ZoneMinder \\(https?:/.test(n))"""
    )
    replacements = [[camera["name"], "Driveway"]]
    if host and (match := re.search(r"https?://([^/:)]+)", host)):
        replacements.append([match.group(1), "homeserver"])

    open_page(page, f"{base}/config/devices/device/{camera['deviceId']}")
    page.get_by_text("Controls").first.wait_for()
    page.evaluate(
        "([replacements, picture]) => zmReadme.scrub(replacements, picture)",
        [replacements, frame("driveway")],
    )
    page.evaluate("() => zmReadme.hideCardsExcept(['Controls', 'Activity'])")
    page.wait_for_timeout(1000)
    box = page.evaluate("() => zmReadme.boxAround(['Controls', 'Activity'])")
    page.screenshot(path=IMAGES / "device.png", clip=box)


def main() -> None:
    """Take every screenshot."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:8123")
    parser.add_argument(
        "--dashboard",
        default="/zm-cameras/all",
        help="Dashboard view the demo card is drawn over; its title shows above it.",
    )
    parser.add_argument("--headed", action="store_true", help="Show the browser.")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    IMAGES.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=not args.headed)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
            color_scheme="dark",
            locale="en-GB",
        )
        context.set_default_timeout(30_000)
        page = context.new_page()
        sign_in(page, base, token())
        # A new browser profile installs the frontend's service worker, which
        # then reloads the page. Get that over with before taking anything.
        page.goto(base)
        page.evaluate("() => navigator.serviceWorker.ready.then(() => true)")
        page.wait_for_timeout(2000)
        for name, shoot in (
            ("card", lambda: shoot_card(page, base, args.dashboard)),
            ("setup", lambda: shoot_setup(page, base)),
            ("device", lambda: shoot_device(page, base)),
        ):
            shoot()
            print(f"saved {name}")
        browser.close()


if __name__ == "__main__":
    main()
