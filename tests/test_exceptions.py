"""Tests for showing ZoneMinder errors in the UI."""

from __future__ import annotations

from aiozoneminder import ZMApiError, ZMConnectionError, ZMNotSupportedError
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import pytest

from custom_components.zoneminder.exceptions import ha_errors


@pytest.mark.parametrize("error", [ZMApiError("locked"), ZMConnectionError("locked")])
async def test_failures_become_home_assistant_errors(error: Exception) -> None:
    with pytest.raises(HomeAssistantError) as raised:
        async with ha_errors():
            raise error
    assert raised.value.translation_key == "command_failed"
    assert raised.value.translation_placeholders == {"error": "locked"}
    assert raised.value.__cause__ is error


async def test_unsupported_is_a_validation_error() -> None:
    with pytest.raises(ServiceValidationError) as raised:
        async with ha_errors():
            raise ZMNotSupportedError("needs API v3")
    assert raised.value.translation_key == "not_supported"


async def test_other_errors_pass_through() -> None:
    with pytest.raises(KeyError):
        async with ha_errors():
            raise KeyError("not ours")
