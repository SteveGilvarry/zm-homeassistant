# SPDX-License-Identifier: Apache-2.0
"""Build an aiozoneminder client from a config entry."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import aiohttp
from aiozoneminder import ZoneMinderClient, create_client
from aiozoneminder.const import DEFAULT_BACKEND
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BACKEND,
    CONF_STREAM_MAXFPS,
    CONF_STREAM_SCALE,
    CONF_VERIFY_SSL,
    CONF_ZMS_PATH,
)


def client_from_entry_data(
    data: Mapping[str, Any],
    session: aiohttp.ClientSession,
    options: Mapping[str, Any] | None = None,
) -> ZoneMinderClient:
    """Build a client from a config entry's stored data and options.

    API v2 sends times without a timezone; they're read in Home Assistant's.
    """
    stream: dict[str, Any] = {}
    if options and options.get(CONF_STREAM_SCALE):
        stream["stream_scale"] = int(options[CONF_STREAM_SCALE])
    if options and options.get(CONF_STREAM_MAXFPS):
        stream["stream_maxfps"] = options[CONF_STREAM_MAXFPS]
    return create_client(
        data.get(CONF_BACKEND, DEFAULT_BACKEND),
        data[CONF_HOST],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        session,
        verify_ssl=data.get(CONF_VERIFY_SSL, True),
        timezone=dt_util.get_default_time_zone(),
        zms_path=data.get(CONF_ZMS_PATH),
        **stream,
    )
