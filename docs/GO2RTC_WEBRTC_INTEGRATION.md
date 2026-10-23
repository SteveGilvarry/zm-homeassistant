# go2rtc WebRTC Integration for ZMHA

## Overview

This document describes how to integrate **ZoneMinder's go2rtc WebRTC streaming** directly into Home Assistant via a custom Lovelace card, bypassing Home Assistant's go2rtc entirely.

## Architecture

### Current Implementation (Indirect)
```
Browser → HA's go2rtc → ZM's go2rtc (RTSP) → Camera
```

### Proposed Implementation (Direct)
```
Browser → ZM's go2rtc (WebRTC) → Camera
```

## Benefits of Direct Integration

1. **Lower latency** - One fewer hop in the stream path
2. **No transcoding** - Direct WebRTC from source
3. **Better performance** - HA doesn't proxy/transcode streams
4. **Simpler setup** - Leverages existing ZM go2rtc configuration
5. **Native go2rtc features** - Access to all go2rtc streaming modes

## ZoneMinder go2rtc Configuration

### Discovered Setup
- **go2rtc version**: 1.9.13
- **Base URL**: `http://192.168.0.45:1984`
- **Config file**: `/opt/go2rtc/go2rtc.yaml`
- **Available monitors**: 1, 2, 3, 4 (plus substreams: 1_0, 1_1, 2_0, 3_0, 4_0)

### ZoneMinder Settings
The integration auto-detects go2rtc via ZoneMinder API:
- Query: `GET /zm/api/configs.json`
- Look for: `ZM_GO2RTC_PATH` config value
- Example: `https://192.168.0.45:1985/api`

## go2rtc API Endpoints

### Stream Viewing URLs

#### WebRTC (Recommended)
- **HTML viewer**: `http://192.168.0.45:1984/webrtc.html?src={monitor_id}&media=video+audio`
- **Auto-select**: `http://192.168.0.45:1984/stream.html?src={monitor_id}` (tries WebRTC first)
- **WebRTC only**: `http://192.168.0.45:1984/stream.html?src={monitor_id}&mode=webrtc`

#### Other Formats (Fallbacks)
- **MSE**: `http://192.168.0.45:1984/stream.html?src={monitor_id}&mode=mse`
- **HLS**: `http://192.168.0.45:1984/api/stream.m3u8?src={monitor_id}`
- **MJPEG**: `http://192.168.0.45:1984/api/stream.mjpeg?src={monitor_id}`
- **MP4**: `http://192.168.0.45:1984/api/stream.mp4?src={monitor_id}`

#### Snapshots
- **JPEG**: `http://192.168.0.45:1984/api/frame.jpeg?src={monitor_id}`
- **MP4**: `http://192.168.0.45:1984/api/frame.mp4?src={monitor_id}`

#### RTSP (for HA's go2rtc)
- **Default**: `rtsp://192.168.0.45:8554/{monitor_id}`
- **With MP4**: `rtsp://192.168.0.45:8554/{monitor_id}?mp4`
- **All tracks**: `rtsp://192.168.0.45:8554/{monitor_id}?video=all&audio=all`

### WebSocket API (WebRTC Signaling)

**Endpoint**: `ws://192.168.0.45:1984/api/ws?src={monitor_id}`

## WebRTC Signaling Protocol

### 1. Client-Side Implementation

```javascript
// Create RTCPeerConnection
const pc = new RTCPeerConnection({
    iceServers: [
        {urls: ['stun:stun.cloudflare.com:3478']},
        {urls: ['stun:stun.l.google.com:19302']}
    ]
});

// Add transceivers for receiving video and audio
pc.addTransceiver('video', {direction: 'recvonly'});
pc.addTransceiver('audio', {direction: 'recvonly'});

// Connect to go2rtc WebSocket
const ws = new WebSocket('ws://192.168.0.45:1984/api/ws?src=1');

ws.addEventListener('open', () => {
    // Handle ICE candidates
    pc.addEventListener('icecandidate', ev => {
        if (!ev.candidate) return;
        const msg = {
            type: 'webrtc/candidate',
            value: ev.candidate.candidate
        };
        ws.send(JSON.stringify(msg));
    });

    // Create and send offer
    pc.createOffer().then(offer => {
        return pc.setLocalDescription(offer);
    }).then(() => {
        const msg = {
            type: 'webrtc/offer',
            value: pc.localDescription.sdp
        };
        ws.send(JSON.stringify(msg));
    });
});

ws.addEventListener('message', ev => {
    const msg = JSON.parse(ev.data);

    if (msg.type === 'webrtc/candidate') {
        pc.addIceCandidate({
            candidate: msg.value,
            sdpMid: '0'
        });
    } else if (msg.type === 'webrtc/answer') {
        pc.setRemoteDescription({
            type: 'answer',
            sdp: msg.value
        });
    }
});

// Attach stream to video element
pc.addEventListener('track', ev => {
    document.getElementById('video').srcObject = ev.streams[0];
});
```

### 2. Message Flow

```
Client                          go2rtc
  |                               |
  |--- WebSocket Connect -------->|
  |<-- WebSocket Open ------------|
  |                               |
  |--- webrtc/offer ------------->| (SDP offer)
  |<-- webrtc/answer -------------|  (SDP answer)
  |                               |
  |--- webrtc/candidate --------->| (ICE candidate)
  |<-- webrtc/candidate ----------| (ICE candidate)
  |                               |
  |<== WebRTC Media Stream =======| (P2P connection established)
```

### 3. Message Formats

**Offer (Client → go2rtc)**
```json
{
  "type": "webrtc/offer",
  "value": "v=0\r\no=- ... SDP content ..."
}
```

**Answer (go2rtc → Client)**
```json
{
  "type": "webrtc/answer",
  "value": "v=0\r\no=- ... SDP content ..."
}
```

**ICE Candidate (Bidirectional)**
```json
{
  "type": "webrtc/candidate",
  "value": "candidate:... ICE candidate string ..."
}
```

## Custom Lovelace Card Implementation

### Architecture

**Two-Component Approach:**

1. **Integration (zmha)** - HACS Integration
   - Provides camera entities (metadata only)
   - Provides binary motion sensors
   - MQTT real-time events
   - No streaming (or MJPEG fallback only)

2. **Custom Card (zoneminder-card)** - HACS Lovelace
   - Direct WebRTC to ZM's go2rtc
   - Multi-camera montage view
   - Real-time motion indicators
   - Click actions, PTZ controls

### Card Features

```yaml
type: custom:zoneminder-card
title: Security Cameras
zoneminder_go2rtc_url: http://192.168.0.45:1984  # Auto-detected from integration
monitors:
  - entity: camera.front_door
    stream_id: "1"  # Monitor ID for go2rtc
  - entity: camera.backyard
    stream_id: "2"
  - entity: camera.garage
    stream_id: "4"
columns: 2
aspect_ratio: "16:9"
streaming_mode: webrtc  # webrtc, mse, hls, mjpeg
show_motion_indicator: true
show_controls: true
```

### Card Implementation (TypeScript + Lit)

**Key Components:**

1. **WebRTC Player Component** - Handles individual stream
2. **Montage Grid** - Responsive multi-camera layout
3. **Motion Indicator Overlay** - Reads from binary_sensor entities
4. **Controls Overlay** - Quick actions (alarm, PTZ, etc.)

**Technology Stack:**
- **Lit** - Web component framework (HA standard)
- **TypeScript** - Type safety
- **Rollup** - Bundling
- **HACS** - Distribution

### Example Card Code Structure

```typescript
// src/zoneminder-card.ts
@customElement('zoneminder-card')
export class ZoneMinerCard extends LitElement {
  @property() config!: ZoneMinerCardConfig;
  @property() hass!: HomeAssistant;

  private players: Map<string, WebRTCPlayer> = new Map();

  render() {
    return html`
      <div class="grid" style="grid-template-columns: repeat(${this.config.columns}, 1fr)">
        ${this.config.monitors.map(monitor => this.renderMonitor(monitor))}
      </div>
    `;
  }

  private renderMonitor(monitor: MonitorConfig) {
    const motionEntity = this.hass.states[monitor.entity.replace('camera.', 'binary_sensor.') + '_motion'];
    const isMotion = motionEntity?.state === 'on';

    return html`
      <div class="monitor ${isMotion ? 'motion-active' : ''}">
        <webrtc-player
          .go2rtcUrl="${this.config.zoneminder_go2rtc_url}"
          .streamId="${monitor.stream_id}"
          .mode="${this.config.streaming_mode}">
        </webrtc-player>
        ${isMotion ? html`<div class="motion-indicator">Motion Detected</div>` : ''}
      </div>
    `;
  }
}

// src/webrtc-player.ts
@customElement('webrtc-player')
export class WebRTCPlayer extends LitElement {
  @property() go2rtcUrl!: string;
  @property() streamId!: string;
  @property() mode: 'webrtc' | 'mse' | 'hls' | 'mjpeg' = 'webrtc';

  private pc?: RTCPeerConnection;
  private ws?: WebSocket;

  firstUpdated() {
    if (this.mode === 'webrtc') {
      this.connectWebRTC();
    }
    // ... handle other modes
  }

  private async connectWebRTC() {
    const video = this.shadowRoot!.querySelector('video')!;

    this.pc = new RTCPeerConnection({
      iceServers: [
        {urls: ['stun:stun.cloudflare.com:3478']},
        {urls: ['stun:stun.l.google.com:19302']}
      ]
    });

    this.pc.addTransceiver('video', {direction: 'recvonly'});
    this.pc.addTransceiver('audio', {direction: 'recvonly'});

    const wsUrl = this.go2rtcUrl.replace('http', 'ws') + `/api/ws?src=${this.streamId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.pc!.onicecandidate = (ev) => {
        if (ev.candidate) {
          this.ws!.send(JSON.stringify({
            type: 'webrtc/candidate',
            value: ev.candidate.candidate
          }));
        }
      };

      this.pc!.createOffer().then(offer => {
        return this.pc!.setLocalDescription(offer);
      }).then(() => {
        this.ws!.send(JSON.stringify({
          type: 'webrtc/offer',
          value: this.pc!.localDescription!.sdp
        }));
      });
    };

    this.ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === 'webrtc/candidate') {
        this.pc!.addIceCandidate({candidate: msg.value, sdpMid: '0'});
      } else if (msg.type === 'webrtc/answer') {
        this.pc!.setRemoteDescription({type: 'answer', sdp: msg.value});
      }
    };

    this.pc.ontrack = (ev) => {
      video.srcObject = ev.streams[0];
    };
  }

  render() {
    return html`<video autoplay playsinline muted></video>`;
  }
}
```

## Integration Changes

### Update camera.py

**Remove or simplify streaming support:**

```python
class ZoneMinerCamera(CoordinatorEntity[ZoneMinerDataUpdateCoordinator], Camera):
    """Representation of a ZoneMinder camera (metadata only)."""

    # Option 1: Remove STREAM feature entirely
    _attr_supported_features = 0  # No streaming via HA

    # Option 2: Keep MJPEG fallback only
    _attr_supported_features = 0  # WebRTC handled by custom card

    async def stream_source(self) -> str | None:
        """Return MJPEG fallback for basic camera card support."""
        if self._mjpeg_url:
            return self._mjpeg_url
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return attributes including go2rtc stream info for custom card."""
        monitor = self.monitor
        if monitor is None:
            return {}

        attrs = {
            "monitor_id": monitor.id,
            "function": monitor.function,
            "width": monitor.width,
            "height": monitor.height,
            "type": monitor.type,
            # Add go2rtc info for custom card
            "go2rtc_stream_id": str(monitor.id),
            "go2rtc_available": self._go2rtc_url is not None,
        }

        # Add event info...
        return attrs
```

### Add go2rtc URL to integration data

```python
# __init__.py
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ZoneMinder from a config entry."""
    # ... existing setup ...

    # Check for go2rtc
    go2rtc_config = await api.check_go2rtc()

    # Store go2rtc URL for custom card access
    hass.data[DOMAIN][entry.entry_id]["go2rtc_url"] = (
        go2rtc_config["base_url"] if go2rtc_config else None
    )
```

## Deployment Strategy

### Phase 1: Update Integration
1. Modify [camera.py](custom_components/zoneminder/camera.py) to remove/simplify streaming
2. Add go2rtc URL to integration data
3. Update attributes to include go2rtc stream info
4. Test MJPEG fallback still works

### Phase 2: Create Custom Card
1. Initialize TypeScript + Lit project
2. Implement WebRTCPlayer component
3. Implement montage grid layout
4. Add motion indicators
5. Add controls overlay

### Phase 3: HACS Publication
1. Create separate repository: `zoneminder-card`
2. Configure HACS metadata
3. Add documentation and screenshots
4. Publish to HACS

### Phase 4: Testing
1. Test with multiple monitors
2. Test motion indicators
3. Test fallback modes (MSE, HLS, MJPEG)
4. Test mobile browsers
5. Test HA mobile app

## Browser Compatibility

### WebRTC Support
- ✅ **Chrome/Edge**: Full WebRTC support (H.264, H.265 via MSE fallback)
- ✅ **Firefox**: Full WebRTC support (H.264, OPUS)
- ✅ **Safari**: WebRTC support (H.264, H.265 native)
- ✅ **Mobile Safari**: Full support
- ✅ **Chrome Android**: Full support

### Fallback Modes
- **MSE**: Chrome, Firefox, Safari (Mac/iPad)
- **HLS**: Safari (all), Chrome Android
- **MJPEG**: All browsers (least efficient)

## Security Considerations

### Network Access
- go2rtc must be accessible from client browser
- Consider using reverse proxy (Nginx) with HTTPS
- Use Home Assistant ingress for external access

### Authentication
- go2rtc doesn't have built-in auth
- Rely on network security (VPN, firewall)
- Or add auth via reverse proxy

### Example Nginx Config
```nginx
location /zm-go2rtc/ {
    proxy_pass http://192.168.0.45:1984/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

## Performance Considerations

### Bandwidth
- **WebRTC**: ~1-5 Mbps per stream (H.264)
- **MSE**: ~1-5 Mbps per stream
- **HLS**: ~1-5 Mbps per stream (buffering)
- **MJPEG**: ~5-20 Mbps per stream (inefficient)

### CPU Usage (Client-Side)
- **WebRTC**: Low (hardware decode)
- **MSE**: Low (hardware decode)
- **HLS**: Low (hardware decode)
- **MJPEG**: Medium (software decode)

### Latency
- **WebRTC**: <1 second
- **MSE**: 1-3 seconds
- **HLS**: 3-10 seconds
- **MJPEG**: <1 second (no buffering)

## Testing Checklist

- [ ] WebRTC connection establishes
- [ ] Video plays smoothly
- [ ] Audio works (if camera has audio)
- [ ] Motion indicators update in real-time
- [ ] Multiple cameras display in grid
- [ ] Fallback modes work (MSE, HLS, MJPEG)
- [ ] Works on Chrome desktop
- [ ] Works on Firefox desktop
- [ ] Works on Safari Mac
- [ ] Works on Safari iOS
- [ ] Works on Chrome Android
- [ ] Works in HA mobile app
- [ ] ICE candidates exchange properly
- [ ] Reconnection works after network drop
- [ ] Card configuration UI works
- [ ] go2rtc URL auto-detected from integration

## Next Steps

1. **Validate approach** with user
2. **Prototype** WebRTCPlayer component
3. **Test** with real ZM instance
4. **Design** card UI/UX
5. **Implement** full montage card
6. **Document** setup instructions
7. **Publish** to HACS

## References

- [go2rtc Documentation](https://github.com/AlexxIT/go2rtc)
- [WebRTC API](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API)
- [Lit Framework](https://lit.dev)
- [HACS Documentation](https://hacs.xyz)
- [Home Assistant Frontend Development](https://developers.home-assistant.io/docs/frontend/)
