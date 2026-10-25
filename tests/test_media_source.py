"""Tests for browsing ZoneMinder recordings."""

from __future__ import annotations

from unittest.mock import patch

from aioresponses import aioresponses
from homeassistant.components import media_source
from homeassistant.components.media_source import Unresolvable
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import event  # noqa: F401,


@pytest.fixture(autouse=True)
async def media_source_component(hass: HomeAssistant) -> None:
    """Load the media_source integration."""
    assert await async_setup_component(hass, "media_source", {})


async def test_browse_lists_servers_then_monitors(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The tree starts at the server and opens into its cameras."""
    root = await media_source.async_browse_media(hass, "media-source://zoneminder")
    assert [child.title for child in root.children] == ["ZoneMinder (test)"]

    monitors = await media_source.async_browse_media(
        hass, f"media-source://zoneminder/{setup_integration.entry_id}"
    )
    assert [child.title for child in monitors.children] == [
        "Driveway",
        "Back door",
        "Gate",
    ]
    assert all(child.can_expand for child in monitors.children)


async def test_browse_groups_recordings_by_day(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """A camera opens into the days it has recordings for."""
    days = await media_source.async_browse_media(
        hass, f"media-source://zoneminder/{setup_integration.entry_id}/1"
    )
    assert days.children
    # The fixture events are all on the same day, and it is counted.
    assert "(2)" in days.children[0].title


async def test_browse_lists_playable_recordings(
    hass: HomeAssistant, setup_integration: MockConfigEntry, zm_api: aioresponses
) -> None:
    """Finished recordings are playable and carry a thumbnail."""
    entry_id = setup_integration.entry_id
    listing = await media_source.async_browse_media(
        hass, f"media-source://zoneminder/{entry_id}/1/2026-08-22"
    )

    # Event 300 is still being written, so only 299 can be played.
    assert [child.title.split(" - ")[1] for child in listing.children] == ["Continuous"]
    child = listing.children[0]
    assert child.can_play is True
    assert child.thumbnail.startswith(f"/api/zoneminder/{entry_id}/")
    assert "api/v3/events/299/thumbnail" in child.thumbnail


async def test_recordings_without_a_media_path_are_not_playable(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """API v2 cannot serve recordings, so they are listed but not playable.

    Offering play only to fail with "This backend cannot serve recordings"
    looked like a broken recording.
    """
    entry_id = setup_integration.entry_id
    with patch(
        "aiozoneminder.client.v3.ZoneMinderV3Client.get_event_media_path",
        return_value=None,
    ):
        listing = await media_source.async_browse_media(
            hass, f"media-source://zoneminder/{entry_id}/1/2026-08-22"
        )

    assert listing.children
    assert not any(child.can_play for child in listing.children)


async def test_resolve_returns_a_proxied_url(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Playing a recording hands the browser a proxy URL, not a raw token."""
    entry_id = setup_integration.entry_id
    resolved = await media_source.async_resolve_media(
        hass, f"media-source://zoneminder/{entry_id}/1/2026-08-22/299", None
    )

    assert resolved.mime_type == "video/mp4"
    assert resolved.url.startswith(f"/api/zoneminder/{entry_id}/")
    assert resolved.url.endswith("api/v3/events/299/video")
    assert "token" not in resolved.url


async def test_resolve_rejects_a_bad_identifier(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """A malformed identifier fails cleanly."""
    with pytest.raises(Unresolvable):
        await media_source.async_resolve_media(
            hass, "media-source://zoneminder/nonsense", None
        )


async def test_browse_uses_the_date_range_filter(
    hass: HomeAssistant, setup_integration: MockConfigEntry, zm_api: aioresponses
) -> None:
    """Listing one day asks the server for that day, not for everything."""
    entry_id = setup_integration.entry_id

    listing = await media_source.async_browse_media(
        hass, f"media-source://zoneminder/{entry_id}/1/2026-08-21"
    )
    assert listing.children == []

    requested = [
        str(url)
        for (_method, url), _calls in zm_api.requests.items()
        if "start_time=" in str(url)
    ]
    assert any("2026-08-21" in url and "monitor_id=1" in url for url in requested)
