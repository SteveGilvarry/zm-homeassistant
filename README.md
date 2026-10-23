# ZoneMinder for Home Assistant

A Home Assistant integration for [ZoneMinder](https://zoneminder.com/): live cameras,
recordings you can browse and play, real-time motion, monitor controls and PTZ, all set
up from the UI.

[![HACS Custom][hacs-badge]][hacs]
[![Validate][validate-badge]][validate-workflow]
[![Tests][test-badge]][test-workflow]
[![License: AGPL v3][license-badge]][license]

## What you get

- **Live cameras.** One camera entity per monitor. Video is fetched through Home
  Assistant, so it works in every standard card without exposing a ZoneMinder token.
- **Recordings in the media browser.** Every event shows up under Media > ZoneMinder,
  organised by camera and day, with thumbnails. Play them in the browser or cast them.
- **Motion that means motion.** A `binary_sensor` per monitor, updated in under a second
  over MQTT. Continuous recording no longer registers as motion.
- **Event entities.** An `event` entity per monitor for automations, carrying the event
  id, cause and any object labels from zmeventnotification.
- **Real monitor controls.** ZoneMinder 1.37 split the old Function dropdown into
  Capturing, Analysing and Recording, so you get one `select` for each.
- **NVR-level sensors.** Storage used, events today, capture rate, capture bandwidth,
  camera connection state, daemon health and version, on a ZoneMinder server device that
  the cameras hang off.
- **PTZ.** Pan, tilt, zoom, focus, home and stored presets, through the `zoneminder.ptz`
  service. Buttons appear only on monitors ZoneMinder can actually control.
- **A notification blueprint.** Motion, snapshot, phone. Import it and you are done.

## Requirements

- Home Assistant 2024.1 or newer
- Either a [zm-api](https://github.com/SteveGilvarry/zm-api) server (recommended) or
  ZoneMinder 1.36+ with its built-in API enabled
- An MQTT broker configured in Home Assistant, for sub-second motion
- An internal Home Assistant URL set under Settings > System > Network, so live video can
  be proxied

## Installation

### HACS

1. HACS > Integrations > three-dot menu > Custom repositories
2. Add `https://github.com/stevengilvarry/zmha` with category **Integration**
3. Install **ZoneMinder**, then restart Home Assistant

### Manual

```bash
cd /config
git clone https://github.com/stevengilvarry/zmha
cp -r zmha/custom_components/zoneminder custom_components/zoneminder
```

Then restart Home Assistant.

### Adding the integration

**Settings > Devices & Services > Add Integration > ZoneMinder**, then fill in:

- **API** — zm-api or ZoneMinder's built-in API
- **Server URL** — `http://192.168.1.10:8080` for zm-api, or `http://192.168.1.10/zm`
  for the built-in one
- **Username and password**
- **Use MQTT for real-time events**

## Choosing an API

|                | zm-api (default)                       | Built-in API                        |
| -------------- | -------------------------------------- | ----------------------------------- |
| Talks to       | [zm-api](https://github.com/SteveGilvarry/zm-api) at `/api/v3` | ZoneMinder's CakePHP API at `/zm/api` |
| Auth           | JWT bearer, refreshed automatically    | Query-parameter token               |
| Default port   | 8080                                   | your ZoneMinder web port            |
| Live video     | HLS through the Home Assistant proxy   | go2rtc RTSP, or MJPEG stills        |
| Recordings     | Yes, in the media browser              | Not yet                             |
| Server sensors | Storage, daemons, capture stats        | Version only                        |
| Status         | zm-api is alpha                        | Stable                              |

zm-api gives you recordings, storage and capture statistics that ZoneMinder's built-in
API does not expose. Pick the built-in API if you run a stock install and want to stay
that way.

## Real-time events (MQTT)

Turn on MQTT in ZoneMinder under **Options > MQTT**:

```
ZM_MQTT_HOSTNAME:  your-broker
ZM_MQTT_PORT:      1883
```

Then enable MQTT on each monitor, under its **MQTT** tab. This last step is easy to
miss, and without it ZoneMinder never publishes anything. The integration raises a
repair issue when it notices nothing is publishing.

The topic prefix is read from ZoneMinder's own `ZM_MQTT_TOPIC_PREFIX` setting, so you do
not have to match its capitalisation by hand. Override it in the integration's options if
your broker is set up differently.

With MQTT the integration polls every 5 minutes and reacts to events instantly. Without
it, polling drops to every 30 seconds and motion is only as fresh as the last poll.

## Motion, and why continuous recording is not motion

ZoneMinder opens an event whenever it records, whether or not anything moved. If a
monitor is set to record continuously, there is always an event in progress. Motion
sensors key on events with alarmed frames instead, and ignore MQTT notifications from
monitors that are not analysing.

If a motion sensor never turns on, check that the monitor's **Analysing** select is set
to `Always`. A monitor that only captures and records cannot detect anything.

## Live video

For the zm-api backend, Home Assistant fetches the HLS stream through a proxy the
integration registers at `/api/zoneminder/...`. zm-api requires a bearer token on the
playlist and on every segment, and ffmpeg drops query strings when it resolves relative
segment URIs, so the token has to be added server side. The proxy is restricted to
media paths and is guarded by a per-session secret.

This is why an internal URL must be set: the proxy needs to know its own address.

### WebRTC

zm-api has native WebRTC at `/api/v3/live/{monitor}/webrtc/ws`, and each camera entity
publishes that URL as a `webrtc_signaling_url` attribute. A browser can answer zm-api's
SDP offer directly, which is what the companion
[ZoneMinder Card](https://github.com/stevengilvarry/zoneminder-card) uses for sub-second
video.

Home Assistant's own WebRTC support cannot be wired to it yet. Core expects the
integration to *answer* an offer that the frontend makes, while zm-api sends its own
offer as soon as the socket opens. Both want to be the offerer. If zm-api gains support
for a client-initiated offer, wiring it up here is a small change.

### go2rtc, on the built-in API

Set `ZM_GO2RTC_PATH` in ZoneMinder's options. The integration reads the stream list from
go2rtc and matches monitors to it, rather than guessing that stream names match monitor
ids, and it checks whether go2rtc's RTSP server is actually running before handing Home
Assistant an `rtsp://` URL. When RTSP is switched off, cameras fall back to stills.

## Recordings

Recordings appear under **Media > ZoneMinder**, by server, camera and day. Playback goes
through the same proxy, so no ZoneMinder credentials reach the browser.

## Services

| Service                        | What it does                                            |
| ------------------------------ | ------------------------------------------------------- |
| `zoneminder.trigger_event`     | Forces a monitor into alarm, starting a recording       |
| `zoneminder.cancel_event`      | Clears a forced alarm                                   |
| `zoneminder.ptz`               | Pan, tilt, zoom, focus, home or go to a preset          |
| `zoneminder.set_monitor_state` | Changes capturing, analysing, recording or decoding     |

## Notification blueprint

Import `blueprints/automation/zoneminder/motion_notification.yaml`, or copy it into
`config/blueprints/automation/zoneminder/`. Pick a motion sensor, a camera and a notify
service, and motion gets you a phone notification with a snapshot.

## Troubleshooting

Download diagnostics from the integration's page first. Passwords, tokens and the
credentials embedded in camera RTSP URLs are stripped out, so it is safe to attach to an
issue.

| Symptom                        | Likely cause                                                     |
| ------------------------------ | ---------------------------------------------------------------- |
| Motion never turns on          | The monitor's Analysing is `None`                                |
| Motion is slow                 | MQTT is off in ZoneMinder, or not enabled on the monitor         |
| Cameras show but do not play   | No internal URL set under Settings > System > Network            |
| No recordings in Media         | The built-in API backend, which does not serve them              |
| Device links go nowhere        | Set the ZoneMinder web address in the integration's options      |

## Development

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements_test.txt av PyTurboJPEG ha-ffmpeg
pytest
ruff check custom_components/zoneminder tests
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for the local ZoneMinder and MQTT setup,
and [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).

[hacs]: https://github.com/hacs/integration
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[validate-workflow]: https://github.com/stevengilvarry/zmha/actions/workflows/validate.yaml
[validate-badge]: https://github.com/stevengilvarry/zmha/actions/workflows/validate.yaml/badge.svg
[test-workflow]: https://github.com/stevengilvarry/zmha/actions/workflows/test.yaml
[test-badge]: https://github.com/stevengilvarry/zmha/actions/workflows/test.yaml/badge.svg
[license]: LICENSE
[license-badge]: https://img.shields.io/badge/License-AGPL%20v3-blue.svg
