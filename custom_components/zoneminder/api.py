# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build an aiozoneminder client from a config entry."""

from __future__ import annotations

from typing import Any

import aiohttp
from aiozoneminder import ZoneMinderClient, create_client
from aiozoneminder.const import DEFAULT_BACKEND
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.util import dt as dt_util

from .const import CONF_BACKEND, CONF_VERIFY_SSL


def client_from_entry_data(
    data: dict[str, Any], session: aiohttp.ClientSession
) -> ZoneMinderClient:
    """Build a client from a config entry's stored data.

    API v2 sends times without a timezone; they're read in Home Assistant's.
    """
    return create_client(
        data.get(CONF_BACKEND, DEFAULT_BACKEND),
        data[CONF_HOST],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        session,
        verify_ssl=data.get(CONF_VERIFY_SSL, True),
        timezone=dt_util.get_default_time_zone(),
    )
