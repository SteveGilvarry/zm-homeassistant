# SPDX-License-Identifier: Apache-2.0
"""Show aiozoneminder errors in Home Assistant's UI."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiozoneminder import ZMError, ZMNotSupportedError
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import DOMAIN


@asynccontextmanager
async def ha_errors() -> AsyncIterator[None]:
    """Turn a ZoneMinder error during an action into one the UI shows.

    Without this, a failed button press or action shows "Unknown error" and
    leaves a traceback in the log.
    """
    try:
        yield
    except ZMNotSupportedError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="not_supported",
            translation_placeholders={"error": str(err)},
        ) from err
    except ZMError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="command_failed",
            translation_placeholders={"error": str(err)},
        ) from err
