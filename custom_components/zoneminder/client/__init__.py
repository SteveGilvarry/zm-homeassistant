# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pluggable ZoneMinder backend clients.

The integration can talk to two different ZoneMinder API surfaces:

* :class:`~.legacy.ZoneMinderLegacyClient` - ZoneMinder's built-in CakePHP API.
* :class:`~.v3.ZoneMinderV3Client` - the standalone ``zm-api`` Rust REST server.

Both implement the common :class:`~.base.ZoneMinderClient` contract so the rest
of the integration never needs to know which backend is in use.
"""

from .base import ZoneMinderClient
from .legacy import ZoneMinderLegacyClient
from .v3 import ZoneMinderV3Client

__all__ = [
    "ZoneMinderClient",
    "ZoneMinderLegacyClient",
    "ZoneMinderV3Client",
]
