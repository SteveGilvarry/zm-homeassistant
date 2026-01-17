# ZoneMinder Home Assistant Integration - Implementation Plan

## Overview

Build a Gold-tier Home Assistant Core integration for ZoneMinder with zero-YAML configuration, MQTT support, and best-in-class UX. This is a greenfield project starting from the ZMHA_INTEGRATION_SPEC.md specification.

**Project Context:**
- **Testing Environment**: ZoneMinder 1.37+ with MQTT support available
- **Target**: Official Home Assistant Core submission (Gold tier quality)
- **MVP Priorities**: Live streaming, event playback, MQTT real-time updates
- **Scope**: Core integration + custom Lovelace montage card

## Project Structure

```
custom_components/zoneminder/
├── __init__.py              # Integration setup & coordinator
├── manifest.json            # Integration metadata
├── config_flow.py          # Config/options/reauth flows
├── const.py                # Constants & enums
├── api.py                  # ZoneMinder API client
├── mqtt.py                 # MQTT event handler
├── coordinator.py          # DataUpdateCoordinator (polling)
├── models.py               # Data models (Monitor, Event)
├── exceptions.py           # Custom exceptions
├── diagnostics.py          # Diagnostics support
├── services.yaml           # Service definitions
├── strings.json            # Translations
├── camera.py               # Camera entities (live + event)
├── binary_sensor.py        # Motion detection sensors
├── sensor.py               # Event tracking sensors
├── button.py               # Alarm trigger buttons
└── select.py               # Monitor mode selectors
```

## Implementation Phases

### Phase 1: Foundation (MVP Core) - PRIORITY

**Critical Files:**
- [manifest.json](custom_components/zoneminder/manifest.json)
- [const.py](custom_components/zoneminder/const.py)
- [models.py](custom_components/zoneminder/models.py)
- [exceptions.py](custom_components/zoneminder/exceptions.py)
- [api.py](custom_components/zoneminder/api.py)

**Tasks:**
1. Create project directory structure
2. Implement ZoneMinder API client with:
   - Async authentication (token-based)
   - Monitor listing and retrieval
   - Event listing and retrieval
   - Stream URL generation (focus on ZM 1.37+ MQTT mode)
   - Event clip URL generation (MVP priority)
   - Error handling (auth, connection, API errors)
3. Define data models for Monitor and Event
4. Create custom exceptions for error flow

**API Client Key Methods:**
- `authenticate()` - Login and store auth token
- `get_version()` - Check ZM version (ensure 1.37+)
- `get_monitors()` - Fetch all monitors
- `get_events(monitor_id)` - Fetch events for monitor
- `get_stream_url(monitor_id)` - Generate live stream URL (MVP)
- `get_event_clip_url(event_id)` - Generate event video URL (MVP)
- `trigger_alarm(monitor_id, cause)` - Manual alarm trigger
- `set_monitor_function(monitor_id, function)` - Change mode
- `ptz_move(monitor_id, control)` - PTZ control (post-MVP)

**Testing Focus:**
- Test against real ZM 1.37+ instance
- Verify MQTT topic structure
- Validate stream URLs work in HA

**Deliverable:** Functional API client tested against ZM 1.37+ with MQTT support

### Phase 2: Config Flow

**Critical Files:**
- [config_flow.py](custom_components/zoneminder/config_flow.py)
- [strings.json](custom_components/zoneminder/strings.json)
- [translations/en.json](custom_components/zoneminder/translations/en.json)

**Tasks:**
1. Implement user config flow:
   - Fields: ZM Base URL, Username, Password, MQTT Enable toggle
   - Validation: Test connection, fetch monitors
   - Unique ID: Based on ZM host
2. Implement reauth flow for expired credentials
3. Implement options flow for MQTT settings
4. Add comprehensive error handling and user messages

**Config Flow Steps:**
- User → Validate credentials → Create entry
- Reauth → Update credentials → Reload entry
- Options → Update MQTT settings → Reload entry

**Deliverable:** Integration can be added via HA UI with proper validation and error messages

### Phase 3: Coordinator & Live Cameras

**Critical Files:**
- [coordinator.py](custom_components/zoneminder/coordinator.py)
- [camera.py](custom_components/zoneminder/camera.py)
- [__init__.py](custom_components/zoneminder/__init__.py)

**Tasks:**
1. Implement DataUpdateCoordinator for polling:
   - Fetch monitors and latest events
   - 30-second default interval (configurable)
   - Handle auth failures → trigger reauth
2. Create camera entities:
   - Live camera per monitor (`camera.<monitor>`)
   - Implement `stream_source()` for MJPEG/RTSP
   - Implement `async_camera_image()` for snapshots
3. Setup device registry entries per monitor
4. Implement `async_setup_entry()` in __init__.py:
   - Initialize API client
   - Setup coordinator
   - Forward to camera platform
   - Register devices

**Entity Properties:**
- Unique ID: `{monitor_id}_live`
- Device info: Monitor name, type, configuration URL
- Supported features: STREAM

**Deliverable:** Live camera feeds visible in Home Assistant

### Phase 4: MQTT Integration - PRIORITY

**Critical Files:**
- [mqtt.py](custom_components/zoneminder/mqtt.py)
- Update [__init__.py](custom_components/zoneminder/__init__.py)

**Tasks:**
1. Document ZM 1.37 MQTT topic structure (test against your instance):
   - Primary topic: `zoneminder/events/<monitor_id>`
   - Expected payload: event_id, monitor_id, timestamp, cause, state
   - Test subscription and message receipt
2. Implement MQTT listener:
   - Auto-detect HA MQTT integration
   - Subscribe to ZM event topics (all monitors: `zoneminder/events/+`)
   - Parse event messages (handle start/end states)
   - Update coordinator data immediately for real-time response
3. Implement MQTT-first strategy:
   - MQTT is PRIMARY path (no fallback needed for ZM 1.37+)
   - Polling used only for initial data fetch and health checks (5min)
   - No need for aggressive polling with MQTT
4. Add MQTT configuration validation in config flow

**MQTT Message Flow (Real-Time):**
1. ZM detects event → Publishes to MQTT immediately
2. HA receives message (<1 second) → Parse event data
3. Fetch event details via API (snapshot URL, clip URL)
4. Update coordinator data → Trigger entity callbacks
5. Binary sensor updates instantly, notification fires

**Testing with Real ZM 1.37+:**
- Subscribe to topics manually to verify format
- Trigger test events and measure latency
- Verify event start/end messages
- Test with multiple monitors simultaneously

**Deliverable:** Sub-second event notifications via MQTT, validated against real ZM 1.37+ instance

### Phase 5: Sensors & Motion Detection

**Critical Files:**
- [binary_sensor.py](custom_components/zoneminder/binary_sensor.py)
- [sensor.py](custom_components/zoneminder/sensor.py)

**Tasks:**
1. Implement motion binary sensor:
   - Device class: MOTION
   - State: ON when event active (no end_time), OFF otherwise
   - Attributes: event_id, cause, start_time
2. Implement event sensors:
   - Last event ID sensor
   - Last event time sensor (timestamp device class)
   - Optional: 24h event count sensor
3. Forward platforms in __init__.py

**Entity Unique IDs:**
- Motion: `{monitor_id}_motion`
- Last event ID: `{monitor_id}_last_event_id`
- Last event time: `{monitor_id}_last_event_time`

**Deliverable:** Motion detection and event tracking working in HA

### Phase 6: Controls & Services

**Critical Files:**
- [button.py](custom_components/zoneminder/button.py)
- [select.py](custom_components/zoneminder/select.py)
- [services.yaml](custom_components/zoneminder/services.yaml)
- Update [__init__.py](custom_components/zoneminder/__init__.py)

**Tasks:**
1. Implement alarm trigger button:
   - Calls `api.trigger_alarm()` on press
   - Unique ID: `{monitor_id}_trigger_alarm`
2. Implement monitor function select:
   - Options: None, Monitor, Modect, Record, Mocord, Nodect
   - Current option from monitor state
   - Calls `api.set_monitor_function()` on change
3. Register services:
   - `zoneminder.trigger_event` - Target device, optional cause
   - `zoneminder.ptz` - Target device, control command, preset
4. Service handlers in __init__.py:
   - Extract monitor_id from device_id
   - Call appropriate API method
   - Handle errors gracefully

**Service Schemas:**
- trigger_event: device target, optional cause (string)
- ptz: device target, control (select), optional preset (number)

**Deliverable:** Manual controls and services functional

### Phase 7: Event Playback - PRIORITY (MVP)

**Critical Files:**
- Update [camera.py](custom_components/zoneminder/camera.py)
- Update [api.py](custom_components/zoneminder/api.py)

**Tasks:**
1. Add event camera entities:
   - One per monitor: `camera.<monitor>_event`
   - Unique ID: `{monitor_id}_event`
   - Shows most recent completed event clip
2. Implement `stream_source()` for event clips:
   - Return latest event clip URL (MP4 format preferred)
   - Use API method `get_event_clip_url(event_id)`
   - Handle both in-progress and completed events
3. Add event metadata to camera attributes:
   - Event ID, cause, duration, frame count, start/end times
   - Snapshot URL for notifications
4. Test event playback thoroughly:
   - HA media player
   - Mobile app notifications with clips
   - Different video formats (MP4, AVI)

**Event Camera Logic:**
- If latest_event exists and completed → Return clip URL
- If event in progress → Return partial clip or live stream
- If no event → Return None
- Update immediately when MQTT event ends

**Integration with Notifications:**
- Event camera provides clip for rich notifications
- Snapshot available from event data
- Actions: "View Live" (live camera) and "View Event" (event camera)

**Testing with Real ZM:**
- Trigger multiple events
- Verify clip URLs are correct
- Test different event durations
- Check clip format compatibility with HA

**Deliverable:** Event clips viewable in HA with rich notification support

### Phase 8: Polish & Diagnostics

**Critical Files:**
- [diagnostics.py](custom_components/zoneminder/diagnostics.py)
- Update all files with logging and type hints

**Tasks:**
1. Implement diagnostics platform:
   - ZM version and configuration
   - Monitor list with status
   - MQTT status (enabled/disabled)
   - Recent events summary
   - Redact sensitive data (passwords, tokens)
2. Add comprehensive logging:
   - DEBUG: API calls, data updates
   - INFO: Setup, major events
   - WARNING: Fallback modes, degraded functionality
   - ERROR: Failures, exceptions
3. Complete translation strings
4. Add type hints throughout (mypy compliance)
5. Code formatting (Ruff/Black)

**Diagnostics Data Structure:**
```python
{
    "zoneminder": {
        "version": "1.37.0",
        "mqtt_enabled": true,
        "monitors_count": 3,
        "monitors": [...],  # Sanitized monitor data
        "recent_events": [...],  # Last 10 events
    }
}
```

**Deliverable:** Professional-grade code with diagnostics support

### Phase 9: Testing & Documentation

**Critical Files:**
- Create `tests/` directory with full test suite
- Create [README.md](README.md)
- Create [CHANGELOG.md](CHANGELOG.md)

**Tasks:**
1. Write comprehensive tests:
   - test_config_flow.py - All flows and error cases
   - test_api.py - API client methods with mocks
   - test_coordinator.py - Polling and updates
   - test_camera.py - Camera entities
   - test_binary_sensor.py - Motion detection
   - test_sensor.py - Event sensors
   - test_button.py - Alarm triggers
   - test_select.py - Function selection
   - test_services.py - Service calls
2. Achieve >90% test coverage
3. Write comprehensive README:
   - Installation instructions (HACS)
   - Configuration guide
   - Feature overview with screenshots
   - Troubleshooting section
4. Document example automations:
   - Motion detection notifications
   - Event clip attachments
   - Multi-monitor alerts
5. Test with real ZM 1.36 and 1.37 instances

**Example Automation (for docs):**
```yaml
automation:
  - alias: "Front Door Motion Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door_motion
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Motion Detected"
          message: "Front door activity"
          data:
            image: "/api/camera_proxy/camera.front_door"
            actions:
              - action: "VIEW_LIVE"
                title: "View Live"
              - action: "VIEW_EVENT"
                title: "View Event"
```

**Deliverable:** Production-ready integration with comprehensive tests and documentation

### Phase 10: Lovelace Montage Card - INCLUDED

**Critical Files (new repo: zoneminder-card):**
- Create separate `zoneminder-card` repository for HACS
- [src/zoneminder-card.ts](../zoneminder-card/src/zoneminder-card.ts) - Main card component
- [src/editor.ts](../zoneminder-card/src/editor.ts) - Visual configuration editor
- [src/montage-view.ts](../zoneminder-card/src/montage-view.ts) - Grid layout
- [src/types.ts](../zoneminder-card/src/types.ts) - TypeScript interfaces
- [hacs.json](../zoneminder-card/hacs.json) - HACS metadata
- [package.json](../zoneminder-card/package.json) - Dependencies & build
- [README.md](../zoneminder-card/README.md) - Installation & usage

**Tasks:**
1. Setup TypeScript + Lit + Rollup project:
   - Use Lit for web components (HA standard)
   - Rollup for bundling
   - TypeScript for type safety
2. Create multi-camera montage card:
   - Responsive grid layout (1-4 columns, auto-adjust)
   - Live stream display per monitor
   - Real-time motion indicators (pulse on motion)
   - Event count badges
   - Click to view full camera or event clips
3. Add quick action controls:
   - Trigger alarm button per camera
   - Function mode selector (Monitor/Modect/Record)
   - PTZ controls for supported cameras
   - Fullscreen toggle
4. Implement visual editor:
   - Drag-and-drop camera selection
   - Column count selector
   - Toggle options (motion indicators, controls, timestamps)
   - Preview changes live
5. Add advanced features:
   - Event timeline overlay (show recent events)
   - Click event thumbnail to play clip
   - Auto-refresh on motion detection
   - Dark/light theme support
6. HACS integration:
   - Proper hacs.json configuration
   - Version tagging for releases
   - Installation documentation
7. Test thoroughly:
   - Desktop browsers (Chrome, Firefox, Safari)
   - Mobile browsers (iOS, Android)
   - HA mobile app
   - Performance with 8+ cameras

**Card Configuration Example:**
```yaml
type: custom:zoneminder-card
title: Security Cameras
monitors:
  - camera.front_door
  - camera.backyard
  - camera.garage
  - camera.driveway
columns: 2
aspect_ratio: "16:9"
show_motion_indicator: true
show_event_count: true
show_controls: true
show_timeline: false  # v2 feature
refresh_interval: 1000  # ms, for motion indicator updates
click_action: fullscreen  # or 'events'
```

**Visual Features:**
- Motion indicator: Pulsing red border when binary_sensor active
- Event badge: "3 events (24h)" in corner
- Status overlay: Recording indicator, connection status
- Smooth transitions and animations

**Development Tools:**
```bash
npm install
npm run dev      # Watch mode with live reload
npm run build    # Production build
npm run lint     # ESLint + Prettier
```

**Integration with ZMHA:**
- Card reads entities from zoneminder integration
- Subscribes to state changes for real-time updates
- Calls services for quick actions
- Links to camera entities for fullscreen

**Testing Checklist:**
- [ ] Grid layout responsive (1-4 cols)
- [ ] Live streams load and display
- [ ] Motion indicators update in real-time
- [ ] Event counts accurate
- [ ] Click actions work (fullscreen, events)
- [ ] Quick actions call correct services
- [ ] Visual editor saves config correctly
- [ ] Performance good with 8+ cameras
- [ ] Mobile-friendly interface
- [ ] Dark/light themes

**Deliverable:** Professional-grade custom Lovelace card with montage view, motion indicators, and quick actions, available via HACS

## Critical Implementation Details

### API Client Architecture

**Authentication Flow:**
1. POST `/zm/api/host/login.json` with credentials
2. Receive auth token in response
3. Include token in subsequent requests (query param or cookie)
4. Handle 401 responses → Trigger reauth flow

**Stream URL Format:**
- Live MJPEG: `/zm/cgi-bin/nph-zms?mode=jpeg&monitor={id}&auth={token}`
- Live RTSP: `rtsp://{user}:{pass}@{host}/zm/monitor{id}`
- Event clip: `/zm/api/events/{event_id}.mp4?auth={token}`

### MQTT Topic Structure (ZM 1.37)

Based on ZoneMinder documentation:
- Events: `zoneminder/events/{monitor_id}`
- Monitor status: `zoneminder/monitors/{monitor_id}/status`

**Event Payload Example:**
```json
{
  "event_id": 12345,
  "monitor_id": 1,
  "cause": "Motion",
  "timestamp": "2025-01-17T10:30:00Z",
  "notes": "Detection zone: Front porch"
}
```

### Device Registry Structure

Each monitor becomes a device:
```python
DeviceInfo(
    identifiers={(DOMAIN, str(monitor.id))},
    name=monitor.name,
    manufacturer="ZoneMinder",
    model=monitor.type,  # Local, Remote, Ffmpeg, etc.
    configuration_url=f"{host}/zm/index.php?view=monitor&mid={monitor.id}",
)
```

All entities for that monitor link to this device via `device_info`.

### Error Handling Strategy

**Exception Hierarchy:**
```
ZoneMinerError (base)
├── ZMConnectionError - Network issues
├── ZMAuthenticationError - Invalid credentials → Reauth flow
└── ZMApiError - API errors (4xx, 5xx)
```

**Usage:**
- API client raises specific exceptions
- Config flow catches and displays user-friendly errors
- Coordinator catches and raises ConfigEntryAuthFailed or UpdateFailed
- Services catch and log errors

### Performance Considerations

1. **Session Reuse**: Single aiohttp session for all API calls
2. **Parallel Fetching**: Use `asyncio.gather()` for multiple monitors
3. **MQTT Priority**: Reduce polling frequency when MQTT active
4. **Stream Caching**: Cache stream URLs for 5 minutes
5. **Selective Updates**: Only update changed data in coordinator

## Verification & Testing

### End-to-End Testing Checklist

**Setup:**
- [ ] Integration appears in HA integrations list
- [ ] Config flow accepts valid credentials
- [ ] Config flow rejects invalid credentials with clear error
- [ ] Monitors discovered and devices created
- [ ] Entities created per monitor

**Functionality:**
- [ ] Live camera streams display in HA
- [ ] Motion binary sensor updates on events
- [ ] Event sensors show latest event data
- [ ] Alarm button triggers ZM alarm
- [ ] Function select changes monitor mode
- [ ] Services work with device targeting
- [ ] PTZ controls operate camera

**MQTT Mode:**
- [ ] MQTT auto-detected when available
- [ ] Events received in <5 seconds
- [ ] Binary sensor updates immediately
- [ ] Fallback to polling when MQTT disabled

**Polling Mode:**
- [ ] Updates every 30 seconds
- [ ] No errors when MQTT unavailable
- [ ] Data consistent with MQTT mode

**Error Handling:**
- [ ] Invalid credentials trigger reauth
- [ ] Network errors show appropriate messages
- [ ] Diagnostics available and useful
- [ ] Logs provide debugging information

**Performance:**
- [ ] Stream startup <3 seconds
- [ ] No blocking I/O in main thread
- [ ] CPU usage acceptable with 10+ monitors
- [ ] Memory stable over 24h operation

### Test Coverage Requirements

Minimum 90% coverage for Gold tier:
- Config flow: 100% (all paths, all errors)
- API client: 95% (mock all HTTP calls)
- Coordinator: 90% (polling and updates)
- Platforms: 85% (entity properties and actions)
- Services: 95% (all service calls and validations)

## Documentation Requirements

### README.md Structure

1. **Introduction**: What is ZMHA, key features
2. **Installation**: HACS instructions, manual install
3. **Configuration**: Adding integration via UI
4. **Features**: List all entities and services
5. **MQTT Setup**: ZM 1.37 MQTT configuration
6. **Automation Examples**: Common use cases
7. **Troubleshooting**: Common issues and solutions
8. **Development**: Contributing, testing locally

### Example Automations to Document

1. **Motion Notification with Snapshot**
2. **Event Recording to Cloud Storage**
3. **Multi-Camera Alarm Mode Toggle**
4. **PTZ Preset on Motion Detection**
5. **Event Clip Notification to Mobile App**

## HA Core Submission Checklist

Before submitting PR to home-assistant/core:

**Code Quality:**
- [ ] All code fully async (no blocking I/O)
- [ ] Type hints throughout (mypy --strict passes)
- [ ] Formatted with Black and Ruff
- [ ] No violations of HA code standards
- [ ] Proper error handling everywhere

**Integration Features:**
- [ ] Config flow with reauth
- [ ] Options flow for settings
- [ ] Device registry per monitor
- [ ] Diagnostics platform
- [ ] Services with proper schemas
- [ ] Translations complete

**Testing:**
- [ ] Unit tests >90% coverage
- [ ] All tests pass
- [ ] Test fixtures for API responses
- [ ] No external dependencies in tests

**Documentation:**
- [ ] strings.json complete
- [ ] services.yaml accurate
- [ ] Code comments for complex logic
- [ ] README with setup instructions

**Quality Scale:**
- [ ] Gold tier requirements met
- [ ] Integration checklist completed
- [ ] Brand guidelines followed
- [ ] No rate limiting issues

## Reference Integrations

Study these HA Core integrations for best practices:

1. **Reolink** ([code](https://github.com/home-assistant/core/tree/dev/homeassistant/components/reolink))
   - Camera platform patterns
   - Config flow structure
   - Device registry usage

2. **UniFi Protect** ([code](https://github.com/home-assistant/core/tree/dev/homeassistant/components/unifiprotect))
   - Event handling
   - Binary sensor motion detection
   - Rich entity model

3. **Axis** ([code](https://github.com/home-assistant/core/tree/dev/homeassistant/components/axis))
   - MQTT integration
   - PTZ controls
   - Stream handling

4. **Synology DSM** ([code](https://github.com/home-assistant/core/tree/dev/homeassistant/components/synology_dsm))
   - API client design
   - Coordinator pattern
   - Diagnostics implementation

5. **Frigate** (custom component)
   - Event notifications
   - Clip playback
   - Custom card integration

## Timeline Estimate

**Total: 12-14 weeks for full v1 release + Lovelace card**

**Core Integration (10 weeks):**
- Phase 1: Foundation - 2 weeks (API client + ZM 1.37 testing)
- Phase 2: Config Flow - 1 week
- Phase 3: Cameras (Live) - 1 week
- Phase 4: MQTT Integration - 1.5 weeks (priority feature, thorough testing)
- Phase 5: Sensors - 1 week
- Phase 6: Controls - 1 week
- Phase 7: Event Playback - 1.5 weeks (MVP priority feature)
- Phase 8: Polish - 1 week
- Phase 9: Testing & Docs - 2 weeks

**Lovelace Card (3-4 weeks, can overlap with Phase 8-9):**
- Phase 10: Montage Card - 3-4 weeks (TypeScript + Lit + advanced features)

**Critical Path:**
- MVP (Phases 1-4, 7): 7 weeks - Live streaming, MQTT events, event playback
- Full Integration (Phases 1-9): 10 weeks - Production-ready for HA Core
- Complete Project (Phases 1-10): 12-14 weeks - Integration + Custom Card

## Success Criteria

**MVP Success (Phases 1-4, 7) - 7 weeks:**
- Integration installable via HA UI
- Live cameras working with fast stream startup
- MQTT event detection with <1 second latency (tested on real ZM 1.37+)
- Event clips playable in HA
- Motion binary sensors updating in real-time
- Rich notifications with snapshots and event clips
- Basic documentation and example automations

**v1 Release Success (Phases 1-9) - 10 weeks:**
- All entities implemented (cameras, sensors, buttons, selects)
- MQTT real-time updates fully validated on ZM 1.37+
- Event playback with multiple format support
- Full control suite (alarm triggers, mode switching, PTZ)
- >90% test coverage
- Comprehensive documentation with screenshots
- Diagnostics platform functional
- Gold tier quality standards met
- Ready for HA Core submission

**Complete Project Success (Phases 1-10) - 12-14 weeks:**
- Core integration merged or pending in HA Core
- Custom Lovelace montage card available via HACS
- Multi-camera grid view with real-time motion indicators
- Quick action controls in card
- Advanced automation examples documented
- Community feedback incorporated
- Production-ready for end users

## Recommended Implementation Order (Based on Your Priorities)

Given your focus on **HA Core submission** with **ZM 1.37+ MQTT**, **live streaming**, and **event playback**:

**Week 1-2: Foundation**
- Phase 1: Build and test API client against your ZM 1.37+ instance
- Document actual MQTT message formats from your system
- Validate stream URLs and event clip URLs

**Week 3: Config Flow**
- Phase 2: Implement UI-based configuration
- Test connection validation with your ZM server
- Ensure seamless setup experience

**Week 4-5: Core Viewing (MVP)**
- Phase 3: Live camera streaming
- Phase 7: Event playback (moved up due to priority)
- Test both features thoroughly with your cameras

**Week 6-7: MQTT Real-Time (MVP)**
- Phase 4: MQTT integration (extended time for thorough testing)
- Monitor real event latency on your system
- Optimize for sub-second notifications

**Week 8: Sensors & Motion**
- Phase 5: Binary sensors and event sensors
- Integrate with MQTT for instant updates
- Test notification automations

**Week 9: Controls**
- Phase 6: Buttons, selects, services
- Complete the entity model

**Week 10: Polish**
- Phase 8: Diagnostics, logging, code quality
- Prepare for Gold tier standards

**Week 11-12: Testing & Docs**
- Phase 9: Comprehensive testing and documentation
- Screenshot creation and automation examples
- HA Core submission preparation

**Week 13-16: Lovelace Card (Parallel)**
- Phase 10: Custom montage card
- Can start during Phase 8 and continue after Phase 9
- Independent from core integration
