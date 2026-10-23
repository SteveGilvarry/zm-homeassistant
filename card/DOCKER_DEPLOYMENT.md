# Docker Deployment Guide

How to deploy the ZoneMinder Card to Home Assistant running in Docker.

## Quick Deployment

### Method 1: Using the Deploy Script (Recommended)

```bash
# Build the card
npm install
npm run build

# Deploy to HA Docker container
./deploy-to-ha.sh zmha-homeassistant
```

That's it! The script will:
- ✅ Create the `www` directory if needed
- ✅ Copy the card file to `/config/www/zoneminder-card.js`
- ✅ Verify the deployment
- ✅ Show next steps

### Method 2: Manual Docker Copy

```bash
# Build the card
npm run build

# Find your container name
docker ps | grep homeassistant

# Copy the file
docker cp dist/zoneminder-card.js zmha-homeassistant:/config/www/zoneminder-card.js

# Verify
docker exec zmha-homeassistant ls -lh /config/www/zoneminder-card.js
```

### Method 3: Docker Volume Mount (Development)

If you want automatic updates during development, mount the dist folder:

**In your `docker-compose.yml`:**

```yaml
services:
  homeassistant:
    image: homeassistant/home-assistant:latest
    volumes:
      - ./ha_config:/config
      - /Users/stevengilvarry/Code/zoneminder-card/dist:/config/www/zoneminder-card:ro
```

Then access as: `/local/zoneminder-card/zoneminder-card.js`

## Configure in Home Assistant

### Step 1: Add Lovelace Resource

**Via UI:**
1. Open Home Assistant
2. Go to **Settings** → **Dashboards** → **Resources** (top right menu)
3. Click **Add Resource**
4. Configure:
   - **URL**: `/local/zoneminder-card.js`
   - **Resource type**: `JavaScript Module`
5. Click **Create**

**Via YAML (if using YAML mode):**

Edit your Lovelace config:

```yaml
resources:
  - url: /local/zoneminder-card.js
    type: module
```

### Step 2: Clear Browser Cache

**Important!** Always clear cache after deploying:
- Chrome/Edge: `Ctrl+Shift+R` or `Cmd+Shift+R`
- Firefox: `Ctrl+Shift+R` or `Cmd+Shift+R`
- Safari: `Cmd+Option+R`

Or use incognito/private mode to test.

### Step 3: Add Card to Dashboard

1. Go to your dashboard
2. Click **Edit Dashboard** (top right)
3. Click **Add Card**
4. Scroll down and select **Custom: ZoneMinder Card**
   - Or click **Manual** and paste the YAML below

**Basic Configuration:**

```yaml
type: custom:zoneminder-card
title: Security Cameras
monitors:
  - entity: camera.front_door
  - entity: camera.backyard
columns: 2
```

**Full Configuration:**

```yaml
type: custom:zoneminder-card
title: Security Cameras
zoneminder_go2rtc_url: http://192.168.0.45:1984
monitors:
  - entity: camera.hikvision_ds_2cd2087g2_lu
    stream_id: "1"
    name: "Front Door"
  - entity: camera.driveway_east
    stream_id: "2"
    name: "Driveway"
columns: 2
streaming_mode: webrtc
show_motion_indicator: true
```

## Development Workflow

### Watch Mode (Auto-rebuild)

```bash
# Terminal 1: Watch and rebuild on changes
cd /Users/stevengilvarry/Code/zoneminder-card
npm run dev

# Terminal 2: Auto-deploy on changes (optional)
while true; do
  inotifywait -e modify dist/zoneminder-card.js
  ./deploy-to-ha.sh zmha-homeassistant
  echo "✅ Deployed! Clear browser cache to see changes."
done
```

**macOS Alternative (using fswatch):**

```bash
# Install fswatch first: brew install fswatch
fswatch -o dist/zoneminder-card.js | xargs -n1 -I{} ./deploy-to-ha.sh zmha-homeassistant
```

### Live Reload Setup

For even faster development:

1. **Start dev server** in card directory:
   ```bash
   npm run dev
   ```

2. **Add dev resource** in HA:
   - URL: `http://YOUR_COMPUTER_IP:5000/zoneminder-card.js`
   - Type: `JavaScript Module`

3. **Make changes** - card will auto-reload!

4. **Switch back to production** when done:
   - Remove dev resource
   - Add production resource (`/local/zoneminder-card.js`)

## Troubleshooting

### Card Not Loading

**Check if file exists:**
```bash
docker exec zmha-homeassistant ls -lh /config/www/zoneminder-card.js
```

**Check file contents:**
```bash
docker exec zmha-homeassistant head -20 /config/www/zoneminder-card.js
```

**Check browser console (F12):**
- Look for 404 errors (file not found)
- Look for syntax errors (build issue)
- Look for "zoneminder-card" errors

### Card Shows Old Version

1. **Clear browser cache** (Ctrl+Shift+R or Cmd+Shift+R)
2. **Hard reload** multiple times
3. **Try incognito mode**
4. **Redeploy the card:**
   ```bash
   ./deploy-to-ha.sh zmha-homeassistant
   ```

### Container Name Unknown

**Find your container:**
```bash
docker ps --format 'table {{.Names}}\t{{.Image}}'
```

**Use correct name in script:**
```bash
./deploy-to-ha.sh YOUR_CONTAINER_NAME
```

### Permission Issues

**Check www directory permissions:**
```bash
docker exec zmha-homeassistant ls -ld /config/www
docker exec zmha-homeassistant chmod 755 /config/www
```

### WebRTC Not Working

**Check go2rtc URL is accessible from browser:**
```bash
# From your computer
curl http://192.168.0.45:1984

# From HA container
docker exec zmha-homeassistant curl http://192.168.0.45:1984
```

**Check browser console for WebSocket errors:**
- F12 → Network → WS (WebSocket filter)
- Look for connection to `ws://192.168.0.45:1984/api/ws?src=1`

**Try MSE fallback:**
```yaml
type: custom:zoneminder-card
streaming_mode: mse  # Instead of webrtc
monitors:
  - entity: camera.front_door
```

## Docker-Compose Full Example

Here's a complete `docker-compose.yml` for development:

```yaml
version: '3.8'

services:
  homeassistant:
    container_name: zmha-homeassistant
    image: homeassistant/home-assistant:latest
    restart: unless-stopped
    volumes:
      - ./ha_config:/config
      - /etc/localtime:/etc/localtime:ro
      # Optional: Mount card for development
      # - /Users/stevengilvarry/Code/zoneminder-card/dist:/config/www/zoneminder-card:ro
    ports:
      - "8123:8123"
    environment:
      - TZ=America/New_York

  # ZoneMinder (example)
  zoneminder:
    image: zoneminderhq/zoneminder:latest-ubuntu22.04
    ports:
      - "80:80"
    # ... rest of ZM config
```

## Deployment Checklist

Before deploying to production:

- [ ] Run `npm run build` (not `npm run dev`)
- [ ] Check file size is reasonable (~30KB)
- [ ] Deploy to HA: `./deploy-to-ha.sh`
- [ ] Add Lovelace resource
- [ ] Clear browser cache
- [ ] Test card loads without errors
- [ ] Test WebRTC streaming works
- [ ] Test motion indicators work
- [ ] Test on mobile
- [ ] Document the version deployed

## Updating the Card

When you make changes:

```bash
# 1. Make your changes to src/*.ts files
# 2. Rebuild
npm run build

# 3. Redeploy
./deploy-to-ha.sh zmha-homeassistant

# 4. Clear browser cache (Ctrl+Shift+R)
# 5. Reload the page
```

## Production Deployment

For a production deployment:

1. **Tag a release:**
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

2. **Build production:**
   ```bash
   npm run build
   ```

3. **Deploy:**
   ```bash
   ./deploy-to-ha.sh zmha-homeassistant
   ```

4. **Or use HACS** (when published):
   - HACS → Frontend → ZoneMinder Card
   - Click Install
   - No manual deployment needed!

## Summary

**Development:**
```bash
npm run dev  # Watch mode
# Edit files, auto-rebuild
./deploy-to-ha.sh zmha-homeassistant
# Clear browser cache
```

**Production:**
```bash
npm run build
./deploy-to-ha.sh zmha-homeassistant
# Add Lovelace resource
# Clear browser cache
```

**HACS (Future):**
```
HACS → Frontend → ZoneMinder Card → Install
# No manual steps needed!
```
