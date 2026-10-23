# ZoneMinder integration: status and plan

Last updated 2026-08-23, against ZoneMinder 1.39.22 and zm-api 3.0.0-alpha.1.

## Where this stands

The integration talks to zm-api by default and to ZoneMinder's built-in API as a
fallback. Both go through one client interface, so the platforms never know which is in
use.

| Area                        | State    | Notes                                                        |
| --------------------------- | -------- | ------------------------------------------------------------ |
| zm-api v3 client            | Done     | JWT with refresh, paginated collections, typed models         |
| Built-in API client         | Done     | go2rtc discovery fixed, split state fields written            |
| Config, options, reauth     | Done     | Plus a reconfigure flow                                       |
| Coordinator                 | Done     | One bulk events request, not one per monitor                  |
| Cameras                     | Done     | HLS through the media proxy                                   |
| Motion binary sensors       | Done     | Alarm-frame based, with an MQTT timeout                       |
| Event entities              | Done     | Motion and recording, with object labels                      |
| Selects                     | Done     | Capturing, analysing, recording, decoding                     |
| Sensors                     | Done     | Per monitor and per server                                    |
| Buttons and PTZ             | Done     | Only on controllable monitors                                 |
| Services                    | Done     | Device and entity targeting, errors surface in the UI         |
| Media source                | Done     | Browse by camera and day, play through the proxy              |
| Diagnostics                 | Done     | Redacts credentials, including RTSP passwords                 |
| Repairs                     | Done     | Warns when ZoneMinder is not publishing over MQTT             |
| Tests                       | Done     | 110 tests, 85% coverage                                       |
| Notification blueprint      | Done     | Motion to phone with a snapshot                               |
| Native Home Assistant WebRTC| Blocked  | See below                                                     |
| Object detection sensors    | Not done | MQTT labels are parsed but not yet their own entities         |
| Timeline card               | Done     | Source in `card/`, served by the integration                  |

## What was verified against a live server

Run against ZoneMinder 1.39.22 at 192.168.0.45:8080, four monitors:

- Authentication, token refresh, and every collection endpoint the integration reads
- Monitor state parsing, including the fields the server's own `function` disagrees with
- One `/monitor-status` call covering every monitor's capture rate and bandwidth
- Live HLS played end to end through the proxy, confirmed with `ffprobe`: master
  playlist, child playlist, init segment and media segments, all authenticated
- The proxy allowlist refusing `api/v3/users` and `api/v3/configs`
- Event thumbnails and ranged video requests
- The MQTT topic prefix read from ZoneMinder's own configuration

## Native WebRTC is blocked on zm-api

Home Assistant's camera WebRTC API hands the integration an SDP offer created by the
frontend and expects an answer back. zm-api sends *its* offer as soon as the signalling
socket opens and expects the client to answer. There is no client-offer message in its
protocol, so neither side can answer the other.

Three ways forward, in order of preference:

1. zm-api accepts a client-initiated offer. Then
   `Camera.async_handle_async_webrtc_offer` can pass the frontend's offer straight
   through, and this becomes roughly forty lines here.
2. The companion card keeps doing it. A browser can answer zm-api's offer, and the
   camera entity already publishes `webrtc_signaling_url` for exactly this.
3. Bridge in Python with aiortc. Rejected: a heavy dependency, and Home Assistant would
   be decoding and re-encoding video it does not need to touch.

Until then, live view uses HLS through the proxy, which works in every stock card.

## Next

**Object detection entities.** `mqtt.py` already parses detection labels out of
zmeventnotification payloads and exposes them on the motion sensor and event entity.
Turning them into per-label binary sensors or a `detected object` sensor is the change
that would make this feel like Frigate for people already running the ML hooks.

**Zones.** zm-api exposes `/monitors/{id}/zones`. Per-zone motion sensors would let
automations distinguish the driveway from the street.

**Groups.** `/groups` and `/groups-monitors` could drive Home Assistant areas or entity
grouping instead of making people rebuild the same structure by hand.

**Quality scale.** The manifest claims bronze. Silver needs the coverage above 95% and a
documented log-when-unavailable policy; gold needs discovery, translations beyond
English and device triggers.

## Notes for whoever picks this up

- ZoneMinder 1.37 replaced `Function` with `Capturing`, `Analysing` and `Recording`. The
  server still reports a `function` field, and on 1.39.22 it disagrees with the three
  real fields, so `Monitor.function` is derived rather than read.
- Continuous recording opens an event roughly every ten minutes with zero alarm frames.
  Anything that treats an open event as motion will be wrong on those monitors.
- zm-api will not materialise a live playlist until `POST /live/{id}/start` has been
  called, and the session needs re-arming periodically.
- go2rtc stream names are not monitor ids. On the test server monitor 3 is published as
  `3`, `3_h264` and `3_ZoneMinderPrimary`, while monitor 1 is only `1_0`.
