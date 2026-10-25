# SPDX-License-Identifier: Apache-2.0
"""WebRTC straight from ZoneMinder API v3.

The browser's offer goes to zm-api's WHEP endpoint and the answer comes
back, so video flows from ZoneMinder to the browser with nothing re-packaging
it on the way. Home Assistant only relays the signalling, which keeps
ZoneMinder's token on the server.

This is a WebRTC *provider* rather than a native camera implementation on
purpose: Home Assistant then still offers HLS beside WebRTC, so a browser that
can't reach ZoneMinder over WebRTC (away from home, no TURN) falls back to HLS
instead of showing nothing.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from aiozoneminder import ZMApiError, ZMConnectionError, ZMError
from homeassistant.components.camera import Camera
from homeassistant.components.camera.webrtc import (
    CameraWebRTCProvider,
    WebRTCAnswer,
    WebRTCError,
    WebRTCSendMessage,
)
from homeassistant.core import HomeAssistant, callback
from webrtc_models import RTCIceCandidateInit

from .const import DOMAIN

if TYPE_CHECKING:
    from aiozoneminder import ZoneMinderV3Client

_LOGGER = logging.getLogger(__name__)


class ZoneMinderWebRTCProvider(CameraWebRTCProvider):
    """Relay WebRTC signalling between the browser and zm-api."""

    def __init__(self, hass: HomeAssistant, api: ZoneMinderV3Client) -> None:
        """Initialize the provider for one ZoneMinder server."""
        self.hass = hass
        self.api = api
        #: HA session id -> zm-api session URL.
        self._sessions: dict[str, str] = {}
        #: Browser candidates that arrive while zm-api is still answering the
        #: offer, held until the session URL is known.
        self._early: dict[str, list[RTCIceCandidateInit]] = {}
        #: Sessions the viewer closed before the answer came back.
        self._closed_early: set[str] = set()

    @property
    def domain(self) -> str:
        """Return the integration domain."""
        return DOMAIN

    @callback
    def async_is_supported(self, stream_source: str) -> bool:
        """Never chosen for other cameras; ours attach it directly."""
        return False

    async def async_handle_async_webrtc_offer(
        self,
        camera: Camera,
        offer_sdp: str,
        session_id: str,
        send_message: WebRTCSendMessage,
    ) -> None:
        """Hand the offer to zm-api and send its answer back."""
        monitor_id: int = camera.monitor_id  # type: ignore[attr-defined]
        started = time.monotonic()
        _LOGGER.debug(
            "WebRTC offer for monitor %d (session %s)", monitor_id, session_id
        )
        self._early[session_id] = []
        try:
            answer, location = await self.api.async_whep_offer(monitor_id, offer_sdp)
        except (ZMApiError, ZMConnectionError) as err:
            self._early.pop(session_id, None)
            self._closed_early.discard(session_id)
            _LOGGER.debug("WebRTC offer for monitor %d failed: %s", monitor_id, err)
            send_message(WebRTCError("webrtc_offer_failed", str(err)))
            return
        early = self._early.pop(session_id, [])
        if session_id in self._closed_early:
            # The viewer left while zm-api was answering: end its session too.
            self._closed_early.discard(session_id)
            await self.api.async_whep_close(location)
            return
        _LOGGER.debug(
            "WebRTC answer for monitor %d in %.2fs",
            monitor_id,
            time.monotonic() - started,
        )
        self._sessions[session_id] = location
        send_message(WebRTCAnswer(answer))
        for candidate in early:
            await self.async_on_webrtc_candidate(session_id, candidate)

    async def async_on_webrtc_candidate(
        self, session_id: str, candidate: RTCIceCandidateInit
    ) -> None:
        """Trickle a browser candidate to zm-api."""
        if (location := self._sessions.get(session_id)) is None:
            # The browser trickles straight after its offer; keep candidates
            # until zm-api's answer gives the session URL.
            if session_id in self._early:
                self._early[session_id].append(candidate)
            return
        try:
            await self.api.async_whep_candidate(
                location, candidate.sdp_mid, candidate.candidate
            )
        except ZMError as err:
            # One lost candidate rarely matters; ICE tries the others.
            _LOGGER.debug("WebRTC candidate for %s not sent: %s", location, err)

    @callback
    def async_close_session(self, session_id: str) -> None:
        """Tell zm-api the viewer has gone."""
        if (location := self._sessions.pop(session_id, None)) is None:
            if session_id in self._early:
                self._closed_early.add(session_id)
            return
        self.hass.async_create_background_task(
            self.api.async_whep_close(location), name="zoneminder webrtc close"
        )
