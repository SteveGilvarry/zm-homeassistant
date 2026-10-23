# SPDX-License-Identifier: AGPL-3.0-or-later
"""Exceptions raised by the ZoneMinder integration."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError


class ZMError(HomeAssistantError):
    """Base class for every ZoneMinder error.

    Deriving from HomeAssistantError means an error raised while handling a
    service call or an entity command surfaces in the UI instead of vanishing
    into the log.
    """


class ZMConnectionError(ZMError):
    """The ZoneMinder server could not be reached."""


class ZMAuthenticationError(ZMError):
    """Credentials were rejected, or the session could not be refreshed."""


class ZMApiError(ZMError):
    """The server was reached but returned an error."""


class ZMNotSupportedError(ZMError):
    """The active backend does not implement the requested capability."""
