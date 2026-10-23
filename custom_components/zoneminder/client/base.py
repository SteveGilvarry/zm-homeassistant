# SPDX-License-Identifier: AGPL-3.0-or-later
"""The contract every ZoneMinder backend client implements.

Concrete clients talk to one specific API (the standalone zm-api v3 server or
ZoneMinder's built-in CakePHP API) and expose the same surface to the
coordinator, the entity platforms and the media proxy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import aiohttp

from ..const import DEFAULT_TIMEOUT, STREAM_TYPE_MJPEG
from ..exceptions import ZMNotSupportedError
from ..models import Event, EventSummary, Monitor, MonitorStatus, ServerInfo


class ZoneMinderClient(ABC):
    """Common interface for a ZoneMinder backend."""

    #: Short identifier for the backend (``"v3"`` or ``"legacy"``).
    backend: str = "base"

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        timeout: int = DEFAULT_TIMEOUT,
        verify_ssl: bool = True,
    ) -> None:
        """Initialize the client."""
        self._host = host.rstrip("/")
        self._username = username
        self._password = password
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._verify_ssl = verify_ssl
        self._authenticated = False

    @property
    def host(self) -> str:
        """Return the server URL, without a trailing slash."""
        return self._host

    @property
    def authenticated(self) -> bool:
        """Return True once a session has been established."""
        return self._authenticated

    def _build_url(self, endpoint: str) -> str:
        """Join the host with a relative endpoint path."""
        return f"{self._host}/{endpoint.lstrip('/')}"

    # -- Lifecycle -----------------------------------------------------------

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the server."""

    @abstractmethod
    async def get_version(self) -> str:
        """Return the ZoneMinder version string."""

    @abstractmethod
    async def get_server_info(self) -> ServerInfo:
        """Return version, daemon health and storage usage."""

    @abstractmethod
    async def close(self) -> None:
        """Release resources and drop credentials."""

    # -- Monitors ------------------------------------------------------------

    @abstractmethod
    async def get_monitors(self) -> list[Monitor]:
        """Return every monitor."""

    @abstractmethod
    async def get_monitor(self, monitor_id: int) -> Monitor:
        """Return a single monitor."""

    async def get_monitor_statuses(self) -> dict[int, MonitorStatus]:
        """Return live capture stats keyed by monitor id.

        Backends without a status endpoint return an empty mapping.
        """
        return {}

    @abstractmethod
    async def set_monitor_state(
        self,
        monitor_id: int,
        *,
        capturing: str | None = None,
        analysing: str | None = None,
        recording: str | None = None,
        decoding: str | None = None,
    ) -> None:
        """Update one or more of a monitor's state fields.

        Raises a ``ZMError`` subclass when the change is rejected, so callers
        can surface the failure instead of silently doing nothing.
        """

    # -- Events --------------------------------------------------------------

    @abstractmethod
    async def get_events(
        self,
        monitor_id: int | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Return events newest first, optionally filtered to one monitor."""

    @abstractmethod
    async def get_event(self, event_id: int) -> Event:
        """Return a single event."""

    async def get_events_between(
        self,
        monitor_id: int,
        start: datetime,
        end: datetime,
        limit: int = 500,
    ) -> list[Event]:
        """Return a monitor's events that started inside a time window.

        Backends without a range filter fall back to slicing the most recent
        events, which is correct but only reaches as far back as ``limit``.
        """
        events = await self.get_events(monitor_id=monitor_id, limit=limit)
        return [event for event in events if start <= event.start_time < end]

    async def get_event_summary(self, monitor_id: int) -> EventSummary | None:
        """Return event counts and disk usage for a monitor, if supported."""
        return None

    # -- Alarm and control ---------------------------------------------------

    @abstractmethod
    async def trigger_alarm(self, monitor_id: int, cause: str) -> None:
        """Force a monitor into alarm state."""

    @abstractmethod
    async def cancel_alarm(self, monitor_id: int) -> None:
        """Clear a forced alarm."""

    @abstractmethod
    async def ptz(self, monitor_id: int, command: str, **kwargs: Any) -> None:
        """Issue a PTZ command from the vocabulary in ``PTZ_COMMANDS``."""

    async def get_ptz_presets(self, monitor_id: int) -> dict[int, str]:
        """Return ``{preset_number: label}`` for a controllable monitor."""
        return {}

    # -- Configuration -------------------------------------------------------

    async def get_configs(self) -> dict[str, str]:
        """Return ZoneMinder's configuration keys and values."""
        return {}

    # -- Live streaming ------------------------------------------------------

    async def async_prepare_live(self, monitor_id: int) -> None:
        """Make sure a live session exists before a stream URL is fetched.

        Backends that stream without an explicit session do nothing here.
        """
        return None

    @abstractmethod
    async def get_stream_source(self, monitor_id: int) -> str | None:
        """Return a stream URL for Home Assistant's stream component.

        This is only used for backends whose stream URL needs no request
        headers. The v3 backend streams through the integration's media proxy
        instead, because its HLS segments require a bearer token.
        """

    def get_stream_type(self, monitor_id: int) -> str:
        """Return the stream type the camera entity advertises."""
        return STREAM_TYPE_MJPEG

    def get_webrtc_signaling_url(self, monitor_id: int) -> str | None:
        """Return the WebSocket URL for native WebRTC signaling, if any."""
        return None

    # -- Media ---------------------------------------------------------------

    @abstractmethod
    async def async_get_snapshot(self, monitor_id: int) -> bytes | None:
        """Return one JPEG still frame."""

    def get_live_media_path(self, monitor_id: int) -> str | None:
        """Return the relative path of the live HLS master playlist."""
        return None

    def get_event_media_path(self, event_id: int) -> str | None:
        """Return the relative path of an event's video."""
        return None

    def get_event_thumbnail_path(self, event_id: int) -> str | None:
        """Return the relative path of an event's thumbnail image."""
        return None

    @asynccontextmanager
    async def async_stream_media(
        self, path: str, headers: dict[str, str] | None = None
    ) -> AsyncIterator[aiohttp.ClientResponse]:
        """Yield an authenticated response for a relative media path.

        The media proxy uses this to add credentials to requests that Home
        Assistant's stream component and the frontend cannot authenticate
        themselves.
        """
        raise ZMNotSupportedError(
            f"The {self.backend} backend does not support media proxying"
        )
        yield  # pragma: no cover - unreachable, satisfies the generator contract
