"""Config flow for ZoneMinder integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .api import ZoneMinerAPI
from .const import (
    CONF_MQTT_ENABLED,
    CONF_MQTT_TOPIC,
    DEFAULT_MQTT_TOPIC,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .exceptions import ZMApiError, ZMAuthenticationError, ZMConnectionError

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from USER_DATA_SCHEMA with values provided by the user.
    """
    # Create API client
    session = aiohttp.ClientSession()
    api = ZoneMinerAPI(
        host=data[CONF_HOST],
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        session=session,
    )

    try:
        # Test authentication
        await api.authenticate()

        # Get version to verify API access
        version = await api.get_version()
        _LOGGER.info("Connected to ZoneMinder version %s", version)

        # Get monitors to verify we can fetch data
        monitors = await api.get_monitors()
        _LOGGER.info("Found %d monitors", len(monitors))

        # Return info for creating entry
        return {
            "title": f"ZoneMinder ({data[CONF_HOST]})",
            "version": version,
            "monitor_count": len(monitors),
        }

    finally:
        await api.close()
        await session.close()


class ZoneMinerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ZoneMinder."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                # Set unique ID based on host to prevent duplicates
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()

                # Create the config entry
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                    options={
                        CONF_MQTT_ENABLED: user_input.get(CONF_MQTT_ENABLED, True),
                        CONF_MQTT_TOPIC: DEFAULT_MQTT_TOPIC,
                    },
                )

            except ZMAuthenticationError:
                errors["base"] = "invalid_auth"
            except ZMConnectionError:
                errors["base"] = "cannot_connect"
            except ZMApiError:
                errors["base"] = "api_error"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during config flow")
                errors["base"] = "unknown"

        # Show form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_MQTT_ENABLED, default=True): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauth flow when credentials expire."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm reauth dialog."""
        errors: dict[str, str] = {}

        if user_input is not None:
            assert self._reauth_entry is not None

            # Build full data with new credentials
            data = {
                CONF_HOST: self._reauth_entry.data[CONF_HOST],
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }

            try:
                # Validate new credentials
                await validate_input(self.hass, data)

                # Update the entry
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={
                        CONF_HOST: data[CONF_HOST],
                        CONF_USERNAME: data[CONF_USERNAME],
                        CONF_PASSWORD: data[CONF_PASSWORD],
                    },
                )

                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)

                return self.async_abort(reason="reauth_successful")

            except ZMAuthenticationError:
                errors["base"] = "invalid_auth"
            except ZMConnectionError:
                errors["base"] = "cannot_connect"
            except ZMApiError:
                errors["base"] = "api_error"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reauth")
                errors["base"] = "unknown"

        # Show reauth form
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "host": self._reauth_entry.data[CONF_HOST]
                if self._reauth_entry
                else "Unknown"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ZoneMinerOptionsFlow:
        """Get the options flow for this handler."""
        return ZoneMinerOptionsFlow(config_entry)


class ZoneMinerOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for ZoneMinder."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_MQTT_ENABLED,
                        default=self.config_entry.options.get(CONF_MQTT_ENABLED, True),
                    ): bool,
                    vol.Optional(
                        CONF_MQTT_TOPIC,
                        default=self.config_entry.options.get(
                            CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC
                        ),
                    ): str,
                    vol.Optional(
                        "scan_interval",
                        default=self.config_entry.options.get(
                            "scan_interval", DEFAULT_SCAN_INTERVAL.total_seconds()
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                }
            ),
        )
