# zm-homeassistant development guide

## Quick Start

### 1. Setup Development Environment

Run the setup script:
```bash
./setup_dev.sh
```

This will:
- Create a Python virtual environment
- Install required dependencies (aiohttp)
- Create `.env` file from template

### 2. Configure Your ZoneMinder Credentials

Edit `.env` with your ZoneMinder server details:
```bash
ZM_HOST=http://your-zm-host:8080
ZM_USERNAME=admin
ZM_PASSWORD=your_password
```

### 3. Test the API Client

```bash
source venv/bin/activate
python test_api.py
```

## Development Environments

### Option 1: Existing ZoneMinder + Local HA Testing

If you already have ZoneMinder 1.37+ running:

1. Configure `.env` with your ZM credentials
2. Test API client: `python test_api.py`
3. Start test HA instance: `docker-compose up homeassistant`
4. Access HA at http://localhost:8123
5. Add the ZoneMinder integration via the UI

### Option 2: Docker Test Environment

Start a complete test environment with HA + MQTT:

```bash
docker-compose up -d
```

This provides:
- **Home Assistant**: http://localhost:8123
- **MQTT Broker**: localhost:1883
- Auto-loads the ZoneMinder custom component

**Note:** You'll still need to provide your own ZoneMinder server or point to an existing one.

### Option 3: Command Line Testing Only

Test the API client without running full HA:

```bash
# Using .env file
python test_api.py

# Or with arguments
python test_api.py http://zm.local:8080 admin password
```

## Project Structure

```
zm-homeassistant/
├── custom_components/zoneminder/   # Integration code
│   ├── api.py                      # Builds the aiozoneminder client
│   ├── const.py                    # Constants
│   ├── exceptions.py               # Shows ZoneMinder errors in the UI
│   └── manifest.json               # Metadata
# The API client, models and errors live in aiozoneminder (a separate repo).
├── test_api.py                     # ✅ API test script
├── .env                            # Your credentials (git-ignored)
├── .env.example                    # Template
├── docker-compose.yml              # Test environment
└── venv/                           # Virtual environment

Phase 1 Status: ✅ COMPLETE
```

## Testing Workflow

### Manual API Testing

```bash
# Activate virtual environment
source venv/bin/activate

# Run comprehensive test
python test_api.py

# Test specific scenarios
python -c "
import asyncio
from test_api import test_api
asyncio.run(test_api('http://zm.local', 'admin', 'pass'))
"
```

### Testing in Home Assistant

1. Start HA container:
   ```bash
   docker-compose up homeassistant
   ```

2. Navigate to http://localhost:8123

3. Complete initial setup

4. Go to Settings → Devices & Services → Add Integration

5. Search for "ZoneMinder"

6. Enter your ZM credentials

7. Verify monitors are discovered

## MQTT Testing

### Monitor ZoneMinder MQTT Events

Connect to the MQTT broker and subscribe to topics:

```bash
# Install mosquitto clients
brew install mosquitto  # macOS
# or
apt-get install mosquitto-clients  # Linux

# Subscribe to all ZoneMinder events
mosquitto_sub -h localhost -t "zoneminder/#" -v

# Subscribe to specific monitor
mosquitto_sub -h localhost -t "zoneminder/events/1" -v
```

### Test MQTT Flow

1. Start MQTT broker: `docker-compose up mosquitto`
2. Subscribe to events in one terminal
3. Trigger motion in ZoneMinder
4. Verify event messages appear

Expected message format:
```json
{
  "event_id": 12345,
  "monitor_id": 1,
  "cause": "Motion",
  "timestamp": "2025-01-17T10:30:00Z",
  "state": "started"
}
```

## Common Issues

### Python Not Configured

```bash
# Install Python 3.11+
brew install python@3.11  # macOS
# or use system package manager

# Verify installation
python3 --version
```

### Missing aiohttp

```bash
source venv/bin/activate
pip install aiohttp
```

### Connection Errors

- Check ZM_HOST in `.env` is correct
- Verify ZoneMinder is accessible: `curl http://zm.local/zm/api/host/getVersion.json`
- Check firewall/network settings

### Authentication Errors

- Verify username/password in `.env`
- Check ZoneMinder authentication settings
- Try logging in via web UI first

## Next Steps

After Phase 1 testing is complete:

1. **Phase 2**: Implement Config Flow (UI-based setup)
2. **Phase 3**: Add Live Camera entities
3. **Phase 4**: Implement MQTT integration
4. **Phase 5**: Add binary sensors and event sensors

## Resources

- [HA Developer Docs](https://developers.home-assistant.io/)
- [ZoneMinder API Docs](https://zoneminder.readthedocs.io/en/stable/api.html)
- [Implementation Plan](IMPLEMENTATION_PLAN.md)
- [Developer Guide](CLAUDE.md)

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `ZM_HOST` | ZoneMinder server URL | `http://zm.local:8080` |
| `ZM_USERNAME` | ZoneMinder username | `admin` |
| `ZM_PASSWORD` | ZoneMinder password | `secretpass` |

## Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or in Home Assistant `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.zoneminder: debug
```
