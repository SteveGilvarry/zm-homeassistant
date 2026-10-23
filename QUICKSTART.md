# Quick Start Guide

Get the ZoneMinder Card running in 5 minutes!

## Prerequisites

✅ ZoneMinder 1.37+ with go2rtc configured
✅ Home Assistant with zmha integration installed
✅ Node.js 18+ (for building)

## Step 1: Build the Card

```bash
cd /Users/stevengilvarry/Code/zoneminder-card
npm install
npm run build
```

## Step 2: Copy to Home Assistant

```bash
# If HA is local:
cp dist/zoneminder-card.js /path/to/homeassistant/config/www/

# If HA is in Docker:
docker cp dist/zoneminder-card.js homeassistant:/config/www/
```

## Step 3: Add Resource

1. Open Home Assistant
2. Go to **Settings → Dashboards → Resources**
3. Click **Add Resource**
4. Enter:
   - URL: `/local/zoneminder-card.js`
   - Resource type: `JavaScript Module`
5. Click **Create**

## Step 4: Add Card to Dashboard

1. Go to your dashboard
2. Click **Edit Dashboard**
3. Click **Add Card**
4. Click **Custom: ZoneMinder Card** (or search for "zoneminder")
5. Configure:

```yaml
type: custom:zoneminder-card
title: Security Cameras
monitors:
  - entity: camera.front_door
  - entity: camera.backyard
```

6. Click **Save**

## Step 5: Enjoy!

You should now see your cameras streaming via WebRTC with ultra-low latency! 🎉

## Troubleshooting

### Card not appearing?
- Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
- Check browser console for errors (F12)
- Verify resource was added correctly

### Cameras not loading?
- Check that entities exist (Developer Tools → States)
- Verify go2rtc is accessible: `http://your-zm-server:1984`
- Check browser console for WebSocket errors

### Motion indicators not working?
- Verify binary sensor entities exist: `binary_sensor.{camera}_motion`
- Check MQTT is working in zmha integration

## Next Steps

- Read [README.md](README.md) for full configuration options
- See [example-config.yaml](example-config.yaml) for more examples
- Check [BUILDING.md](BUILDING.md) for development setup

## Need Help?

- Open an issue: [GitHub Issues](https://github.com/yourusername/zoneminder-card/issues)
- Read the docs: [GO2RTC_WEBRTC_INTEGRATION.md](../zmha/GO2RTC_WEBRTC_INTEGRATION.md)
