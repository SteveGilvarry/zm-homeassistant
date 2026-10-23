# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **custom Home Assistant Lovelace card** written in TypeScript using the Lit web component framework. It displays ZoneMinder security camera feeds with direct WebRTC streaming via go2rtc, bypassing Home Assistant's video proxy for ultra-low latency (<1 second).

## Build Commands

```bash
npm install          # Install dependencies
npm run build        # Production build (minified, no source maps)
npm run dev          # Development server + watch mode (http://localhost:5000)
npm run lint         # ESLint type checking
npm run format       # Prettier code formatting
```

## Deployment to Home Assistant Docker

After making changes to the card source code:

1. Build the distribution file:
   ```bash
   npm run build
   ```

2. Copy to Home Assistant www directory:
   ```bash
   cp dist/zoneminder-card.js ~/Code/zmha/ha_config/www/zoneminder-card.js
   ```

3. Restart Home Assistant container:
   ```bash
   cd ~/Code/zmha && docker-compose restart homeassistant
   ```

4. Clear browser cache to reload the card (Ctrl+F5 or Cmd+Shift+R)

Note: The HA instance is running in docker-compose at `~/Code/zmha` with volume mount:
- `./ha_config/www:/config/www` - Custom Lovelace resources

## Development Workflow

1. Run `npm run dev` to start the dev server with hot reload
2. Add to Home Assistant Lovelace resources: `http://localhost:5000/zoneminder-card.js`
3. Manual testing via `test.html` which mocks Home Assistant state
4. For Docker testing: build and copy to `../zmha/ha_config/www/`, then hard-refresh HA dashboard

## Architecture

### Component Structure

```
src/
├── zoneminder-card.ts   # Main card (LitElement) - grid layout, motion detection, HA integration
├── webrtc-player.ts     # Video streaming component - WebRTC/MSE/HLS/MJPEG protocols
└── types.ts             # TypeScript interfaces for config, HA types, WebRTC signaling
```

### Key Components

**ZoneMinerCard** (`zoneminder-card.ts`)
- Registered as `custom:zoneminder-card` in Home Assistant
- Renders CSS Grid of camera monitors with configurable columns/aspect ratios
- Detects motion via `binary_sensor.{camera_name}_motion` entities from MQTT
- Auto-detects go2rtc URL from camera entity attributes (`go2rtc_url`, `go2rtc_stream_id`)
- Handles orientation/rotation from entity attributes for portrait cameras

**WebRTCPlayer** (`webrtc-player.ts`)
- Custom element `<webrtc-player>` for video streaming
- WebRTC signaling via WebSocket (`ws://{go2rtc}/api/ws?src={streamId}`)
- Fallback modes: MSE (`.mp4`), HLS (`.m3u8`), MJPEG (`.mjpeg`)
- Auto-reconnect on connection drop (5 second delay)
- CSS transforms for camera orientation (rotate, flip)

### Data Flow

```
Browser <--WebRTC--> ZoneMinder's go2rtc <-- Camera
                     (direct, no HA proxy)

Motion: ZoneMinder --> MQTT --> HA binary_sensor --> Card overlay
```

### Configuration Interface

Card config is defined in `ZoneMinerCardConfig` (types.ts):
- `monitors[]` - Array of camera entities with optional stream_id and grid span
- `streaming_mode` - webrtc | mse | hls | mjpeg
- `columns` / `aspect_ratio` - Grid layout settings
- `zoneminder_go2rtc_url` - Optional override (auto-detected from entity attributes)

## Build Output

- `dist/zoneminder-card.js` - Single bundled ES module
- Rollup bundles with terser minification in production
- TypeScript targets ES2020 with strict mode

## Home Assistant Integration Points

- Camera entities expose `go2rtc_url`, `go2rtc_stream_id`, `monitor_id`, `width`, `height`, `orientation` in attributes
- Motion sensors follow naming convention: `binary_sensor.{camera_name}_motion`
- Card registers via `window.customCards` for HA card picker
