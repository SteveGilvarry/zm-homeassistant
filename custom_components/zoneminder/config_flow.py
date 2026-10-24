# SPDX-License-Identifier: AGPL-3.0-or-later
"""Config flow for the ZoneMinder integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from aiozoneminder import ZMApiError, ZMAuthenticationError, ZMConnectionError
from aiozoneminder.const import BACKEND_LEGACY, BACKEND_V3, BACKENDS, DEFAULT_BACKEND
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .api import client_from_entry_data
from .const import (
    CONF_BACKEND,
    CONF_MQTT_ENABLED,
    CONF_MQTT_TOPIC,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    CONF_WEB_URL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .data import ZoneMinderConfigEntry

_LOGGER = logging.getLogger(__name__)

_BACKEND_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=list(BACKENDS),
        mode=SelectSelectorMode.LIST,
        translation_key="backend",
    )
)
_URL_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.URL))
_PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


def _user_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Return the schema for the credentials step."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_BACKEND, default=defaults.get(CONF_BACKEND, DEFAULT_BACKEND)
            ): _BACKEND_SELECTOR,
            vol.Required(
                CONF_HOST, default=defaults.get(CONF_HOST, "http://homeserver:8080")
            ): _URL_SELECTOR,
            vol.Required(
                CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")
            ): TextSelector(),
            vol.Required(CONF_PASSWORD): _PASSWORD_SELECTOR,
            vol.Optional(
                CONF_VERIFY_SSL, default=defaults.get(CONF_VERIFY_SSL, True)
            ): BooleanSelector(),
            vol.Optional(
                CONF_MQTT_ENABLED, default=defaults.get(CONF_MQTT_ENABLED, True)
            ): BooleanSelector(),
        }
    )


def _normalise_host(host: str) -> str:
    """Return a canonical form of the server URL, for the unique id."""
    return host.strip().rstrip("/").lower()


async def _async_validate(
    hass: HomeAssistant, data: Mapping[str, Any]
) -> dict[str, Any]:
    """Check the credentials and report what was found."""
    client = client_from_entry_data(dict(data), async_get_clientsession(hass))
    try:
        await client.authenticate()
        version = await client.get_version()
        monitors = await client.get_monitors()
    finally:
        await client.close()

    return {"version": version, "monitor_count": len(monitors)}


class ZoneMinderConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the ZoneMinder config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the server details."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await self._async_try(user_input)
            if not errors:
                await self.async_set_unique_id(_normalise_host(user_input[CONF_HOST]))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"ZoneMinder ({user_input[CONF_HOST]})",
                    data={
                        CONF_BACKEND: user_input.get(CONF_BACKEND, DEFAULT_BACKEND),
                        CONF_HOST: user_input[CONF_HOST].rstrip("/"),
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_VERIFY_SSL: user_input.get(CONF_VERIFY_SSL, True),
                    },
                    options={
                        CONF_MQTT_ENABLED: user_input.get(CONF_MQTT_ENABLED, True)
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
            description_placeholders={"default_port": "8080"},
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Move a server from the old YAML integration to a config entry.

        The core ZoneMinder integration only spoke the built-in API, so the
        imported entry does too; switch to API v3 later with Reconfigure.
        """
        scheme = "https" if import_data.get("ssl") else "http"
        path = "/" + str(import_data.get("path", "/zm/")).strip("/")
        host = f"{scheme}://{import_data[CONF_HOST]}{path}".rstrip("/")
        user_input = {
            CONF_BACKEND: BACKEND_LEGACY,
            CONF_HOST: host,
            CONF_USERNAME: import_data.get(CONF_USERNAME, ""),
            CONF_PASSWORD: import_data.get(CONF_PASSWORD, ""),
            CONF_VERIFY_SSL: import_data.get(CONF_VERIFY_SSL, True),
            CONF_MQTT_ENABLED: True,
        }
        await self.async_set_unique_id(_normalise_host(host))
        self._abort_if_unique_id_configured()
        if errors := await self._async_try(user_input):
            return self.async_abort(reason=errors["base"])
        return self.async_create_entry(
            title=f"ZoneMinder ({host})",
            data={k: v for k, v in user_input.items() if k != CONF_MQTT_ENABLED},
            options={CONF_MQTT_ENABLED: True},
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start the re-authentication flow."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for fresh credentials."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            candidate = {**entry.data, **user_input}
            errors = await self._async_try(candidate)
            if not errors:
                return self.async_update_reload_and_abort(entry, data=candidate)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME, default=entry.data.get(CONF_USERNAME, "")
                    ): TextSelector(),
                    vol.Required(CONF_PASSWORD): _PASSWORD_SELECTOR,
                }
            ),
            errors=errors,
            description_placeholders={"host": entry.data[CONF_HOST]},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the server address or backend of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await self._async_try(user_input)
            if not errors:
                # The unique id is the URL, so moving the server (new port,
                # zm-api instead of /zm) changes it. Allow that, but refuse an
                # address another entry already owns.
                unique_id = _normalise_host(user_input[CONF_HOST])
                if unique_id != entry.unique_id:
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=unique_id,
                    title=f"ZoneMinder ({user_input[CONF_HOST].rstrip('/')})",
                    data_updates={
                        CONF_BACKEND: user_input.get(CONF_BACKEND, DEFAULT_BACKEND),
                        CONF_HOST: user_input[CONF_HOST].rstrip("/"),
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_VERIFY_SSL: user_input.get(CONF_VERIFY_SSL, True),
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_user_schema(user_input or entry.data),
            errors=errors,
        )

    async def _async_try(self, data: Mapping[str, Any]) -> dict[str, str]:
        """Validate input and translate failures into form errors."""
        try:
            info = await _async_validate(self.hass, data)
        except ZMAuthenticationError:
            return {"base": "invalid_auth"}
        except ZMConnectionError:
            return {"base": "cannot_connect"}
        except ZMApiError:
            return {"base": "api_error"}
        except Exception:
            _LOGGER.exception("Unexpected error while validating ZoneMinder")
            return {"base": "unknown"}

        _LOGGER.debug(
            "Validated ZoneMinder %s with %d monitors",
            info["version"],
            info["monitor_count"],
        )
        return {}

    @staticmethod
    @callback
    def async_get_options_flow(entry: ZoneMinderConfigEntry) -> ZoneMinderOptionsFlow:
        """Return the options flow."""
        return ZoneMinderOptionsFlow()


class ZoneMinderOptionsFlow(OptionsFlow):
    """Handle the ZoneMinder options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the options."""
        if user_input is not None:
            cleaned = {
                key: value
                for key, value in user_input.items()
                if value not in (None, "")
            }
            if CONF_SCAN_INTERVAL in cleaned:
                cleaned[CONF_SCAN_INTERVAL] = int(cleaned[CONF_SCAN_INTERVAL])
            return self.async_create_entry(data=cleaned)

        options = self.config_entry.options
        is_v3 = self.config_entry.data.get(CONF_BACKEND, DEFAULT_BACKEND) == BACKEND_V3

        schema: dict[Any, Any] = {
            vol.Optional(
                CONF_MQTT_ENABLED, default=options.get(CONF_MQTT_ENABLED, True)
            ): BooleanSelector(),
            vol.Optional(
                CONF_MQTT_TOPIC,
                description={"suggested_value": options.get(CONF_MQTT_TOPIC)},
            ): TextSelector(),
            vol.Optional(
                CONF_SCAN_INTERVAL,
                description={"suggested_value": options.get(CONF_SCAN_INTERVAL)},
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL,
                    max=MAX_SCAN_INTERVAL,
                    step=5,
                    unit_of_measurement="seconds",
                    mode=NumberSelectorMode.BOX,
                )
            ),
        }
        if is_v3:
            # The zm-api server and the ZoneMinder web UI are usually on
            # different ports, so the "Visit device" link needs its own address.
            schema[
                vol.Optional(
                    CONF_WEB_URL,
                    description={"suggested_value": options.get(CONF_WEB_URL)},
                )
            ] = _URL_SELECTOR

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))
