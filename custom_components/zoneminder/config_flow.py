# SPDX-License-Identifier: Apache-2.0
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
from homeassistant.data_entry_flow import AbortFlow
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
    CONF_EVENT_PERIODS,
    CONF_FUNCTION_OFF,
    CONF_FUNCTION_ON,
    CONF_MQTT_ENABLED,
    CONF_MQTT_TOPIC,
    CONF_SCAN_INTERVAL,
    CONF_STREAM_MAXFPS,
    CONF_STREAM_SCALE,
    CONF_VERIFY_SSL,
    CONF_WEB_URL,
    CONF_ZMS_PATH,
    DEFAULT_EVENT_PERIODS,
    DOMAIN,
    EVENT_PERIODS,
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


#: Options the YAML import can set from the old platform blocks.
_IMPORTED_OPTIONS = (
    CONF_EVENT_PERIODS,
    CONF_FUNCTION_ON,
    CONF_FUNCTION_OFF,
    CONF_SCAN_INTERVAL,
)


def _normalise_host(host: str) -> str:
    """Return a canonical form of the server URL, for spotting duplicates."""
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

    VERSION = 2
    MINOR_VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the server details."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await self._async_try(user_input)
            if not errors:
                self._abort_if_host_configured(user_input[CONF_HOST])
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

    def _entry_for_host(
        self, host: str, exclude: ZoneMinderConfigEntry | None = None
    ) -> ZoneMinderConfigEntry | None:
        """Return the entry already using this server address, if any.

        ZoneMinder has no serial number or other stable id, and Home Assistant
        doesn't allow a URL as a unique id, so entries have none. Duplicates
        are found by address instead, ignoring case and a trailing slash.
        """
        wanted = _normalise_host(host)
        return next(
            (
                entry
                for entry in self._async_current_entries(include_ignore=False)
                if entry is not exclude
                and _normalise_host(entry.data.get(CONF_HOST, "")) == wanted
            ),
            None,
        )

    def _abort_if_host_configured(
        self, host: str, exclude: ZoneMinderConfigEntry | None = None
    ) -> None:
        """Abort when another entry already uses this server address."""
        if self._entry_for_host(host, exclude) is not None:
            raise AbortFlow("already_configured")

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
        if zms_path := import_data.get(CONF_ZMS_PATH):
            user_input[CONF_ZMS_PATH] = zms_path
        # Settings from the old platform blocks (see yaml_import.py).
        imported = {
            key: import_data[key] for key in _IMPORTED_OPTIONS if key in import_data
        }

        if entry := self._entry_for_host(host):
            # Imported before platform settings were read: add them, but
            # never overwrite what the user has set since.
            if missing := {k: v for k, v in imported.items() if k not in entry.options}:
                self.hass.config_entries.async_update_entry(
                    entry, options={**entry.options, **missing}
                )
            return self.async_abort(reason="already_configured")
        if errors := await self._async_try(user_input):
            return self.async_abort(reason=errors["base"])
        return self.async_create_entry(
            title=f"ZoneMinder ({host})",
            data={k: v for k, v in user_input.items() if k != CONF_MQTT_ENABLED},
            options={CONF_MQTT_ENABLED: True, **imported},
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
                # Moving the server (new port, zm-api instead of /zm) is fine,
                # but not onto an address another entry already uses.
                self._abort_if_host_configured(user_input[CONF_HOST], entry)
                return self.async_update_reload_and_abort(
                    entry,
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
            for key in (CONF_SCAN_INTERVAL, CONF_STREAM_SCALE, CONF_STREAM_MAXFPS):
                if key in cleaned:
                    cleaned[key] = int(cleaned[key])
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
        schema[
            vol.Optional(
                CONF_EVENT_PERIODS,
                default=options.get(CONF_EVENT_PERIODS, DEFAULT_EVENT_PERIODS),
            )
        ] = SelectSelector(
            SelectSelectorConfig(
                options=EVENT_PERIODS,
                multiple=True,
                translation_key=CONF_EVENT_PERIODS,
            )
        )
        if not is_v3:
            # Only API v2 streams MJPEG, which these shrink and slow down.
            schema[
                vol.Optional(
                    CONF_STREAM_SCALE,
                    description={"suggested_value": options.get(CONF_STREAM_SCALE)},
                )
            ] = NumberSelector(
                NumberSelectorConfig(
                    min=10,
                    max=100,
                    step=5,
                    unit_of_measurement="%",
                    mode=NumberSelectorMode.BOX,
                )
            )
            schema[
                vol.Optional(
                    CONF_STREAM_MAXFPS,
                    description={"suggested_value": options.get(CONF_STREAM_MAXFPS)},
                )
            ] = NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=30,
                    step=1,
                    unit_of_measurement="fps",
                    mode=NumberSelectorMode.BOX,
                )
            )
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
