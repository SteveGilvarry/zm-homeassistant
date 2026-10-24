# SPDX-License-Identifier: AGPL-3.0-or-later
"""Serve the ZoneMinder card with the integration.

The card ships inside the integration and is registered on every dashboard,
so there is no resource to add by hand and the card always matches the
integration.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILE = Path(__file__).parent / "www" / "zoneminder-card.js"
CARD_URL = f"/{DOMAIN}_static/zoneminder-card.js"


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and load it on every dashboard, once per instance."""
    if hass.data.get(f"{DOMAIN}_card_registered"):
        return
    if "frontend" not in hass.config.components:
        return
    hass.data[f"{DOMAIN}_card_registered"] = True

    if not await hass.async_add_executor_job(CARD_FILE.is_file):
        _LOGGER.debug("No bundled card at %s, skipping", CARD_FILE)
        return

    contents = await hass.async_add_executor_job(CARD_FILE.read_bytes)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_FILE), cache_headers=False)]
    )
    from homeassistant.components.frontend import (  # noqa: PLC0415 - optional
        add_extra_js_url,
    )

    # A hash of the file, so browsers fetch the card again whenever it
    # changes, not only when the integration's version does.
    add_extra_js_url(hass, f"{CARD_URL}?v={hashlib.sha256(contents).hexdigest()[:12]}")
