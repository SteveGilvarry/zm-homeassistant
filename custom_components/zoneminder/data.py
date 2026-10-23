# SPDX-License-Identifier: AGPL-3.0-or-later
"""Runtime data attached to a ZoneMinder config entry."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .coordinator import ZoneMinderDataUpdateCoordinator
    from .event_watcher import ZoneMinderEventWatcher
    from .mqtt import ZoneMinderMQTTListener
    from .webrtc import ZoneMinderWebRTCProvider


@dataclass
class ZoneMinderRuntimeData:
    """Everything a set-up ZoneMinder entry keeps in memory."""

    coordinator: ZoneMinderDataUpdateCoordinator
    proxy_secret: str
    mqtt_listener: ZoneMinderMQTTListener | None = None
    event_watcher: ZoneMinderEventWatcher | None = None
    #: Set on API v3 servers; cameras use it once WHEP is confirmed.
    webrtc_provider: ZoneMinderWebRTCProvider | None = None
    #: (event id, "start" | "end") already handed to entities, newest last.
    published: OrderedDict[tuple[int, str], None] = field(default_factory=OrderedDict)
    ptz_presets: dict[int, dict[int, str]] = field(default_factory=dict)
    #: Device registry id of the server device the cameras hang off.
    server_device_id: str | None = None


#: A config entry that has finished setting up carries its runtime data.
type ZoneMinderConfigEntry = ConfigEntry[ZoneMinderRuntimeData]
