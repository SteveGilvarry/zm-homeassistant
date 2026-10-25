"""Fixtures for the live tests, which talk to a real ZoneMinder server.

Nothing here runs unless the server is configured through environment
variables (see the "Live tests" part of the README):

- ``ZM_LIVE_V2_URL``: ZoneMinder's address for the built-in API v2, such as
  ``http://zm.local/zm``
- ``ZM_LIVE_V3_URL``: the address of zm-api (API v3), such as
  ``http://zm.local``
- ``ZM_LIVE_USER`` and ``ZM_LIVE_PASSWORD``: an administrator
- ``ZM_LIVE_MONITOR``: optional, the id or name of the monitor to use
- ``ZM_LIVE_RESTRICTED_USER`` and ``ZM_LIVE_RESTRICTED_PASSWORD``: optional, a
  user who may view monitors and events but not System
- ``ZM_LIVE_TIMEZONE``: optional, the server's time zone (default UTC)
- ``ZM_LIVE_WRITE=1``: also run the tests that change the server

Every test runs once per configured API. Without a URL, or without the user
and password, every test is skipped.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from dataclasses import dataclass
import os
import socket

from aiozoneminder.const import BACKEND_LEGACY, BACKEND_V3
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zoneminder.const import (
    CONF_BACKEND,
    CONF_MQTT_ENABLED,
    CONF_VERIFY_SSL,
    DOMAIN,
)

#: zm-api allows a burst of logins, then about one every two seconds per
#: address. A setup refused for that is retried once after this long.
LOGIN_BACKOFF = 40


@dataclass(frozen=True)
class LiveServer:
    """One configured API of the server under test."""

    name: str
    backend: str
    url: str


@dataclass(frozen=True)
class LiveSettings:
    """The live test configuration, read from the environment."""

    servers: dict[str, LiveServer]
    username: str
    password: str
    monitor: str
    restricted_user: str
    restricted_password: str
    timezone: str
    write: bool

    @property
    def skip_reason(self) -> str | None:
        """Return why the live tests can't run, or None when they can."""
        if not self.servers:
            return "live tests: set ZM_LIVE_V2_URL and/or ZM_LIVE_V3_URL"
        if not self.username or not self.password:
            return "live tests: set ZM_LIVE_USER and ZM_LIVE_PASSWORD"
        return None


def _settings() -> LiveSettings:
    env = os.environ
    servers = {
        name: LiveServer(name, backend, url.rstrip("/"))
        for name, backend, url in (
            ("v2", BACKEND_LEGACY, env.get("ZM_LIVE_V2_URL", "")),
            ("v3", BACKEND_V3, env.get("ZM_LIVE_V3_URL", "")),
        )
        if url
    }
    return LiveSettings(
        servers=servers,
        username=env.get("ZM_LIVE_USER", ""),
        password=env.get("ZM_LIVE_PASSWORD", ""),
        monitor=env.get("ZM_LIVE_MONITOR", ""),
        restricted_user=env.get("ZM_LIVE_RESTRICTED_USER", ""),
        restricted_password=env.get("ZM_LIVE_RESTRICTED_PASSWORD", ""),
        timezone=env.get("ZM_LIVE_TIMEZONE", "UTC"),
        write=env.get("ZM_LIVE_WRITE", "") == "1",
    )


SETTINGS = _settings()

# Home Assistant's test plugin blocks every socket and allows only 127.0.0.1
# once a test starts. These run before that, so they are the real functions.
_REAL_NETWORK = {
    (socket.socket, "connect"): socket.socket.connect,
    (socket, "getaddrinfo"): socket.getaddrinfo,
    (socket, "gethostbyname"): socket.gethostbyname,
    (socket, "gethostbyname_ex"): socket.gethostbyname_ex,
}


def pytest_configure(config: pytest.Config) -> None:
    """Register the live test markers."""
    config.addinivalue_line(
        "markers", "live_write: changes the server; runs only with ZM_LIVE_WRITE=1"
    )
    config.addinivalue_line(
        "markers",
        "live_xfail(*apis, reason): expected to fail on these APIs (v2, v3) "
        "until the fix named in reason is merged",
    )


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Run each test once per configured API, or skip it."""
    if "server" not in metafunc.fixturenames:
        return
    if reason := SETTINGS.skip_reason:
        metafunc.parametrize(
            "server", [pytest.param(None, marks=pytest.mark.skip(reason=reason))]
        )
        return
    writes = metafunc.definition.get_closest_marker("live_write") is not None
    params = []
    for name, server in SETTINGS.servers.items():
        marks = [
            pytest.mark.xfail(strict=False, reason=marker.kwargs["reason"])
            for marker in metafunc.definition.iter_markers("live_xfail")
            if name in marker.args
        ]
        if writes and not SETTINGS.write:
            marks.append(pytest.mark.skip(reason="changes the server: ZM_LIVE_WRITE=1"))
        params.append(pytest.param(server, marks=marks, id=name))
    metafunc.parametrize("server", params)


@pytest.fixture(autouse=True)
def live_network(socket_enabled: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Let the test reach the ZoneMinder server, by name or by address."""
    for (owner, name), real in _REAL_NETWORK.items():
        monkeypatch.setattr(owner, name, real)


# The integration's timers and Home Assistant's stream worker outlive a test by
# design. Each entry is unloaded in teardown, which is what matters here.
@pytest.fixture
def expected_lingering_timers() -> bool:
    """Allow timers left behind by a live entry."""
    return True


@pytest.fixture
def expected_lingering_tasks() -> bool:
    """Allow tasks left behind by a live entry."""
    return True


@pytest.fixture
def settings() -> LiveSettings:
    """Return the live test configuration."""
    return SETTINGS


def entry_data(server: LiveServer, username: str, password: str) -> dict[str, str]:
    """Return what the config flow is given for this server and user."""
    return {
        CONF_BACKEND: server.backend,
        CONF_HOST: server.url,
        CONF_USERNAME: username,
        CONF_PASSWORD: password,
        CONF_VERIFY_SSL: False,
        CONF_MQTT_ENABLED: False,
    }


async def async_add_entry(
    hass: HomeAssistant, server: LiveServer, username: str, password: str
) -> MockConfigEntry:
    """Add and set up an entry for the server, as the config flow would."""
    await hass.config.async_set_time_zone(SETTINGS.timezone)
    data = entry_data(server, username, password)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"ZoneMinder ({server.url})",
        unique_id=server.url.lower(),
        data={k: v for k, v in data.items() if k != CONF_MQTT_ENABLED},
        options={CONF_MQTT_ENABLED: False},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    if entry.state is ConfigEntryState.SETUP_RETRY:
        # Most likely zm-api's login limit; wait for it once.
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        await asyncio.sleep(LOGIN_BACKOFF)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED, f"{entry.state}: {entry.reason}"
    return entry


@pytest.fixture
async def entry(
    hass: HomeAssistant, server: LiveServer
) -> AsyncGenerator[MockConfigEntry]:
    """Set the integration up against the server as the administrator."""
    entry = await async_add_entry(hass, server, SETTINGS.username, SETTINGS.password)
    yield entry
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
