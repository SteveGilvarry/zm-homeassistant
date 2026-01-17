"""ZoneMinder API client."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    API_ALARM_OFF,
    API_ALARM_ON,
    API_EVENT,
    API_EVENTS,
    API_LOGIN,
    API_LOGOUT,
    API_MONITOR,
    API_MONITORS,
    API_VERSION,
    DEFAULT_TIMEOUT,
    EVENT_VIDEO_PATH,
    STREAM_PATH,
)
from .exceptions import ZMApiError, ZMAuthenticationError, ZMConnectionError
from .models import Event, Monitor

_LOGGER = logging.getLogger(__name__)


class ZoneMinerAPI:
    """ZoneMinder API Client."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the API client.

        Args:
            host: ZoneMinder server URL (e.g., http://zm.local)
            username: Username for authentication
            password: Password for authentication
            session: aiohttp ClientSession for making requests
            timeout: Request timeout in seconds

        """
        self._host = host.rstrip("/")
        self._username = username
        self._password = password
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._auth_token: str | None = None
        self._authenticated = False

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from host and endpoint.

        Args:
            endpoint: API endpoint path (relative, no leading slash)

        Returns:
            Full URL

        """
        return f"{self._host}/{endpoint}"

    async def authenticate(self) -> bool:
        """Authenticate with ZoneMinder.

        Returns:
            True if authentication successful

        Raises:
            ZMAuthenticationError: If authentication fails
            ZMConnectionError: If connection to server fails

        """
        url = self._build_url(API_LOGIN)
        data = {
            "username": self._username,
            "password": self._password,
        }

        try:
            async with self._session.post(
                url,
                data=data,
                timeout=self._timeout,
                allow_redirects=True,
            ) as response:
                if response.status == 401:
                    raise ZMAuthenticationError("Invalid username or password")

                if response.status == 404:
                    # Try to provide helpful error message
                    text = await response.text()
                    raise ZMConnectionError(
                        f"API endpoint not found (404). "
                        f"Please check:\n"
                        f"  1. ZoneMinder is installed and running\n"
                        f"  2. API is enabled in ZM settings\n"
                        f"  3. Host URL is correct: {self._host}\n"
                        f"  Response: {text[:200]}"
                    )

                response.raise_for_status()
                result = await response.json()

                # Extract auth token from response
                self._auth_token = result.get("access_token")
                if not self._auth_token:
                    # Some ZM versions use different response format
                    self._auth_token = result.get("credentials")

                self._authenticated = True
                _LOGGER.debug("Successfully authenticated with ZoneMinder")
                return True

        except aiohttp.ClientError as err:
            raise ZMConnectionError(f"Connection failed: {err}") from err
        except Exception as err:
            raise ZMApiError(f"Authentication error: {err}") from err

    async def logout(self) -> None:
        """Logout from ZoneMinder."""
        if not self._authenticated:
            return

        try:
            url = self._build_url(API_LOGOUT)
            async with self._session.get(
                url,
                params={"token": self._auth_token},
                timeout=self._timeout,
            ) as response:
                response.raise_for_status()
                self._authenticated = False
                self._auth_token = None
                _LOGGER.debug("Successfully logged out from ZoneMinder")
        except Exception as err:
            _LOGGER.warning("Logout failed: %s", err)

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an authenticated request to ZoneMinder API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to the request

        Returns:
            JSON response as dictionary

        Raises:
            ZMAuthenticationError: If authentication required or fails
            ZMConnectionError: If connection fails
            ZMApiError: If API returns an error

        """
        if not self._authenticated:
            await self.authenticate()

        url = self._build_url(endpoint)

        # Add auth token to request
        params = kwargs.pop("params", {})
        if self._auth_token:
            params["token"] = self._auth_token

        try:
            async with self._session.request(
                method,
                url,
                params=params,
                timeout=self._timeout,
                **kwargs,
            ) as response:
                if response.status == 401:
                    # Token expired, re-authenticate
                    self._authenticated = False
                    raise ZMAuthenticationError("Authentication token expired")

                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientError as err:
            raise ZMConnectionError(f"Request failed: {err}") from err
        except ZMAuthenticationError:
            raise
        except Exception as err:
            raise ZMApiError(f"API request error: {err}") from err

    async def get_version(self) -> str:
        """Get ZoneMinder version.

        Returns:
            Version string (e.g., "1.37.0")

        """
        response = await self._request("GET", API_VERSION)
        version = response.get("version", "unknown")
        _LOGGER.debug("ZoneMinder version: %s", version)
        return version

    async def get_monitors(self) -> list[Monitor]:
        """Get list of all monitors.

        Returns:
            List of Monitor objects

        """
        response = await self._request("GET", API_MONITORS)
        monitors = []

        for monitor_data in response.get("monitors", []):
            try:
                monitor = Monitor.from_dict(monitor_data)
                monitors.append(monitor)
            except (KeyError, ValueError) as err:
                _LOGGER.warning("Failed to parse monitor data: %s", err)
                continue

        _LOGGER.debug("Found %d monitors", len(monitors))
        return monitors

    async def get_monitor(self, monitor_id: int) -> Monitor:
        """Get single monitor details.

        Args:
            monitor_id: Monitor ID

        Returns:
            Monitor object

        """
        endpoint = API_MONITOR.format(monitor_id=monitor_id)
        response = await self._request("GET", endpoint)

        monitor_data = response.get("monitor", {})
        return Monitor.from_dict(monitor_data)

    async def get_events(
        self,
        monitor_id: int | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Get events, optionally filtered by monitor.

        Args:
            monitor_id: Optional monitor ID to filter events
            limit: Maximum number of events to return

        Returns:
            List of Event objects (empty list if events API is unavailable)

        """
        params: dict[str, Any] = {"limit": limit}

        if monitor_id is not None:
            params["MonitorId"] = monitor_id

        try:
            response = await self._request("GET", API_EVENTS, params=params)
            events = []

            for event_data in response.get("events", []):
                try:
                    event = Event.from_dict(event_data)
                    events.append(event)
                except (KeyError, ValueError) as err:
                    _LOGGER.warning("Failed to parse event data: %s", err)
                    continue

            _LOGGER.debug("Found %d events", len(events))
            return events

        except (ZMConnectionError, ZMApiError) as err:
            # Events API may be broken on some ZM installations
            # Return empty list and log warning
            _LOGGER.warning(
                "Events API unavailable (this is a ZM server issue): %s", err
            )
            return []

    async def get_event(self, event_id: int) -> Event:
        """Get single event details.

        Args:
            event_id: Event ID

        Returns:
            Event object

        """
        endpoint = API_EVENT.format(event_id=event_id)
        response = await self._request("GET", endpoint)

        event_data = response.get("event", {})
        return Event.from_dict(event_data)

    async def trigger_alarm(self, monitor_id: int, cause: str = "HA Manual Trigger") -> bool:
        """Trigger manual alarm on a monitor.

        Args:
            monitor_id: Monitor ID
            cause: Reason for triggering the alarm

        Returns:
            True if successful

        """
        endpoint = API_ALARM_ON.format(monitor_id=monitor_id)
        params = {"cause": cause}

        try:
            await self._request("GET", endpoint, params=params)
            _LOGGER.info("Triggered alarm on monitor %d: %s", monitor_id, cause)
            return True
        except Exception as err:
            _LOGGER.error("Failed to trigger alarm on monitor %d: %s", monitor_id, err)
            return False

    async def cancel_alarm(self, monitor_id: int) -> bool:
        """Cancel alarm on a monitor.

        Args:
            monitor_id: Monitor ID

        Returns:
            True if successful

        """
        endpoint = API_ALARM_OFF.format(monitor_id=monitor_id)

        try:
            await self._request("GET", endpoint)
            _LOGGER.info("Cancelled alarm on monitor %d", monitor_id)
            return True
        except Exception as err:
            _LOGGER.error("Failed to cancel alarm on monitor %d: %s", monitor_id, err)
            return False

    async def set_monitor_function(self, monitor_id: int, function: str) -> bool:
        """Set monitor function/mode.

        Args:
            monitor_id: Monitor ID
            function: Monitor function (Monitor, Modect, Record, etc.)

        Returns:
            True if successful

        """
        endpoint = API_MONITOR.format(monitor_id=monitor_id)
        data = {"Monitor[Function]": function}

        try:
            await self._request("POST", endpoint, data=data)
            _LOGGER.info("Set monitor %d function to %s", monitor_id, function)
            return True
        except Exception as err:
            _LOGGER.error(
                "Failed to set monitor %d function to %s: %s",
                monitor_id,
                function,
                err,
            )
            return False

    def get_stream_url(self, monitor_id: int, mode: str = "jpeg") -> str:
        """Get live stream URL for a monitor.

        Args:
            monitor_id: Monitor ID
            mode: Stream mode (jpeg for MJPEG, single for snapshot)

        Returns:
            Full stream URL

        """
        params = {
            "mode": mode,
            "monitor": monitor_id,
            "maxfps": 30,
            "buffer": 1000,
        }

        if self._auth_token:
            params["token"] = self._auth_token

        # Build query string
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{self._host}{STREAM_PATH}?{query}"

        _LOGGER.debug("Stream URL for monitor %d: %s", monitor_id, url)
        return url

    def get_event_clip_url(self, event_id: int) -> str:
        """Get event video clip URL.

        Args:
            event_id: Event ID

        Returns:
            Full event video URL

        """
        path = EVENT_VIDEO_PATH.format(event_id=event_id)
        url = f"{self._host}{path}"

        if self._auth_token:
            url += f"?token={self._auth_token}"

        _LOGGER.debug("Event clip URL for event %d: %s", event_id, url)
        return url

    async def ptz_move(
        self,
        monitor_id: int,
        control: str,
        x_coord: int | None = None,
        y_coord: int | None = None,
    ) -> bool:
        """Send PTZ command to a monitor.

        Args:
            monitor_id: Monitor ID
            control: PTZ control command (moveLeft, moveRight, etc.)
            x_coord: Optional X coordinate for relative movements
            y_coord: Optional Y coordinate for relative movements

        Returns:
            True if successful

        """
        endpoint = f"/api/controls/{monitor_id}.json"
        data = {"control": control}

        if x_coord is not None:
            data["xCoord"] = x_coord
        if y_coord is not None:
            data["yCoord"] = y_coord

        try:
            await self._request("POST", endpoint, data=data)
            _LOGGER.info("Sent PTZ command %s to monitor %d", control, monitor_id)
            return True
        except Exception as err:
            _LOGGER.error(
                "Failed to send PTZ command %s to monitor %d: %s",
                control,
                monitor_id,
                err,
            )
            return False

    async def close(self) -> None:
        """Close the API client and logout."""
        await self.logout()
