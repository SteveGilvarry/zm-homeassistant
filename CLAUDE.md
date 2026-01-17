# ZMHA Development Guide for Claude

This document provides context and guidance for Claude when working on the ZoneMinder Home Assistant (ZMHA) integration project.

## Project Overview

**Goal:** Create a Gold-tier Home Assistant Core integration for ZoneMinder that provides best-in-class UX with zero-YAML configuration, real-time MQTT event updates, and comprehensive camera/event management.

**Status:** Greenfield project - starting from specification

**Target Users:** Home Assistant users with ZoneMinder NVR installations

**Key Differentiators vs Existing Solutions:**
- Zero YAML configuration (100% UI-based)
- MQTT-first event handling (ZM 1.37+) with polling fallback (ZM 1.36+)
- Fast live stream startup
- Rich notifications with event clips
- Native HA Core integration (not custom component long-term)

## Architecture Overview

### Component Structure

```
custom_components/zoneminder/
├── Core Integration
│   ├── __init__.py          - Entry point, coordinator setup, service registration
│   ├── manifest.json        - Integration metadata and dependencies
│   ├── config_flow.py       - UI configuration flows (user, reauth, options)
│   └── const.py             - Shared constants and enumerations
│
├── Data Layer
│   ├── api.py               - Async ZoneMinder API client
│   ├── mqtt.py              - MQTT event listener (ZM 1.37+)
│   ├── coordinator.py       - DataUpdateCoordinator (polling fallback)
│   └── models.py            - Data models (Monitor, Event, MonitorData)
│
├── Entity Platforms
│   ├── camera.py            - Live streams + event clip playback
│   ├── binary_sensor.py     - Motion detection sensors
│   ├── sensor.py            - Event tracking sensors (ID, time, count)
│   ├── button.py            - Manual alarm trigger buttons
│   └── select.py            - Monitor function/mode selectors
│
└── Support
    ├── exceptions.py        - Custom exception hierarchy
    ├── diagnostics.py       - Debug data collection
    ├── services.yaml        - Service definitions
    └── strings.json         - Translatable UI strings
```

### Data Flow

**MQTT Mode (Primary):**
```
ZM Event → MQTT Broker → HA MQTT Integration → mqtt.py → Coordinator
→ Entity Callbacks → UI Updates
```

**Polling Mode (Fallback):**
```
Coordinator Timer → api.py → ZM API → Parse Response → Coordinator
→ Entity Callbacks → UI Updates
```

### Key Design Patterns

1. **Coordinator Pattern**: Single `DataUpdateCoordinator` manages polling and data distribution to all entities

2. **Hybrid Updates**: MQTT provides instant updates, coordinator provides periodic health checks and fallback

3. **Device Registry**: Each ZM monitor = one HA device with multiple entities

4. **Async Everything**: All I/O operations are async, no blocking calls

5. **Graceful Degradation**: MQTT unavailable → polling mode, auth failed → reauth flow

## ZoneMinder API Reference

### Authentication

```python
# Login (required before any API calls)
POST /zm/api/host/login.json
Body: username=admin&password=secret
Response: {"access_token": "...", "expires": 3600}

# Subsequent requests include token
GET /zm/api/monitors.json?token=...
```

### Core Endpoints

**Monitors:**
```python
GET /zm/api/monitors.json              # List all monitors
GET /zm/api/monitors/{id}.json         # Get single monitor
POST /zm/api/monitors/{id}.json        # Update monitor (change function)
```

**Events:**
```python
GET /zm/api/events.json?MonitorId={id}&limit=100  # List events
GET /zm/api/events/{id}.json                       # Get event details
```

**Alarms:**
```python
GET /zm/api/monitors/alarm/id:{id}/command:on.json  # Trigger alarm
GET /zm/api/monitors/alarm/id:{id}/command:off.json # Cancel alarm
```

**PTZ:**
```python
POST /zm/api/controls/{monitor_id}.json
Body: control=moveLeft&xCoord=0&yCoord=0
```

**Streams:**
```python
# Live MJPEG stream
/zm/cgi-bin/nph-zms?mode=jpeg&monitor={id}&auth={token}

# Event video
/zm/api/events/{event_id}.mp4?auth={token}
```

### API Response Formats

**Monitor Object:**
```json
{
  "id": "1",
  "name": "Front Door",
  "function": "Modect",
  "enabled": "1",
  "width": "1920",
  "height": "1080",
  "type": "Ffmpeg",
  "protocol": "rtsp",
  "host": "192.168.1.100",
  "port": "554",
  "path": "/stream"
}
```

**Event Object:**
```json
{
  "id": "12345",
  "monitorId": "1",
  "name": "Event-12345",
  "cause": "Motion",
  "startTime": "2025-01-17 10:30:00",
  "endTime": "2025-01-17 10:30:45",
  "length": "45.2",
  "frames": "1356",
  "alarmFrames": "234",
  "notes": "Front porch detection"
}
```

## MQTT Integration (ZM 1.37+)

### Topic Structure

ZoneMinder publishes to these topics:

```
zoneminder/events/{monitor_id}      # New event notifications
zoneminder/monitors/{monitor_id}    # Monitor status updates (optional)
```

### Event Message Format

```json
{
  "event_id": 12345,
  "monitor_id": 1,
  "monitor_name": "Front Door",
  "cause": "Motion",
  "timestamp": "2025-01-17T10:30:00Z",
  "notes": "Detection in zone: Porch",
  "state": "started"  // or "ended"
}
```

### MQTT Setup Requirements

1. ZM must have MQTT enabled in Options → System
2. HA must have MQTT integration configured
3. Both must connect to same MQTT broker
4. ZMHA detects MQTT automatically via `mqtt.async_wait_for_mqtt_client()`

### Subscription Pattern

```python
# In mqtt.py
await mqtt.async_subscribe(
    hass,
    f"{topic_prefix}/events/+",  # Subscribe to all monitor events
    self._handle_event_message,
    qos=1
)
```

## Home Assistant Integration Standards

### Config Flow Requirements

**Must Have:**
- User step for initial setup
- Validation with clear error messages
- Unique ID (prevents duplicate entries)
- Reauth flow for expired credentials
- Options flow for runtime settings

**Error Keys (strings.json):**
```json
{
  "error": {
    "cannot_connect": "Unable to connect to ZoneMinder",
    "invalid_auth": "Invalid username or password",
    "unknown": "Unexpected error occurred"
  }
}
```

### Entity Guidelines

**Naming:**
- Use `_attr_has_entity_name = True`
- Entity ID format: `{platform}.{monitor_name}_{suffix}`
- Example: `camera.front_door`, `binary_sensor.front_door_motion`

**Device Linkage:**
```python
@property
def device_info(self) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, str(self._monitor.id))},
        name=self._monitor.name,
        manufacturer="ZoneMinder",
        model=self._monitor.type,
        configuration_url=f"{self._api_host}/zm/",
    )
```

**Unique IDs:**
- Must be stable across restarts
- Format: `{monitor_id}_{entity_type}`
- Examples: `1_live`, `1_motion`, `1_last_event_id`

### Service Standards

**Service Schema (services.yaml):**
```yaml
trigger_event:
  name: Trigger event
  description: Manually trigger an alarm event
  target:
    device:
      integration: zoneminder
  fields:
    cause:
      name: Cause
      description: Reason for triggering
      example: "Manual trigger from automation"
      selector:
        text:
```

**Service Handler:**
```python
async def handle_trigger_event(call: ServiceCall) -> None:
    """Handle trigger_event service call."""
    device_id = call.data["device_id"]
    cause = call.data.get("cause", "Home Assistant")

    # Get monitor ID from device registry
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get(device_id)
    monitor_id = int(next(iter(device.identifiers))[1])

    # Execute action
    await api.trigger_alarm(monitor_id, cause)
```

### Diagnostics Requirements

**Redact Sensitive Data:**
```python
async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for config entry."""
    data = {
        "zoneminder": {
            "version": await api.get_version(),
            "host": entry.data[CONF_HOST],  # OK to include
            # DO NOT include: username, password, auth_token
            "mqtt_enabled": entry.options.get(CONF_MQTT_ENABLED),
            "monitors": [
                {
                    "id": m.id,
                    "name": m.name,
                    "function": m.function,
                    # Redact: host, path (may contain credentials)
                }
                for m in await api.get_monitors()
            ],
        }
    }
    return data
```

## Testing Strategy

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures and mocks
├── test_init.py             # Integration setup tests
├── test_config_flow.py      # Config flow tests (critical)
├── test_api.py              # API client tests
├── test_coordinator.py      # Coordinator tests
├── test_mqtt.py             # MQTT handling tests
├── test_camera.py           # Camera platform tests
├── test_binary_sensor.py    # Binary sensor tests
├── test_sensor.py           # Sensor tests
├── test_button.py           # Button tests
├── test_select.py           # Select tests
└── test_services.py         # Service tests
```

### Key Fixtures

```python
# conftest.py
@pytest.fixture
def mock_zoneminder_api():
    """Mock ZoneMinder API client."""
    with patch("custom_components.zoneminder.api.ZoneMinerAPI") as mock:
        api = mock.return_value
        api.authenticate = AsyncMock(return_value=True)
        api.get_version = AsyncMock(return_value="1.37.0")
        api.get_monitors = AsyncMock(return_value=[
            Monitor(id=1, name="Front Door", function="Modect", ...),
        ])
        api.get_events = AsyncMock(return_value=[])
        yield api

@pytest.fixture
async def setup_integration(hass, mock_zoneminder_api):
    """Set up integration for testing."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "http://zm.local",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "password",
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
```

### Test Coverage Goals

**Gold Tier Requirements:**
- Overall: >90% coverage
- Config flow: 100% (all paths, all errors)
- API client: >95% (all methods, all error cases)
- Platforms: >85% (entity properties and actions)
- Critical: 100% (auth flow, error handling)

### Test Example

```python
# test_config_flow.py
async def test_user_form_success(hass, mock_zoneminder_api):
    """Test successful user form submission."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "http://zm.local",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "password",
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "ZoneMinder (http://zm.local)"
    assert result["data"][CONF_HOST] == "http://zm.local"

async def test_user_form_invalid_auth(hass, mock_zoneminder_api):
    """Test form with invalid credentials."""
    mock_zoneminder_api.authenticate.side_effect = ZMAuthenticationError()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "http://zm.local", ...},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
```

## Common Pitfalls to Avoid

### 1. Blocking I/O

**Bad:**
```python
def get_monitors(self):
    response = requests.get(f"{self.host}/zm/api/monitors.json")
    return response.json()
```

**Good:**
```python
async def get_monitors(self):
    async with self._session.get(
        f"{self._host}/zm/api/monitors.json",
        timeout=self._timeout
    ) as response:
        response.raise_for_status()
        return await response.json()
```

### 2. Missing Error Handling

**Bad:**
```python
async def async_setup_entry(hass, entry):
    api = ZoneMinerAPI(...)
    monitors = await api.get_monitors()
    # What if authentication fails?
```

**Good:**
```python
async def async_setup_entry(hass, entry):
    api = ZoneMinerAPI(...)
    try:
        await api.authenticate()
        monitors = await api.get_monitors()
    except ZMAuthenticationError:
        raise ConfigEntryAuthFailed("Invalid credentials")
    except ZMConnectionError as err:
        raise ConfigEntryNotReady(f"Cannot connect: {err}")
```

### 3. Hardcoded Values

**Bad:**
```python
stream_url = f"http://zm.local/zm/cgi-bin/nph-zms?monitor=1"
```

**Good:**
```python
from .const import DEFAULT_TIMEOUT, STREAM_PATH

stream_url = f"{self._host}{STREAM_PATH}?monitor={monitor_id}&auth={self._token}"
```

### 4. Missing Device Info

**Bad:**
```python
class ZoneMinerCamera(Camera):
    # No device_info property
    pass
```

**Good:**
```python
class ZoneMinerCamera(CoordinatorEntity, Camera):
    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._monitor.id))},
            name=self._monitor.name,
            manufacturer="ZoneMinder",
        )
```

### 5. Non-Unique Entity IDs

**Bad:**
```python
self._attr_unique_id = "camera"  # Conflicts with other monitors!
```

**Good:**
```python
self._attr_unique_id = f"{monitor.id}_live"  # Unique per monitor
```

## Development Workflow

### Local Development Setup

1. **Clone HA Core for reference:**
   ```bash
   git clone https://github.com/home-assistant/core.git
   ```

2. **Setup development environment:**
   ```bash
   cd zmha
   python3 -m venv venv
   source venv/bin/activate
   pip install homeassistant
   ```

3. **Install for local testing:**
   ```bash
   # Link to HA config
   mkdir -p ~/.homeassistant/custom_components
   ln -s $(pwd)/custom_components/zoneminder ~/.homeassistant/custom_components/
   ```

4. **Run tests:**
   ```bash
   pip install pytest pytest-homeassistant-custom-component
   pytest tests/
   ```

### Code Quality Tools

```bash
# Install tools
pip install black ruff mypy

# Format code
black custom_components/zoneminder/

# Lint code
ruff custom_components/zoneminder/

# Type check
mypy custom_components/zoneminder/
```

### Git Commit Guidelines

Follow Conventional Commits:
```
feat: Add MQTT event listener
fix: Handle missing event end_time
docs: Update README with MQTT setup
test: Add config flow error tests
refactor: Extract stream URL generation
```

## Resources & References

### Official Documentation

- [HA Developer Docs](https://developers.home-assistant.io/)
- [Integration Manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [Config Flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/)
- [Data Update Coordinator](https://developers.home-assistant.io/docs/integration_fetching_data/)
- [Quality Scale](https://developers.home-assistant.io/docs/integration_quality_scale_index/)

### ZoneMinder Documentation

- [ZoneMinder API](https://zoneminder.readthedocs.io/en/stable/api.html)
- [ZoneMinder MQTT](https://zoneminder.readthedocs.io/en/latest/userguide/definemonitor/definemonitor_mqtt.html)

### Reference Integrations (Study These)

1. **Reolink** - Camera platform patterns
   - File: `homeassistant/components/reolink/`
   - Focus: Config flow, camera entities, coordinator

2. **UniFi Protect** - Event handling and rich entities
   - File: `homeassistant/components/unifiprotect/`
   - Focus: Binary sensors, event processing

3. **Axis** - MQTT integration and PTZ
   - File: `homeassistant/components/axis/`
   - Focus: MQTT setup, PTZ services

4. **Synology DSM** - API client and diagnostics
   - File: `homeassistant/components/synology_dsm/`
   - Focus: API design, diagnostics platform

### Community

- [Home Assistant Discord](https://discord.gg/home-assistant) - #devs channel
- [Home Assistant Community Forum](https://community.home-assistant.io/c/development/10)
- [GitHub Discussions](https://github.com/home-assistant/architecture/discussions)

## Implementation Checklist

Use this checklist to track progress through implementation:

**Foundation:**
- [ ] Project structure created
- [ ] manifest.json configured
- [ ] Constants defined in const.py
- [ ] Data models created in models.py
- [ ] Custom exceptions defined
- [ ] API client implemented
- [ ] API client tested against real ZM

**Config Flow:**
- [ ] User config flow working
- [ ] Credential validation implemented
- [ ] Error handling complete
- [ ] Reauth flow implemented
- [ ] Options flow implemented
- [ ] Translations added (strings.json)

**Core Integration:**
- [ ] __init__.py entry point complete
- [ ] Coordinator implemented
- [ ] Device registry setup
- [ ] Platform forwarding working
- [ ] Services registered

**MQTT:**
- [ ] MQTT listener implemented
- [ ] Topic subscriptions working
- [ ] Event parsing correct
- [ ] Coordinator integration complete
- [ ] Fallback to polling tested

**Entity Platforms:**
- [ ] Live camera entities
- [ ] Event camera entities
- [ ] Motion binary sensors
- [ ] Event ID sensors
- [ ] Event time sensors
- [ ] Alarm trigger buttons
- [ ] Function select entities

**Services:**
- [ ] trigger_event service
- [ ] PTZ service
- [ ] Service schemas in services.yaml
- [ ] Device targeting working

**Polish:**
- [ ] Diagnostics platform
- [ ] Comprehensive logging
- [ ] Type hints complete
- [ ] Code formatted (Black/Ruff)

**Testing:**
- [ ] Test structure created
- [ ] Config flow tests (100%)
- [ ] API tests (>95%)
- [ ] Coordinator tests (>90%)
- [ ] Platform tests (>85%)
- [ ] Service tests (>95%)
- [ ] Overall coverage >90%

**Documentation:**
- [ ] README.md complete
- [ ] Setup guide with screenshots
- [ ] Example automations
- [ ] Troubleshooting section
- [ ] CHANGELOG.md

**Quality Assurance:**
- [ ] Tested with ZM 1.36
- [ ] Tested with ZM 1.37
- [ ] MQTT mode tested
- [ ] Polling mode tested
- [ ] Error scenarios tested
- [ ] Performance validated
- [ ] Code review completed

## Quick Reference

### File Priority (Implement in This Order)

1. **api.py** - Foundation for everything else
2. **models.py** - Required by API client
3. **exceptions.py** - Required by API client
4. **const.py** - Used throughout
5. **config_flow.py** - User-facing setup
6. **coordinator.py** - Data management
7. **__init__.py** - Integration entry point
8. **camera.py** - Primary entity type
9. **mqtt.py** - Real-time updates
10. **binary_sensor.py** - Motion detection
11. **sensor.py** - Event tracking
12. **button.py** - Manual controls
13. **select.py** - Monitor modes
14. **diagnostics.py** - Debug support

### Common Commands

```bash
# Run specific test
pytest tests/test_config_flow.py::test_user_form_success -v

# Run with coverage
pytest --cov=custom_components.zoneminder --cov-report=html

# Type check specific file
mypy custom_components/zoneminder/api.py

# Format code
black custom_components/zoneminder/

# Check integration with HA validator
python -m script.hassfest validate custom_components/zoneminder
```

### Environment Variables for Testing

```bash
export ZM_TEST_HOST="http://zm.local"
export ZM_TEST_USERNAME="admin"
export ZM_TEST_PASSWORD="secret"
export ZM_TEST_MQTT_ENABLED="true"
```

## Questions to Ask Before Implementing

### Before Starting a Phase:

1. Have I read the relevant reference integration code?
2. Do I understand the HA patterns for this component?
3. What are the edge cases I need to handle?
4. How will I test this component?

### Before Writing Code:

1. Is this the async way to do it?
2. Am I handling all error cases?
3. Does this follow HA naming conventions?
4. Will this work with the coordinator pattern?

### Before Committing:

1. Did I add/update tests?
2. Did I update type hints?
3. Did I run the linters?
4. Did I test against real ZoneMinder?

## Support & Questions

When encountering issues:

1. **Check HA Logs**: `~/.homeassistant/home-assistant.log`
2. **Enable Debug Logging**: Add to `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.zoneminder: debug
   ```
3. **Review Reference Integrations**: See how others solved similar problems
4. **Ask in HA Discord**: #devs channel for integration development questions

## License & Attribution

This project will be licensed under Apache 2.0 to be compatible with Home Assistant Core.

When referencing code from other integrations, add attribution:
```python
# Inspired by the Reolink integration
# https://github.com/home-assistant/core/blob/dev/homeassistant/components/reolink/
```
