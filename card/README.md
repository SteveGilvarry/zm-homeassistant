# ZoneMinder card

Source for the dashboard card the integration ships. How to use it is in the
[main README](../README.md#card).

The card is Lit and TypeScript, bundled by rollup into one file. The integration serves
that file from `custom_components/zoneminder/www/` and loads it on every dashboard, so
users never build anything. The built file is committed for that reason.

## Building

```bash
cd card
npm install
npm run ship   # builds, then copies into ../custom_components/zoneminder/www/
```

Commit the copied `zoneminder-card.js` along with the source change.

On the dev Home Assistant, a hard refresh picks up the new build. The integration
adds a version to the URL, so after bumping the integration's version you'll also
need `docker restart zmha-homeassistant`.

## How it works

The card talks only to Home Assistant. It never connects to ZoneMinder or sees a
ZoneMinder login, so it works away from home too.

- Live video uses Home Assistant's own camera stream: WebRTC where the integration
  offers it, HLS otherwise.
- The strip comes from the integration's `zoneminder/events` websocket command.
  Thumbnails and clips go through the integration's media proxy.
