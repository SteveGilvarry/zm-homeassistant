# ZoneMinder Home Assistant Integration (ZMHA)

A Gold-tier Home Assistant Core integration for ZoneMinder with zero-YAML configuration, real-time MQTT event updates, and comprehensive camera/event management.

## Project Status

**Current Phase:** Phase 1 - Foundation (In Progress)

### Completed

- ✅ Project structure created
- ✅ Integration manifest (manifest.json)
- ✅ Constants and configuration (const.py)
- ✅ Data models for Monitor and Event (models.py)
- ✅ Custom exception hierarchy (exceptions.py)
- ✅ Complete async API client (api.py)

### In Progress

- 🔄 Testing API client against ZM 1.37+ instance

## Testing the API Client

A test script is provided to validate the API client against your ZoneMinder instance:

```bash
python test_api.py <zm_host> <username> <password>
```

Example:
```bash
python test_api.py http://zm.local:8080 admin secretpass
```

The test will:
1. Authenticate with your ZM server
2. Retrieve ZoneMinder version
3. List all monitors
4. Fetch recent events
5. Generate stream and event clip URLs
6. Display all results

## Project Goals

- **Best-in-class UX** compared to Frigate
- **Zero YAML** - 100% UI-based configuration
- **Real-time events** via MQTT (ZM 1.37+)
- **Fast stream startup** with optimized streaming
- **Rich notifications** with snapshots and event clips
- **Gold tier quality** for HA Core submission

## Features (Planned)

### Entities (per Monitor)
- `camera.<monitor>` - Live stream
- `camera.<monitor>_event` - Event clip playback
- `binary_sensor.<monitor>_motion` - Motion detection
- `sensor.<monitor>_last_event_id` - Last event ID
- `sensor.<monitor>_last_event_time` - Last event timestamp
- `button.<monitor>_trigger_alarm` - Manual alarm trigger
- `select.<monitor>_mode` - Monitor function selector

### Services
- `zoneminder.trigger_event` - Trigger manual alarm
- `zoneminder.ptz` - PTZ control

### Custom Lovelace Card
- Multi-camera montage view
- Real-time motion indicators
- Quick action controls
- Event timeline overlay

## Development Timeline

- **Phase 1:** Foundation (Weeks 1-2) - **IN PROGRESS**
- **Phase 2:** Config Flow (Week 3)
- **Phase 3:** Live Cameras (Week 4)
- **Phase 4:** MQTT Integration (Weeks 5-6) - Priority
- **Phase 5:** Sensors & Motion (Week 7)
- **Phase 6:** Controls & Services (Week 8)
- **Phase 7:** Event Playback (Week 9) - Priority
- **Phase 8:** Polish & Diagnostics (Week 10)
- **Phase 9:** Testing & Documentation (Weeks 11-12)
- **Phase 10:** Custom Lovelace Card (Weeks 13-16)

**MVP Target:** 7 weeks (Phases 1-4, 7)
**v1 Release:** 10 weeks (Phases 1-9)
**Complete Project:** 12-14 weeks (All phases)

## Requirements

- Home Assistant 2024.1+
- ZoneMinder 1.37+ (MQTT support)
- MQTT broker configured in Home Assistant
- Python 3.11+

## Documentation

- [ZMHA_INTEGRATION_SPEC.md](ZMHA_INTEGRATION_SPEC.md) - Original specification
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Detailed implementation roadmap
- [CLAUDE.md](CLAUDE.md) - Developer reference guide

## Architecture

```
custom_components/zoneminder/
├── __init__.py              # Integration setup & coordinator
├── manifest.json            # Integration metadata ✅
├── config_flow.py          # Config/options/reauth flows
├── const.py                # Constants & enums ✅
├── api.py                  # ZoneMinder API client ✅
├── mqtt.py                 # MQTT event handler
├── coordinator.py          # DataUpdateCoordinator
├── models.py               # Data models ✅
├── exceptions.py           # Custom exceptions ✅
├── diagnostics.py          # Diagnostics support
├── services.yaml           # Service definitions
├── strings.json            # Translations
├── camera.py               # Camera entities
├── binary_sensor.py        # Motion sensors
├── sensor.py               # Event sensors
├── button.py               # Alarm buttons
└── select.py               # Mode selectors
```

## Contributing

This project follows Home Assistant Core standards:
- Fully async code with aiohttp
- Type hints throughout
- Comprehensive error handling
- >90% test coverage
- Black/Ruff code formatting

## License

Apache 2.0 (compatible with Home Assistant Core)

## Credits

- Integration developed for Home Assistant Core submission
- Planning and architecture by Claude Sonnet 4.5
