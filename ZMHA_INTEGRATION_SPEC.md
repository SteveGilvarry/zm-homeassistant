# ZoneMinder to Home Assistant Integration Spec (v1 Draft)

Status: Draft
Owner: TBD
Target: Home Assistant Core integration + HACS Lovelace card

## Goals
- Best-in-class UX compared to Frigate, focused on setup simplicity and event access.
- Zero YAML setup. All configuration via HA Config Flow.
- Fast live stream startup (use ZM stream by default; document optional go2rtc).
- Rich notifications (snapshot + clip + actions).
- Works with ZM 1.37 MQTT as primary event path; ZM 1.36 polling fallback.

## Non-Goals
- No new detection stack. Use ZoneMinder events directly.
- No HA MediaSource storage; use ZM storage only.
- No custom timeline panel in v1 (event list only).

## Target Platforms
- Home Assistant Core (official integration).
- HACS custom Lovelace card for montage view.

## Supported ZoneMinder Versions
- Primary: 1.37+ (MQTT event publishing).
- Fallback: 1.36+ (polling via ZM API).

## User Experience
- Config Flow discovers monitors and sets up entities automatically.
- Users see:
  - Live camera entities per monitor.
  - Event list (basic, v1).
  - Motion binary sensor updates in near-real time (MQTT).
  - Quick actions (PTZ, manual alarm).
- Optional custom montage card for a superior multi-camera view.

## Entity Model
Per ZM Monitor:
- camera.<monitor> (live stream)
- camera.<monitor>_event (event clip playback)
- binary_sensor.<monitor>_motion (active event)
- sensor.<monitor>_last_event_id
- sensor.<monitor>_last_event_time
- sensor.<monitor>_event_count_24h (optional if efficient)
- button.<monitor>_trigger_alarm
- select.<monitor>_mode (Monitor/Modect/Record/Stop)

## Services
- zoneminder.trigger_event (manual alarm trigger)
- zoneminder.ptz (pan/tilt/zoom + presets)

## Data Flow
1) ZoneMinder emits event (MQTT) -> HA updates binary_sensor and event sensors.
2) HA fetches event metadata + snapshot/clip URLs from ZM API.
3) Notifications include snapshot + link to event clip.

## Streaming
- Default: ZM stream URL (MJPEG/RTSP).
- Optional: document go2rtc relay for faster start.

## MQTT Strategy
- Auto-configure and subscribe to ZM MQTT topics if HA MQTT is configured.
- Use ZM 1.37 MQTT as the primary event transport.
- Fallback to polling when MQTT is unavailable or disabled.

### MQTT Topic Map (Draft)
Note: Final topic map must align with ZM 1.37 official MQTT format.
- Event topic: zoneminder/events/<monitor_id>
- Payload: event id, monitor id, timestamp, event type, snapshot URL

## Config Flow Fields
- ZM Base URL
- Username
- Password
- MQTT: auto-detect + enable toggle
- Polling interval (fallback)

## Notifications
- Default automation example in docs:
  - Trigger on binary_sensor motion.
  - Attach snapshot and event clip URL.
  - Action buttons: open live view, open event clip.

## v1 Roadmap
1) MVP:
   - Config Flow + monitor discovery
   - Live camera entity
   - MQTT event updates + polling fallback
   - Motion binary sensor
   - Manual alarm trigger
   - PTZ service
   - Basic event list
2) v1 Release:
   - Event clip playback
   - Notification actions
   - Diagnostics + translations
   - Test coverage: config flow, API client, MQTT handling
3) vNext:
   - Custom event timeline panel
   - Montage overlays (motion indicators, quick actions)

## HA Core Compliance Checklist
- Async I/O only.
- Config Flow + reauth.
- Device registry per monitor.
- Diagnostics support.
- strings.json and translations.
- Unit tests.
- Documentation and screenshots.
- Quality Scale target: Gold.

## References (to study)
- homeassistant/components/unifiprotect
- homeassistant/components/reolink
- homeassistant/components/axis
- homeassistant/components/synology_dsm
- custom_components/frigate
