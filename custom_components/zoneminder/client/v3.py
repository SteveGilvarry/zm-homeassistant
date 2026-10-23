# SPDX-License-Identifier: AGPL-3.0-or-later
"""Client for the standalone zm-api v3 REST server.

Talks to ``/api/v3/...`` with JWT bearer authentication.
See https://github.com/SteveGilvarry/zm-api.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
import logging
from typing import Any

import aiohttp

from ..const import (
    BACKEND_V3,
    DEFAULT_TIMEOUT,
    LONG_TIMEOUT,
    STREAM_TYPE_HLS,
    V3_CONFIGS,
    V3_CONTROL_PRESETS,
    V3_EVENT,
    V3_EVENT_SUMMARY,
    V3_EVENT_THUMBNAIL,
    V3_EVENT_VIDEO,
    V3_EVENTS,
    V3_LIVE_HLS_MASTER,
    V3_LIVE_START,
    V3_LIVE_STATS,
    V3_LIVE_STOP,
    V3_LIVE_WEBRTC_WS,
    V3_LOGIN,
    V3_MONITOR,
    V3_MONITOR_ALARM,
    V3_MONITOR_SNAPSHOT,
    V3_MONITOR_STATUS,
    V3_MONITORS,
    V3_PTZ_FOCUS,
    V3_PTZ_HOME,
    V3_PTZ_MOVE,
    V3_PTZ_PRESET_GOTO,
    V3_PTZ_ZOOM,
    V3_REFRESH,
    V3_STORAGE,
    V3_SYSTEM_STATUS,
    V3_VERSION,
)
from ..exceptions import (
    ZMApiError,
    ZMAuthenticationError,
    ZMConnectionError,
    ZMNotSupportedError,
)
from ..models import (
    Event,
    EventSummary,
    Monitor,
    MonitorStatus,
    ServerInfo,
    StorageArea,
)
from .base import ZoneMinderClient

_LOGGER = logging.getLogger(__name__)

#: Page size used when enumerating collections. The server caps this at 1000.
_PAGE_SIZE = 500
#: Refresh the access token this long before it actually expires.
_TOKEN_SKEW = timedelta(seconds=60)
#: A live session is re-armed if we have not touched it for this long.
_LIVE_SESSION_TTL = timedelta(minutes=2)

_PTZ_MOVE_DIRECTIONS = {
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "up-left": "up-left",
    "up-right": "up-right",
    "down-left": "down-left",
    "down-right": "down-right",
    "stop": "stop",
}
_PTZ_ZOOM_DIRECTIONS = {"zoom-in": "in", "zoom-out": "out", "zoom-stop": "stop"}
_PTZ_FOCUS_DIRECTIONS = {
    "focus-near": "near",
    "focus-far": "far",
    "focus-auto": "auto",
    "focus-stop": "stop",
}


class ZoneMinderV3Client(ZoneMinderClient):
    """Client for the zm-api v3 REST server."""

    backend = BACKEND_V3

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the client."""
        super().__init__(*args, **kwargs)
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expires: datetime | None = None
        self._live_sessions: dict[int, datetime] = {}

    # -- Authentication ------------------------------------------------------

    @property
    def access_token(self) -> str | None:
        """Return the current access token."""
        return self._access_token

    def _auth_headers(self) -> dict[str, str]:
        """Return the Authorization header for the current token."""
        if self._access_token:
            return {"Authorization": f"Bearer {self._access_token}"}
        return {}

    def _store_tokens(self, result: dict[str, Any]) -> None:
        """Record the tokens and expiry returned by login or refresh."""
        self._access_token = result.get("access_token")
        self._refresh_token = result.get("refresh_token") or self._refresh_token
        expires_in = result.get("expire_in")
        if isinstance(expires_in, (int, float)) and expires_in > 0:
            self._token_expires = datetime.now() + timedelta(seconds=expires_in)
        else:
            self._token_expires = None

    async def authenticate(self) -> bool:
        """Log in and store the JWT pair."""
        try:
            async with self._session.post(
                self._build_url(V3_LOGIN),
                json={"username": self._username, "password": self._password},
                timeout=self._timeout,
                ssl=self._verify_ssl,
            ) as response:
                if response.status in (400, 401, 403):
                    raise ZMAuthenticationError("Invalid username or password")
                if response.status == 404:
                    raise ZMConnectionError(
                        f"No zm-api server at {self._host}. Check the URL and port, "
                        "or switch the integration to the legacy backend."
                    )
                response.raise_for_status()
                result = await response.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise ZMConnectionError(f"Connection failed: {err}") from err

        self._store_tokens(result)
        if not self._access_token:
            raise ZMAuthenticationError("Login did not return an access token")
        self._authenticated = True
        _LOGGER.debug("Authenticated with zm-api v3 at %s", self._host)
        return True

    async def _refresh(self) -> bool:
        """Exchange the refresh token for a new access token."""
        if not self._refresh_token:
            return False
        try:
            async with self._session.post(
                self._build_url(V3_REFRESH),
                json={"token": self._refresh_token},
                timeout=self._timeout,
                ssl=self._verify_ssl,
            ) as response:
                if response.status != 200:
                    return False
                result = await response.json()
        except (aiohttp.ClientError, TimeoutError):
            return False
        self._store_tokens(result)
        return bool(self._access_token)

    async def _async_ensure_token(self) -> None:
        """Make sure a usable access token is available."""
        if not self._authenticated or not self._access_token:
            await self.authenticate()
            return
        if self._token_expires and datetime.now() >= self._token_expires - _TOKEN_SKEW:
            _LOGGER.debug("Access token near expiry, refreshing")
            if not await self._refresh():
                await self.authenticate()

    async def close(self) -> None:
        """Drop local tokens. JWT logout is stateless."""
        self._authenticated = False
        self._access_token = None
        self._refresh_token = None
        self._token_expires = None
        self._live_sessions.clear()

    # -- Requests ------------------------------------------------------------

    async def _request(
        self, method: str, endpoint: str, timeout: int | None = None, **kwargs: Any
    ) -> Any:
        """Make an authenticated JSON request, retrying once after a refresh."""
        await self._async_ensure_token()

        url = self._build_url(endpoint)
        client_timeout = (
            aiohttp.ClientTimeout(total=timeout) if timeout else self._timeout
        )

        for attempt in (1, 2):
            headers = {**kwargs.pop("headers", {}), **self._auth_headers()}
            try:
                async with self._session.request(
                    method,
                    url,
                    headers=headers,
                    timeout=client_timeout,
                    ssl=self._verify_ssl,
                    **kwargs,
                ) as response:
                    if response.status == 401:
                        if attempt == 2:
                            raise ZMAuthenticationError(
                                "Authentication failed after refreshing the token"
                            )
                        if not await self._refresh():
                            await self.authenticate()
                        continue
                    if response.status == 404:
                        raise ZMApiError(f"Not found: {endpoint}")
                    response.raise_for_status()
                    if response.status == 204 or not response.content_length:
                        text = await response.text()
                        if not text:
                            return {}
                        return await response.json(content_type=None)
                    return await response.json(content_type=None)
            except aiohttp.ClientResponseError as err:
                raise ZMApiError(
                    f"{endpoint} returned {err.status}: {err.message}"
                ) from err
            except (aiohttp.ClientError, TimeoutError) as err:
                raise ZMConnectionError(f"Request to {endpoint} failed: {err}") from err

        raise ZMApiError(f"Request to {endpoint} did not complete")

    async def _paginate(self, endpoint: str, **params: Any) -> list[dict[str, Any]]:
        """Collect every page of a paginated collection endpoint."""
        items: list[dict[str, Any]] = []
        page = 1
        while True:
            response = await self._request(
                "GET",
                endpoint,
                params={**params, "page": page, "page_size": _PAGE_SIZE},
            )
            batch = response.get("items") or []
            items.extend(batch)
            last_page = response.get("last_page") or 1
            if page >= last_page or not batch:
                break
            page += 1
        return items

    # -- Server --------------------------------------------------------------

    async def get_version(self) -> str:
        """Return the ZoneMinder version."""
        response = await self._request("GET", V3_VERSION)
        return response.get("version", "unknown")

    async def get_server_info(self) -> ServerInfo:
        """Return version, daemon health and storage usage."""
        info = ServerInfo()

        version = await self._request("GET", V3_VERSION)
        info.version = version.get("version", "unknown")
        info.api_version = version.get("api_version")
        info.db_version = version.get("db_version")

        try:
            status = await self._request("GET", V3_SYSTEM_STATUS)
            daemons = status.get("daemons") or []
            info.running = bool(status.get("running"))
            info.daemons_total = len(daemons)
            info.daemons_running = sum(
                1 for d in daemons if d.get("state") == "running"
            )
        except (ZMApiError, ZMConnectionError) as err:
            _LOGGER.debug("System status unavailable: %s", err)

        try:
            for item in await self._paginate(V3_STORAGE):
                info.storage.append(StorageArea.from_v3_dict(item))
        except (ZMApiError, ZMConnectionError) as err:
            _LOGGER.debug("Storage list unavailable: %s", err)

        return info

    async def get_configs(self) -> dict[str, str]:
        """Return ZoneMinder's configuration keys and values."""
        configs: dict[str, str] = {}
        for item in await self._paginate(V3_CONFIGS):
            name = item.get("name")
            if name:
                configs[name] = item.get("value") or ""
        return configs

    # -- Monitors ------------------------------------------------------------

    async def get_monitors(self) -> list[Monitor]:
        """Return every monitor."""
        monitors = []
        for item in await self._paginate(V3_MONITORS):
            if item.get("deleted"):
                continue
            try:
                monitors.append(Monitor.from_v3_dict(item))
            except (KeyError, ValueError, TypeError) as err:
                _LOGGER.warning("Skipping unparsable monitor: %s", err)
        return monitors

    async def get_monitor(self, monitor_id: int) -> Monitor:
        """Return a single monitor."""
        response = await self._request("GET", V3_MONITOR.format(monitor_id=monitor_id))
        return Monitor.from_v3_dict(response)

    async def get_monitor_statuses(self) -> dict[int, MonitorStatus]:
        """Return live capture stats for every monitor in one request."""
        statuses: dict[int, MonitorStatus] = {}
        try:
            items = await self._paginate(V3_MONITOR_STATUS)
        except (ZMApiError, ZMConnectionError) as err:
            _LOGGER.debug("Monitor status unavailable: %s", err)
            return statuses
        for item in items:
            try:
                status = MonitorStatus.from_v3_dict(item)
            except (KeyError, ValueError, TypeError):
                continue
            statuses[status.monitor_id] = status
        return statuses

    async def set_monitor_state(
        self,
        monitor_id: int,
        *,
        capturing: str | None = None,
        analysing: str | None = None,
        recording: str | None = None,
        decoding: str | None = None,
    ) -> None:
        """Update a monitor's capture, analysis, recording or decoding mode."""
        body = {
            key: value
            for key, value in (
                ("capturing", capturing),
                ("analysing", analysing),
                ("recording", recording),
                ("decoding", decoding),
            )
            if value is not None
        }
        if not body:
            return
        await self._request(
            "PATCH", V3_MONITOR.format(monitor_id=monitor_id), json=body
        )
        _LOGGER.debug("Monitor %d updated: %s", monitor_id, body)

    # -- Events --------------------------------------------------------------

    async def get_events(
        self, monitor_id: int | None = None, limit: int = 100
    ) -> list[Event]:
        """Return events newest first, optionally filtered to one monitor."""
        params: dict[str, Any] = {
            "page": 1,
            "page_size": limit,
            "sort": "start_time",
            "direction": "desc",
        }
        if monitor_id is not None:
            params["monitor_id"] = monitor_id

        response = await self._request("GET", V3_EVENTS, params=params)
        events = []
        for item in response.get("items") or []:
            try:
                events.append(Event.from_v3_dict(item))
            except (KeyError, ValueError, TypeError) as err:
                _LOGGER.debug("Skipping unparsable event: %s", err)
        return events

    async def get_event(self, event_id: int) -> Event:
        """Return a single event."""
        response = await self._request("GET", V3_EVENT.format(event_id=event_id))
        return Event.from_v3_dict(response)

    async def get_events_between(
        self,
        monitor_id: int,
        start: datetime,
        end: datetime,
        limit: int = 500,
    ) -> list[Event]:
        """Return a monitor's events that started inside a time window."""
        response = await self._request(
            "GET",
            V3_EVENTS,
            params={
                "page": 1,
                "page_size": limit,
                "monitor_id": monitor_id,
                "start_time": _iso8601(start),
                "end_time": _iso8601(end),
                "sort": "start_time",
                "direction": "desc",
            },
        )
        events = []
        for item in response.get("items") or []:
            try:
                events.append(Event.from_v3_dict(item))
            except (KeyError, ValueError, TypeError) as err:
                _LOGGER.debug("Skipping unparsable event: %s", err)
        return events

    async def get_event_summary(self, monitor_id: int) -> EventSummary | None:
        """Return event counts and disk usage for a monitor."""
        try:
            response = await self._request(
                "GET", V3_EVENT_SUMMARY.format(monitor_id=monitor_id)
            )
            return EventSummary.from_v3_dict(response)
        except (ZMApiError, ZMConnectionError) as err:
            _LOGGER.debug("Event summary for monitor %d failed: %s", monitor_id, err)
            return None

    # -- Alarm and PTZ -------------------------------------------------------

    async def trigger_alarm(self, monitor_id: int, cause: str) -> None:
        """Force a monitor into alarm state."""
        await self._request(
            "PATCH",
            V3_MONITOR_ALARM.format(monitor_id=monitor_id),
            json={"action": "on", "cause": cause},
        )

    async def cancel_alarm(self, monitor_id: int) -> None:
        """Clear a forced alarm."""
        await self._request(
            "PATCH",
            V3_MONITOR_ALARM.format(monitor_id=monitor_id),
            json={"action": "off"},
        )

    async def ptz(self, monitor_id: int, command: str, **kwargs: Any) -> None:
        """Issue a PTZ command."""
        if command in _PTZ_MOVE_DIRECTIONS:
            endpoint = V3_PTZ_MOVE.format(
                monitor_id=monitor_id, direction=_PTZ_MOVE_DIRECTIONS[command]
            )
        elif command in _PTZ_ZOOM_DIRECTIONS:
            endpoint = V3_PTZ_ZOOM.format(
                monitor_id=monitor_id, direction=_PTZ_ZOOM_DIRECTIONS[command]
            )
        elif command in _PTZ_FOCUS_DIRECTIONS:
            endpoint = V3_PTZ_FOCUS.format(
                monitor_id=monitor_id, direction=_PTZ_FOCUS_DIRECTIONS[command]
            )
        elif command == "home":
            endpoint = V3_PTZ_HOME.format(monitor_id=monitor_id)
        elif command == "preset":
            preset = kwargs.get("preset")
            if preset is None:
                raise ZMApiError("The 'preset' command requires a preset number")
            endpoint = V3_PTZ_PRESET_GOTO.format(monitor_id=monitor_id, preset=preset)
        else:
            raise ZMNotSupportedError(f"Unsupported PTZ command: {command}")

        await self._request("POST", endpoint, json={})
        _LOGGER.debug("PTZ %s sent to monitor %d", command, monitor_id)

    async def get_ptz_presets(self, monitor_id: int) -> dict[int, str]:
        """Return the configured PTZ presets for a monitor."""
        presets: dict[int, str] = {}
        try:
            items = await self._paginate(V3_CONTROL_PRESETS, monitor_id=monitor_id)
        except (ZMApiError, ZMConnectionError) as err:
            _LOGGER.debug("PTZ presets for monitor %d failed: %s", monitor_id, err)
            return presets
        for item in items:
            if item.get("monitor_id") != monitor_id:
                continue
            number = item.get("preset")
            if number is None:
                continue
            presets[int(number)] = item.get("label") or f"Preset {number}"
        return presets

    # -- Live streaming ------------------------------------------------------

    async def async_prepare_live(self, monitor_id: int) -> None:
        """Start a live session so the HLS playlist and WebRTC socket exist.

        zm-api only materialises a monitor's playlist once a session is
        running, and sessions are reference counted server side, so we re-arm
        ours periodically rather than on every frame request.
        """
        last = self._live_sessions.get(monitor_id)
        if last and datetime.now() - last < _LIVE_SESSION_TTL:
            return
        try:
            await self._request(
                "POST",
                V3_LIVE_START.format(monitor_id=monitor_id),
                json={"enable_hls": True, "enable_webrtc": True},
                timeout=LONG_TIMEOUT,
            )
            self._live_sessions[monitor_id] = datetime.now()
            _LOGGER.debug("Live session started for monitor %d", monitor_id)
        except (ZMApiError, ZMConnectionError) as err:
            _LOGGER.warning(
                "Could not start a live session for monitor %d: %s", monitor_id, err
            )

    async def async_stop_live(self, monitor_id: int) -> None:
        """Release a live session."""
        self._live_sessions.pop(monitor_id, None)
        try:
            await self._request("DELETE", V3_LIVE_STOP.format(monitor_id=monitor_id))
        except (ZMApiError, ZMConnectionError) as err:
            _LOGGER.debug("Stopping live session %d failed: %s", monitor_id, err)

    async def get_live_stats(self, monitor_id: int) -> dict[str, Any]:
        """Return live session statistics."""
        return await self._request("GET", V3_LIVE_STATS.format(monitor_id=monitor_id))

    def get_stream_type(self, monitor_id: int) -> str:
        """zm-api serves HLS."""
        return STREAM_TYPE_HLS

    async def get_stream_source(self, monitor_id: int) -> str | None:
        """Return nothing. v3 live streams go through the media proxy.

        HLS segments require a bearer token that Home Assistant's stream
        component cannot attach, so the camera entity builds a proxy URL
        instead of using a direct source.
        """
        return None

    def get_webrtc_signaling_url(self, monitor_id: int) -> str | None:
        """Return the WebSocket URL for zm-api's native WebRTC signaling."""
        base = self._host.replace("https://", "wss://").replace("http://", "ws://")
        return f"{base}/{V3_LIVE_WEBRTC_WS.format(monitor_id=monitor_id)}"

    # -- Media ---------------------------------------------------------------

    def get_live_media_path(self, monitor_id: int) -> str:
        """Return the relative path of the live HLS master playlist."""
        return V3_LIVE_HLS_MASTER.format(monitor_id=monitor_id)

    def get_event_media_path(self, event_id: int) -> str:
        """Return the relative path of an event's video."""
        return V3_EVENT_VIDEO.format(event_id=event_id)

    def get_event_thumbnail_path(self, event_id: int) -> str:
        """Return the relative path of an event's thumbnail."""
        return V3_EVENT_THUMBNAIL.format(event_id=event_id)

    async def async_get_snapshot(self, monitor_id: int) -> bytes | None:
        """Return one JPEG still frame."""
        await self._async_ensure_token()
        url = self._build_url(V3_MONITOR_SNAPSHOT.format(monitor_id=monitor_id))
        for attempt in (1, 2):
            try:
                async with self._session.get(
                    url,
                    headers=self._auth_headers(),
                    timeout=aiohttp.ClientTimeout(total=LONG_TIMEOUT),
                    ssl=self._verify_ssl,
                ) as response:
                    if response.status == 401 and attempt == 1:
                        await self.authenticate()
                        continue
                    response.raise_for_status()
                    return await response.read()
            except (aiohttp.ClientError, TimeoutError) as err:
                _LOGGER.error("Snapshot for monitor %d failed: %s", monitor_id, err)
                return None
        return None

    @asynccontextmanager
    async def async_stream_media(
        self, path: str, headers: dict[str, str] | None = None
    ) -> AsyncIterator[aiohttp.ClientResponse]:
        """Yield an authenticated upstream response for a media path."""
        await self._async_ensure_token()
        url = self._build_url(path)
        request_headers = {**(headers or {}), **self._auth_headers()}
        async with self._session.get(
            url,
            headers=request_headers,
            timeout=aiohttp.ClientTimeout(
                total=None, sock_connect=DEFAULT_TIMEOUT, sock_read=LONG_TIMEOUT
            ),
            ssl=self._verify_ssl,
            allow_redirects=False,
        ) as response:
            yield response


def _iso8601(value: datetime) -> str:
    """Format a datetime the way zm-api's time filters expect."""
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
