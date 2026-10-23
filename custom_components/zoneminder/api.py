# SPDX-License-Identifier: AGPL-3.0-or-later
"""Factory for the ZoneMinder backend clients."""

from __future__ import annotations

from typing import Any

import aiohttp
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME

from .client import ZoneMinderClient, ZoneMinderLegacyClient, ZoneMinderV3Client
from .const import (
    BACKEND_V3,
    CONF_BACKEND,
    CONF_VERIFY_SSL,
    DEFAULT_BACKEND,
    DEFAULT_TIMEOUT,
)

__all__ = [
    "ZoneMinderClient",
    "ZoneMinderLegacyClient",
    "ZoneMinderV3Client",
    "build_client",
    "client_from_entry_data",
]


def build_client(
    backend: str,
    host: str,
    username: str,
    password: str,
    session: aiohttp.ClientSession,
    timeout: int = DEFAULT_TIMEOUT,
    verify_ssl: bool = True,
) -> ZoneMinderClient:
    """Instantiate the client for the given backend."""
    client_class = (
        ZoneMinderV3Client if backend == BACKEND_V3 else ZoneMinderLegacyClient
    )
    return client_class(host, username, password, session, timeout, verify_ssl)


def client_from_entry_data(
    data: dict[str, Any], session: aiohttp.ClientSession
) -> ZoneMinderClient:
    """Build a client from a config entry's stored data."""
    return build_client(
        data.get(CONF_BACKEND, DEFAULT_BACKEND),
        data[CONF_HOST],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        session,
        verify_ssl=data.get(CONF_VERIFY_SSL, True),
    )
