# Quick Reference

## Build & Deploy

```bash
# One-time setup
npm install

# Build the card
npm run build

# Deploy to HA Docker
./deploy-to-ha.sh zmha-homeassistant

# Development (auto-rebuild)
npm run dev
```

## Add to Home Assistant

**Settings → Dashboards → Resources → Add Resource**
- URL: `/local/zoneminder-card.js`
- Type: `JavaScript Module`

**Then add card to dashboard:**

```yaml
type: custom:zoneminder-card
monitors:
  - entity: camera.hikvision_ds_2cd2087g2_lu
  - entity: camera.driveway_east
columns: 2
```

## Entity Names

Check your actual camera entity names:
```bash
docker exec zmha-homeassistant grep "camera\." /config/.storage/core.entity_registry | grep zoneminder
```

Or in HA: **Developer Tools → States** → Search "camera"

## go2rtc URL

Your go2rtc is at: `http://192.168.0.45:1984`

Test it: http://192.168.0.45:1984

## Troubleshooting

**Card not loading?**
1. Clear browser cache (Ctrl+Shift+R)
2. Check browser console (F12)
3. Verify file exists: `docker exec zmha-homeassistant ls -lh /config/www/zoneminder-card.js`

**WebRTC not working?**
- Try MSE mode: `streaming_mode: mse`
- Check go2rtc is accessible from browser
- Check browser console for WebSocket errors

## Quick Test

```yaml
type: custom:zoneminder-card
zoneminder_go2rtc_url: http://192.168.0.45:1984
monitors:
  - entity: camera.hikvision_ds_2cd2087g2_lu
    stream_id: "1"
columns: 1
streaming_mode: webrtc
```
