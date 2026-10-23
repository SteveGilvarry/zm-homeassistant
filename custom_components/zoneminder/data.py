# SPDX-License-Identifier: AGPL-3.0-or-later
"""Runtime data attached to a ZoneMinder config entry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .coordinator import ZoneMinderDataUpdateCoordinator
    from .mqtt import ZoneMinderMQTTListener


@dataclass
class ZoneMinderRuntimeData:
    """Everything a set-up ZoneMinder entry keeps in memory."""

    coordinator: ZoneMinderDataUpdateCoordinator
    proxy_secret: str
    mqtt_listener: ZoneMinderMQTTListener | None = None
    ptz_presets: dict[int, dict[int, str]] = field(default_factory=dict)


#: A config entry that has finished setting up carries its runtime data.
type ZoneMinderConfigEntry = ConfigEntry[ZoneMinderRuntimeData]
