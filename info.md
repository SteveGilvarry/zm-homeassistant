# ZoneMinder Card

Custom Lovelace card for ZoneMinder with direct go2rtc WebRTC streaming.

## Features

- ⚡ Ultra-low latency WebRTC streaming (<1 second)
- 🎥 Multi-camera montage view
- 🚨 Real-time motion indicators
- 📱 Mobile-friendly responsive design
- 🎯 Multiple streaming modes (WebRTC, MSE, HLS, MJPEG)

## Prerequisites

**Required**: [ZoneMinder Integration (ZMHA)](https://github.com/yourusername/zmha)

Install the ZMHA integration via HACS first to provide camera entities and go2rtc configuration.

## Quick Start

```yaml
type: custom:zoneminder-card
title: Security Cameras
monitors:
  - entity: camera.front_door
  - entity: camera.backyard
columns: 2
```

For detailed documentation, see the [README](https://github.com/yourusername/zoneminder-card).
