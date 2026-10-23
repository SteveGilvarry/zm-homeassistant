# ZoneMinder Card

A custom Lovelace card for Home Assistant that displays ZoneMinder cameras with **direct go2rtc WebRTC streaming** for ultra-low latency video.

## Features

- ✨ **Direct WebRTC streaming** from ZoneMinder's go2rtc (no Home Assistant proxy)
- 🎥 **Multi-camera montage view** with responsive grid layout
- 🚨 **Real-time motion indicators** synced with MQTT binary sensors
- 🔄 **Multiple streaming modes**: WebRTC, MSE, HLS, MJPEG
- 📱 **Mobile-friendly** with touch support
- ⚡ **Ultra-low latency** (<1 second with WebRTC)
- 🎨 **Customizable** grid layout, aspect ratio, and display options

## Prerequisites

- Home Assistant 2024.1 or newer
- [ZoneMinder Integration (zmha)](https://github.com/yourusername/zmha) installed
- ZoneMinder 1.37+ with go2rtc configured
- MQTT integration (for real-time motion detection)

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Frontend"
3. Click the menu (three dots) in the top right
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/yourusername/zoneminder-card`
6. Category: "Lovelace"
7. Click "Add"
8. Click "Install" on the ZoneMinder Card
9. Restart Home Assistant

### Manual Installation

1. Download `zoneminder-card.js` from the [latest release](https://github.com/yourusername/zoneminder-card/releases)
2. Copy it to `config/www/zoneminder-card.js`
3. Add the following to your Lovelace resources (Settings → Dashboards → Resources):
   ```yaml
   url: /local/zoneminder-card.js
   type: module
   ```
4. Restart Home Assistant

## Configuration

### Basic Configuration

```yaml
type: custom:zoneminder-card
title: Security Cameras
monitors:
  - entity: camera.front_door
  - entity: camera.backyard
  - entity: camera.garage
  - entity: camera.driveway
```

### Full Configuration

```yaml
type: custom:zoneminder-card
title: Security Cameras
zoneminder_go2rtc_url: http://192.168.0.45:1984  # Auto-detected if not provided
monitors:
  - entity: camera.front_door
    stream_id: "1"  # Optional: Monitor ID for go2rtc (auto-detected from entity)
    name: "Front Door"  # Optional: Override monitor name
  - entity: camera.backyard
    stream_id: "2"
  - entity: camera.garage
    stream_id: "4"
columns: 2  # Number of columns in grid (default: 2)
aspect_ratio: "16:9"  # Aspect ratio for cameras (default: 16:9)
streaming_mode: webrtc  # webrtc | mse | hls | mjpeg (default: webrtc)
show_motion_indicator: true  # Show motion detection overlay (default: true)
show_controls: false  # Show camera controls (default: false)
click_action: fullscreen  # fullscreen | events | none (default: fullscreen)
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `type` | string | **required** | Must be `custom:zoneminder-card` |
| `title` | string | optional | Card title |
| `zoneminder_go2rtc_url` | string | auto-detected | go2rtc base URL (e.g., `http://192.168.0.45:1984`) |
| `monitors` | list | **required** | List of monitor configurations (see below) |
| `columns` | number | `2` | Number of columns in grid layout |
| `aspect_ratio` | string | `16:9` | Aspect ratio for cameras (`16:9`, `4:3`, `1:1`, etc.) |
| `streaming_mode` | string | `webrtc` | Streaming protocol: `webrtc`, `mse`, `hls`, `mjpeg` |
| `show_motion_indicator` | boolean | `true` | Show motion detection overlay |
| `show_controls` | boolean | `false` | Show camera controls |
| `click_action` | string | `fullscreen` | Action on click: `fullscreen`, `events`, `none` |

### Monitor Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `entity` | string | **required** | Camera entity ID (e.g., `camera.front_door`) |
| `stream_id` | string | auto-detected | Monitor ID for go2rtc (e.g., `"1"`) |
| `name` | string | auto-detected | Display name for the monitor |

## How It Works

### Architecture

The ZoneMinder Card uses a **two-component architecture**:

1. **ZoneMinder Integration (zmha)** - Provides:
   - Camera entities with metadata
   - Binary motion sensors (MQTT)
   - go2rtc configuration auto-detection

2. **ZoneMinder Card (this card)** - Provides:
   - Direct WebRTC streaming to ZoneMinder's go2rtc
   - Multi-camera montage view
   - Real-time motion indicators

### Streaming Flow

```
Browser ──(WebRTC)──> ZoneMinder's go2rtc ──> Camera
           ↑
           └── No Home Assistant proxy!
```

This direct connection provides:
- **Lower latency** (typically <1 second)
- **Better performance** (no transcoding in HA)
- **Reduced load** on Home Assistant

### Motion Detection

Motion detection is handled via Home Assistant binary sensors that receive real-time updates from ZoneMinder's MQTT:

1. ZoneMinder detects motion
2. Publishes to MQTT (<1 second)
3. Home Assistant binary sensor updates
4. Card shows motion indicator overlay

## Streaming Modes

The card supports multiple streaming protocols:

### WebRTC (Recommended)
- **Latency**: <1 second
- **Quality**: Excellent
- **Browser Support**: All modern browsers
- **Bandwidth**: Low (1-5 Mbps per stream)

### MSE (Media Source Extensions)
- **Latency**: 1-3 seconds
- **Quality**: Excellent
- **Browser Support**: Chrome, Firefox, Safari (Mac/iPad)
- **Bandwidth**: Low (1-5 Mbps per stream)

### HLS (HTTP Live Streaming)
- **Latency**: 3-10 seconds
- **Quality**: Good
- **Browser Support**: Safari (all), Chrome Android
- **Bandwidth**: Medium (buffering)

### MJPEG
- **Latency**: <1 second
- **Quality**: Variable
- **Browser Support**: All browsers
- **Bandwidth**: High (5-20 Mbps per stream)

## Examples

### 2x2 Grid with Motion Indicators

```yaml
type: custom:zoneminder-card
title: Perimeter Cameras
monitors:
  - entity: camera.front_door
  - entity: camera.back_door
  - entity: camera.garage
  - entity: camera.driveway
columns: 2
show_motion_indicator: true
```

### Single Camera Fullscreen

```yaml
type: custom:zoneminder-card
monitors:
  - entity: camera.front_door
columns: 1
aspect_ratio: "16:9"
click_action: fullscreen
```

### 4-Column Grid (Large Display)

```yaml
type: custom:zoneminder-card
title: All Cameras
monitors:
  - entity: camera.cam1
  - entity: camera.cam2
  - entity: camera.cam3
  - entity: camera.cam4
  - entity: camera.cam5
  - entity: camera.cam6
  - entity: camera.cam7
  - entity: camera.cam8
columns: 4
aspect_ratio: "16:9"
```

### MSE Fallback (for browsers without WebRTC)

```yaml
type: custom:zoneminder-card
title: Security Cameras
monitors:
  - entity: camera.front_door
  - entity: camera.backyard
streaming_mode: mse  # Use MSE instead of WebRTC
```

## Troubleshooting

### Cameras not loading

1. **Check go2rtc URL**: Verify `zoneminder_go2rtc_url` is accessible from your browser
   ```
   http://your-zm-server:1984
   ```

2. **Check browser console** for errors (F12 → Console)

3. **Verify entity IDs**: Make sure camera entities exist in Home Assistant

4. **Check network**: Ensure browser can reach go2rtc (may need VPN or firewall rules)

### Motion indicators not working

1. **Check MQTT**: Verify MQTT integration is working
2. **Check binary sensors**: Ensure motion sensors exist:
   ```
   binary_sensor.front_door_motion
   binary_sensor.backyard_motion
   ```
3. **Check entity naming**: Motion sensor should be `binary_sensor.{camera_name}_motion`

### WebRTC connection fails

1. **Try MSE mode** as fallback:
   ```yaml
   streaming_mode: mse
   ```

2. **Check STUN servers**: Firewall may block STUN servers
   - `stun.cloudflare.com:3478`
   - `stun.l.google.com:19302`

3. **Check WebSocket**: Ensure WebSocket connection works:
   ```
   ws://your-zm-server:1984/api/ws?src=1
   ```

### High CPU usage

1. **Reduce number of visible cameras**
2. **Use lower resolution streams** (configure in ZoneMinder)
3. **Switch to MSE or HLS mode** (less CPU than WebRTC on some devices)

## Development

### Setup

```bash
npm install
```

### Build

```bash
npm run build
```

### Development Server

```bash
npm run dev
```

Then add to Lovelace resources:
```yaml
url: http://localhost:5000/zoneminder-card.js
type: module
```

### Linting

```bash
npm run lint
```

### Format Code

```bash
npm run format
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run linting and formatting
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file

## Credits

- Built with [Lit](https://lit.dev)
- Uses [go2rtc](https://github.com/AlexxIT/go2rtc) for WebRTC streaming
- Designed for [ZoneMinder](https://zoneminder.com) integration

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/zoneminder-card/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/zoneminder-card/discussions)
- **Integration**: [ZoneMinder ZMHA Integration](https://github.com/yourusername/zmha)
