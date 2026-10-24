# SPDX-License-Identifier: Apache-2.0
"""Shared entity base classes for the ZoneMinder integration."""

from __future__ import annotations

from aiozoneminder import Monitor
from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_WEB_URL, DOMAIN
from .coordinator import ZoneMinderDataUpdateCoordinator
from .data import ZoneMinderConfigEntry

#: HA 2026.8 links devices by registry id and rejects the old identifier
#: tuple. Older releases only understand the tuple.
_LINK_BY_ID = "via_device_id" in DeviceInfo.__annotations__


def server_device_id(entry: ZoneMinderConfigEntry) -> str:
    """Return the device registry identifier for the ZoneMinder server."""
    return entry.entry_id


def monitor_device_id(entry: ZoneMinderConfigEntry, monitor_id: int) -> str:
    """Return the device registry identifier for one monitor.

    The entry id is part of the identifier so that two ZoneMinder servers can
    be added to the same Home Assistant without their monitors colliding.
    """
    return f"{entry.entry_id}_{monitor_id}"


def _web_url(entry: ZoneMinderConfigEntry) -> str | None:
    """Return the configured ZoneMinder web UI URL, if there is one."""
    url = entry.options.get(CONF_WEB_URL)
    return str(url).rstrip("/") if url else None


def server_device_info(entry: ZoneMinderConfigEntry, version: str) -> DeviceInfo:
    """Return device info for the ZoneMinder server itself."""
    return DeviceInfo(
        identifiers={(DOMAIN, server_device_id(entry))},
        name=entry.title,
        manufacturer="ZoneMinder",
        model="ZoneMinder server",
        sw_version=version,
        configuration_url=_web_url(entry) or entry.data.get(CONF_HOST),
    )


class ZoneMinderEntity(CoordinatorEntity[ZoneMinderDataUpdateCoordinator]):
    """Base class for every ZoneMinder entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entry = entry


class ZoneMinderServerEntity(ZoneMinderEntity):
    """An entity that describes the ZoneMinder server rather than a camera."""

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
        key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_server_{key}"
        self._attr_device_info = server_device_info(
            entry, coordinator.data.server.version
        )


class ZoneMinderMonitorEntity(ZoneMinderEntity):
    """An entity bound to one ZoneMinder monitor."""

    def __init__(
        self,
        coordinator: ZoneMinderDataUpdateCoordinator,
        entry: ZoneMinderConfigEntry,
        monitor: Monitor,
        key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, entry)
        self._monitor_id = monitor.id
        self._attr_unique_id = f"{entry.entry_id}_{monitor.id}_{key}"

        web_url = _web_url(entry)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, monitor_device_id(entry, monitor.id))},
            name=monitor.name,
            manufacturer="ZoneMinder",
            model=monitor.type or "Monitor",
            configuration_url=(
                f"{web_url}/index.php?view=monitor&mid={monitor.id}"
                if web_url
                else None
            ),
        )
        if _LINK_BY_ID:
            if entry.runtime_data.server_device_id is not None:
                self._attr_device_info["via_device_id"] = (
                    entry.runtime_data.server_device_id
                )
        else:
            self._attr_device_info["via_device"] = (DOMAIN, server_device_id(entry))

    @property
    def monitor_id(self) -> int:
        """Return the ZoneMinder monitor id."""
        return self._monitor_id

    @property
    def monitor(self) -> Monitor | None:
        """Return the monitor from the latest poll."""
        return self.coordinator.data.monitors.get(self._monitor_id)

    @property
    def available(self) -> bool:
        """Return True while the monitor is present in the latest poll."""
        return self.coordinator.last_update_success and self.monitor is not None
