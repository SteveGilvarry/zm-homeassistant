"""The integration in Home Assistant against a live ZoneMinder server.

Each test sets the integration up against a real server (API v2, API v3 or
both; see conftest.py for the settings) and judges the result by what Home
Assistant shows and by what the server reports through the API.

Read-only, always run when configured:

- the config flow refuses a wrong password and creates an entry with the
  right one
- every monitor has a device whose mode selects match the server, connectivity
  is known for capturing monitors, and the version sensor shows the server's
  version
- a camera image is a JPEG
- the media browser plays a recording (API v3), or lists API v2 recordings
  without offering to play them
- a user without System access can set the integration up without a reauth
  prompt, and "ZoneMinder running" isn't off just because they can't read it

With ``ZM_LIVE_WRITE=1``, each restoring what it changed (in a ``finally``):

- the analysing and recording selects change the monitor on the server
- the capturing select stops and restarts capture on the server
- the set_monitor_state action takes ZoneMinder's KeyFrames+Ondemand decoding
  and the decoding select shows it
- the trigger alarm button opens an event, the motion sensor and event entity
  follow it, and the cancel alarm button closes it
- the PTZ action and stop button are accepted on a controllable monitor
- save_run_state saves the current modes (API v3; API v2 says it can't), and
  the run state select switches the server's state; the saved state is deleted
  afterwards

Left out, because they need control of the server or cameras that a real
install can't give a test:

- Camera motion, as opposed to a forced alarm, reaching the motion sensor and
  event entity: needs a camera that can be made to see motion on demand. The
  forced alarm exercises the same sensors.
- Capture actually stopping and starting with the capturing select: needs a
  view of the server's processes. Here it is judged by the monitor's
  capturing mode on the server.
- PTZ commands arriving at the camera: needs the camera's request log. Here
  only ``stop`` is sent, so the camera doesn't move, and the check is that the
  server accepts it.
- The run state select applying different modes on API v3: the state switched
  to is one just saved from the current modes, so nothing moves. On API v2,
  where states can't be saved, it switches to another existing state and back.
- After the password changes under a running entry, the integration stops
  logging in: needs changing a user's password and counting the server's
  failed-login log entries.
- Deleted monitors leaving Home Assistant and event lists past 100 events:
  need monitors deleted and over a hundred events created.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import contextlib
import time
from typing import Any

from aiozoneminder import Monitor, RunState, ZMError
from aiozoneminder.const import V3_STATE
from homeassistant import config_entries
from homeassistant.components import camera, media_source
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PASSWORD, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zoneminder.const import DOMAIN

from .conftest import LiveServer, LiveSettings, entry_data

pytestmark = pytest.mark.timeout(300)

# Fixes in open pull requests. Until they are merged, the tests marked with
# them are expected to fail on the API named, and pass once they are.
PR_V2_PTZ = (
    "fixed by the open PR: fix-high: send API v2 PTZ through ZoneMinder's "
    "control request (aiozoneminder)"
)
PR_V3_SAVE_RUN_STATE = (
    "fixed by the open PR: fix-medium: send is_active when creating an API v3 "
    "run state (aiozoneminder)"
)
PR_V2_EVENT_END = (
    "fixed by the open PR: fix-high: read API v2 event ends from EndDateTime "
    "(aiozoneminder)"
)
PR_V2_STATUS = (
    "fixed by the open PR: fix-low: read API v2 live status and event summaries "
    "from monitors.json (aiozoneminder)"
)
PR_V2_PERMISSION = (
    "fixed by the open PR: fix-high: raise ZMApiError, not an auth error, for "
    "API v2 permission refusals (aiozoneminder)"
)
PR_DECODING = (
    "fixed by the open PR: fix-low: list ZoneMinder's KeyFrames+Ondemand "
    "decoding value (aiozoneminder), and fix-low: offer ZoneMinder's "
    "KeyFrames+Ondemand decoding value in the action"
)
PR_RUNNING_UNKNOWN = (
    "fixed by the open PR: fix-medium: report ZoneMinder's running state as "
    "unknown when it can't be read (aiozoneminder), and fix-medium: show "
    "ZoneMinder running as unknown when its status can't be read"
)
PR_MEDIA_UNPLAYABLE = (
    "fixed by the open PR: fix-medium: don't offer to play recordings the "
    "backend can't serve"
)

#: Name of the run state the save test creates and deletes again.
TEST_RUN_STATE = "ha-live-test"

MODE_FIELDS = ("capturing", "analysing", "recording", "decoding")


async def until(
    what: str,
    check: Callable[[], Any | Awaitable[Any]],
    timeout: float = 60,
    interval: float = 2,
) -> Any:
    """Wait for check() to return something truthy, and return it."""
    deadline = time.monotonic() + timeout
    while True:
        result = check()
        if asyncio.iscoroutine(result):
            result = await result
        if result:
            return result
        if time.monotonic() > deadline:
            raise AssertionError(f"no {what} within {timeout:.0f}s")
        await asyncio.sleep(interval)


def api(entry: MockConfigEntry) -> Any:
    """Return the entry's ZoneMinder client."""
    return entry.runtime_data.coordinator.api


async def refresh(entry: MockConfigEntry) -> None:
    """Fetch the server's state now rather than at the next poll."""
    await entry.runtime_data.coordinator.async_refresh()


def entity_id(
    hass: HomeAssistant, entry: MockConfigEntry, device: str, key: str, domain: str
) -> str:
    """Return the entity id for a device name and translation key."""
    entities, devices = er.async_get(hass), dr.async_get(hass)
    for ent in er.async_entries_for_config_entry(entities, entry.entry_id):
        dev = devices.async_get(ent.device_id) if ent.device_id else None
        if (
            ent.domain == domain
            and ent.translation_key == key
            and dev is not None
            and dev.name == device
        ):
            return ent.entity_id
    raise AssertionError(f"no {domain} {key!r} on {device}")


def camera_entity(hass: HomeAssistant, entry: MockConfigEntry, device: str) -> str:
    """Return the camera entity of a monitor."""
    devices = dr.async_get(hass)
    for ent in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id):
        if ent.domain == "camera" and devices.async_get(ent.device_id).name == device:
            return ent.entity_id
    raise AssertionError(f"no camera on {device}")


def state(hass: HomeAssistant, eid: str) -> str:
    """Return an entity's state."""
    st = hass.states.get(eid)
    assert st is not None, f"{eid} has no state"
    return st.state


async def candidate_monitors(entry: MockConfigEntry, settings: LiveSettings):
    """Return the monitors a test may use: ZM_LIVE_MONITOR, or all of them."""
    monitors = sorted(await api(entry).get_monitors(), key=lambda m: m.id)
    if not settings.monitor:
        return monitors
    chosen = [m for m in monitors if settings.monitor in (str(m.id), m.name)]
    if not chosen:
        pytest.fail(f"ZM_LIVE_MONITOR={settings.monitor}: no such monitor")
    return chosen


async def pick_monitor(
    entry: MockConfigEntry,
    settings: LiveSettings,
    *,
    analysing: bool = False,
    controllable: bool = False,
) -> Monitor:
    """Return a capturing monitor with what the test needs, or skip."""
    for monitor in await candidate_monitors(entry, settings):
        if not monitor.enabled:
            continue
        if analysing and not monitor.is_analysing:
            continue
        if controllable and not monitor.controllable:
            continue
        return monitor
    needs = ["capturing"]
    if analysing:
        needs.append("analysing")
    if controllable:
        needs.append("PTZ-controllable")
    pytest.skip(f"needs a {' and '.join(needs)} monitor")


async def restore_modes(entry: MockConfigEntry, before: Monitor) -> None:
    """Put a monitor's modes back to what they were."""
    now = await api(entry).get_monitor(before.id)
    changed = {
        field: getattr(before, field)
        for field in MODE_FIELDS
        if getattr(now, field) != getattr(before, field)
    }
    if changed:
        await api(entry).set_monitor_state(before.id, **changed)


async def select(hass: HomeAssistant, eid: str, option: str) -> None:
    """Choose a select's option."""
    await hass.services.async_call(
        "select", "select_option", {"entity_id": eid, "option": option}, blocking=True
    )


async def press(hass: HomeAssistant, eid: str) -> None:
    """Press a button."""
    await hass.services.async_call("button", "press", {"entity_id": eid}, blocking=True)


def reauth_flows(hass: HomeAssistant) -> list[Any]:
    """Return the reauth flows in progress."""
    return [
        flow
        for flow in hass.config_entries.flow.async_progress()
        if flow["context"].get("source") == config_entries.SOURCE_REAUTH
    ]


async def test_config_flow(
    hass: HomeAssistant, server: LiveServer, settings: LiveSettings
) -> None:
    """The config flow refuses a wrong password and accepts the right one."""
    await hass.config.async_set_time_zone(settings.timezone)
    data = entry_data(server, settings.username, settings.password)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**data, CONF_PASSWORD: settings.password + "-wrong"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"], result

    result = await hass.config_entries.flow.async_configure(result["flow_id"], data)
    assert result["type"] is FlowResultType.CREATE_ENTRY, result
    entry = result["result"]
    await hass.async_block_till_done()
    try:
        assert entry.state is ConfigEntryState.LOADED
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


@pytest.mark.live_xfail("v2", reason=PR_V2_STATUS)
async def test_entities_match_server(
    hass: HomeAssistant, server: LiveServer, entry: MockConfigEntry
) -> None:
    """Every monitor has a device whose entities agree with the server."""
    monitors = await api(entry).get_monitors()
    devices = {
        d.name
        for d in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    }
    assert {m.name for m in monitors} <= devices, f"devices: {sorted(devices)}"

    for monitor in monitors:
        for key in ("capturing", "analysing", "recording"):
            shown = state(hass, entity_id(hass, entry, monitor.name, key, "select"))
            assert shown == getattr(monitor, key), (
                f"{monitor.name} {key}: Home Assistant {shown}, "
                f"server {getattr(monitor, key)}"
            )

    version = state(
        hass, entity_id(hass, entry, entry.title, "server_version", "sensor")
    )
    server_version = await api(entry).get_version()
    assert version.startswith(server_version) or server_version.startswith(version), (
        f"version sensor {version}, server {server_version}"
    )

    # Whether a camera is connected is the server's business; that it's known is
    # the integration's.
    for monitor in monitors:
        if not monitor.enabled:
            continue
        eid = entity_id(hass, entry, monitor.name, "connectivity", "binary_sensor")
        assert state(hass, eid) not in (STATE_UNKNOWN, STATE_UNAVAILABLE), (
            f"{monitor.name}: connectivity {state(hass, eid)}"
        )


async def test_camera_image(
    hass: HomeAssistant, entry: MockConfigEntry, settings: LiveSettings
) -> None:
    """A camera's image is a JPEG."""
    monitor = await pick_monitor(entry, settings)
    eid = camera_entity(hass, entry, monitor.name)
    image = await camera.async_get_image(hass, eid)
    assert image.content[:3] == b"\xff\xd8\xff", image.content[:20]


@pytest.mark.live_xfail("v2", reason=PR_MEDIA_UNPLAYABLE)
async def test_media_browser(
    hass: HomeAssistant,
    server: LiveServer,
    entry: MockConfigEntry,
    settings: LiveSettings,
    hass_client: Any,
) -> None:
    """Recordings play through Home Assistant (API v3), or aren't offered (v2).

    API v2 doesn't serve recordings, so they may be listed but must not show a
    play button that can only fail.
    """
    assert await async_setup_component(hass, "media_source", {})
    listed: list[Any] = []
    playable: list[Any] = []
    for monitor in await candidate_monitors(entry, settings):
        days = await media_source.async_browse_media(
            hass, f"media-source://{DOMAIN}/{entry.entry_id}/{monitor.id}"
        )
        for day in (days.children or [])[:2]:
            items = await media_source.async_browse_media(hass, day.media_content_id)
            listed += items.children or []
            playable += [item for item in items.children or [] if item.can_play]
        if playable or (listed and server.name == "v2"):
            break
    if not listed:
        pytest.skip("no recordings on the server")

    if server.name == "v2":
        assert not playable, f"{len(playable)} API v2 recordings offered for play"
        return

    assert playable, f"{len(listed)} recordings listed, none playable"
    item = playable[0]
    play = await media_source.async_resolve_media(hass, item.media_content_id, None)
    client = await hass_client()
    resp = await client.get(play.url, headers={"Range": "bytes=0-1023"})
    body = await resp.read()
    assert resp.status in (200, 206), (item.title, resp.status, body[:60])
    assert body, item.title
    if play.mime_type == "video/mp4":
        assert b"ftyp" in body[:64], body[:60]


@pytest.mark.live_xfail("v2", reason=PR_V2_PERMISSION)
@pytest.mark.live_xfail("v3", reason=PR_RUNNING_UNKNOWN)
async def test_restricted_user(
    hass: HomeAssistant, server: LiveServer, settings: LiveSettings
) -> None:
    """A user without System access sets the integration up and it stays up.

    The server refuses that user its configuration, run states and status.
    That is no reason to ask for the password again, and not knowing whether
    ZoneMinder runs doesn't mean it is stopped.
    """
    if not settings.restricted_user or not settings.restricted_password:
        pytest.skip("set ZM_LIVE_RESTRICTED_USER and ZM_LIVE_RESTRICTED_PASSWORD")
    await hass.config.async_set_time_zone(settings.timezone)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        entry_data(server, settings.restricted_user, settings.restricted_password),
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY, result
    entry = result["result"]
    try:
        await hass.async_block_till_done()
        if entry.state is ConfigEntryState.LOADED:
            await refresh(entry)
            await hass.async_block_till_done()
        assert not reauth_flows(hass), f"reauth asked for (entry {entry.state})"
        assert entry.state is ConfigEntryState.LOADED, f"entry {entry.state}"
        running = hass.states.get(
            entity_id(hass, entry, entry.title, "server_running", "binary_sensor")
        )
        assert running is None or running.state != "off", (
            "ZoneMinder running shows off for a user who can't read the status"
        )
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


@pytest.mark.live_write
async def test_mode_selects(
    hass: HomeAssistant, entry: MockConfigEntry, settings: LiveSettings
) -> None:
    """The analysing and recording selects change the monitor on the server."""
    monitor = await pick_monitor(entry, settings)
    try:
        for key in ("analysing", "recording"):
            eid = entity_id(hass, entry, monitor.name, key, "select")
            options = hass.states.get(eid).attributes["options"]
            new = next(o for o in ("None", *options) if o != getattr(monitor, key))
            await select(hass, eid, new)
            assert getattr(await api(entry).get_monitor(monitor.id), key) == new
            await refresh(entry)
            assert state(hass, eid) == new

            await select(hass, eid, getattr(monitor, key))
            now = await api(entry).get_monitor(monitor.id)
            assert getattr(now, key) == getattr(monitor, key)
    finally:
        await restore_modes(entry, monitor)


@pytest.mark.live_write
async def test_capturing_select(
    hass: HomeAssistant, entry: MockConfigEntry, settings: LiveSettings
) -> None:
    """The capturing select stops capture on the server, and starts it again."""
    monitor = await pick_monitor(entry, settings)
    eid = entity_id(hass, entry, monitor.name, "capturing", "select")
    try:
        await select(hass, eid, "None")
        assert (await api(entry).get_monitor(monitor.id)).capturing == "None"
        await refresh(entry)
        assert state(hass, eid) == "None"

        await select(hass, eid, monitor.capturing)
        assert (await api(entry).get_monitor(monitor.id)).capturing == monitor.capturing
        await refresh(entry)
        assert state(hass, eid) == monitor.capturing
    finally:
        await restore_modes(entry, monitor)


@pytest.mark.live_write
@pytest.mark.live_xfail("v2", "v3", reason=PR_DECODING)
async def test_decoding_keyframes_ondemand(
    hass: HomeAssistant, entry: MockConfigEntry, settings: LiveSettings
) -> None:
    """ZoneMinder's KeyFrames+Ondemand decoding can be set and is shown."""
    monitor = await pick_monitor(entry, settings)
    # The decoding select is disabled by default.
    eid = entity_id(hass, entry, monitor.name, "decoding", "select")
    er.async_get(hass).async_update_entity(eid, disabled_by=None)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    try:
        await hass.services.async_call(
            DOMAIN,
            "set_monitor_state",
            {
                "entity_id": camera_entity(hass, entry, monitor.name),
                "decoding": "KeyFrames+Ondemand",
            },
            blocking=True,
        )
        assert (await api(entry).get_monitor(monitor.id)).decoding == (
            "KeyFrames+Ondemand"
        )
        await refresh(entry)
        assert state(hass, eid) == "KeyFrames+Ondemand"
    finally:
        await restore_modes(entry, monitor)


@pytest.mark.live_write
@pytest.mark.live_xfail("v2", reason=PR_V2_EVENT_END)
async def test_alarm_buttons_and_motion(
    hass: HomeAssistant, entry: MockConfigEntry, settings: LiveSettings
) -> None:
    """The alarm buttons open and close an event, and motion follows it.

    The trigger button opens an event the server reports as running, the
    motion sensor turns on and the event entity fires. The cancel button
    closes the event and the motion sensor turns off again.
    """
    monitor = await pick_monitor(entry, settings, analysing=True)
    client = api(entry)
    motion = entity_id(hass, entry, monitor.name, "motion", "binary_sensor")
    event_entity = entity_id(hass, entry, monitor.name, "event", "event")

    # A forced alarm while an earlier event is still closing joins that event.
    async def quiet() -> bool:
        events = await client.get_events(monitor.id, limit=5)
        return not any(e.in_progress for e in events)

    await until("the monitor's running event to close", quiet, 120)
    await until(
        "motion sensor off before the alarm",
        lambda: state(hass, motion) == "off",
        60,
        1,
    )
    await asyncio.sleep(5)  # past ZoneMinder's post-event frames

    event_before = state(hass, event_entity)
    newest = max(
        (e.id for e in await client.get_events(monitor.id, limit=5)), default=0
    )

    await press(hass, entity_id(hass, entry, monitor.name, "trigger_alarm", "button"))
    try:
        events = await until(
            "event from the trigger alarm button",
            lambda: _newer_events(client, monitor.id, newest),
            30,
        )
        alarm = events[-1]
        assert alarm.in_progress, f"alarm event {alarm.id} already reads as ended"
        await until(
            "motion sensor on during the alarm",
            lambda: state(hass, motion) == "on",
            45,
            1,
        )
        await until(
            "event entity firing for the alarm",
            lambda: state(hass, event_entity) != event_before,
            30,
            1,
        )
        await press(
            hass, entity_id(hass, entry, monitor.name, "cancel_alarm", "button")
        )
    finally:
        # Never leave a forced alarm running, whatever failed above.
        with contextlib.suppress(ZMError):
            await client.cancel_alarm(monitor.id)

    async def closed() -> bool:
        return not (await client.get_event(alarm.id)).in_progress

    await until(f"alarm event {alarm.id} closing after cancel", closed, 60)
    await until("motion sensor off", lambda: state(hass, motion) == "off", 60, 1)


async def _newer_events(client: Any, monitor_id: int, newest: int) -> list[Any]:
    events = await client.get_events(monitor_id, limit=5)
    return sorted((e for e in events if e.id > newest), key=lambda e: e.id)


@pytest.mark.live_write
@pytest.mark.live_xfail("v2", reason=PR_V2_PTZ)
async def test_ptz(
    hass: HomeAssistant, entry: MockConfigEntry, settings: LiveSettings
) -> None:
    """The PTZ action and stop button are accepted on a controllable monitor."""
    monitor = await pick_monitor(entry, settings, controllable=True)
    await hass.services.async_call(
        DOMAIN,
        "ptz",
        {"entity_id": camera_entity(hass, entry, monitor.name), "command": "stop"},
        blocking=True,
    )
    await press(hass, entity_id(hass, entry, monitor.name, "ptz_stop", "button"))


@pytest.mark.live_write
@pytest.mark.live_xfail("v3", reason=PR_V3_SAVE_RUN_STATE)
async def test_run_states(
    hass: HomeAssistant,
    server: LiveServer,
    entry: MockConfigEntry,
    settings: LiveSettings,
) -> None:
    """save_run_state saves the current modes and the run state select applies one.

    API v3 saves a state from the current modes, and the select switches to it.
    API v2 can't save states; there the select switches to another existing
    state. Either way the previous state and every monitor's modes are put
    back, and the saved state is deleted.
    """
    client = api(entry)
    monitors_before = await client.get_monitors()
    active_before = next((s for s in await client.get_run_states() if s.active), None)
    definition = ",".join(
        f"{m.id}:{m.capturing}:{m.analysing}:{m.recording}"
        for m in sorted(monitors_before, key=lambda m: m.id)
    )
    try:
        if server.name == "v2":
            with pytest.raises(ServiceValidationError) as err:
                await hass.services.async_call(
                    DOMAIN, "save_run_state", {"name": TEST_RUN_STATE}, blocking=True
                )
            assert err.value.translation_key == "run_states_need_v3"
        else:
            await hass.services.async_call(
                DOMAIN, "save_run_state", {"name": TEST_RUN_STATE}, blocking=True
            )
            # A second run state adds the select, which reloads the entry.
            await hass.async_block_till_done()
            saved = {s.name: s for s in await api(entry).get_run_states()}
            assert TEST_RUN_STATE in saved, sorted(saved)
            assert saved[TEST_RUN_STATE].definition == definition

        states = await api(entry).get_run_states()
        target = next((s for s in states if s.name == TEST_RUN_STATE), None) or next(
            (s for s in states if not s.active), None
        )
        if target is None or len(states) < 2:
            pytest.skip("the run state select needs two run states on the server")

        await refresh(entry)
        await hass.async_block_till_done()
        sel = entity_id(hass, entry, entry.title, "run_state", "select")
        assert target.name in hass.states.get(sel).attributes["options"]
        await select(hass, sel, target.name)

        async def applied() -> bool:
            states = await api(entry).get_run_states()
            return [s.name for s in states if s.active] == [target.name]

        await until(f"run state {target.name} active on the server", applied, 90)
        modes = target.monitor_modes()

        async def monitors_follow() -> bool:
            return all(
                modes.get(m.id, (m.capturing, m.analysing, m.recording))
                == (m.capturing, m.analysing, m.recording)
                for m in await api(entry).get_monitors()
            )

        await until(f"monitors taking {target.name}'s modes", monitors_follow, 90)
        await refresh(entry)
        assert state(hass, sel) == target.name
    finally:
        await _restore_run_state(server, entry, active_before, monitors_before)


async def _restore_run_state(
    server: LiveServer,
    entry: MockConfigEntry,
    active_before: RunState | None,
    monitors_before: list[Monitor],
) -> None:
    client = api(entry)
    if active_before is not None and not any(
        s.active and s.name == active_before.name for s in await client.get_run_states()
    ):
        await client.set_run_state(active_before)
    for monitor in monitors_before:
        await restore_modes(entry, monitor)
    if server.name != "v3":
        return
    for run_state in await client.get_run_states():
        if run_state.name == TEST_RUN_STATE:
            # aiozoneminder has no call for deleting a run state.
            await client._request("DELETE", V3_STATE.format(state_id=run_state.id))
