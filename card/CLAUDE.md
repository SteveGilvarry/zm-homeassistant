# CLAUDE.md

Lovelace card for the ZoneMinder integration in the parent folder. Lit + TypeScript, bundled by rollup into `dist/zoneminder-card.js`. `npm run ship` copies the build to `../custom_components/zoneminder/www/`; commit that file with the source change, because HACS installs it as-is.

## Rules

- Talk only to Home Assistant. No direct ZoneMinder, zm-api or go2rtc URLs, and no ZoneMinder credentials in the browser.
- Live video: HA's `ha-camera-stream` element (loaded lazily via `loadCardHelpers`).
- History: the integration's `zoneminder/events` websocket command. Clip and thumbnail URLs it returns go through the integration's media proxy.
- Rotation: live video arrives unrotated and the card turns it by `orientation_degrees`. Snapshots, thumbnails and recorded clips come from ZoneMinder already upright, so don't rotate them.

## Build and deploy to the dev HA

```bash
npm run ship
docker restart zmha-homeassistant   # only needed the first time; after that a hard refresh
```

The integration serves the card at `/zoneminder_static/zoneminder-card.js` and loads it on every dashboard, so there is no Lovelace resource. The dev dashboard is `/zm-cameras`.

## Design

Tokens are on `:host` in `src/zoneminder-card.ts`: asphalt `#182026`, kerb `#232C33`, concrete `#7E8890`, fog `#E3E7E9`, tape `#3E6E8C` (recorded time), sodium `#F0A23B` (motion and playhead only). Type is Barlow Semi Condensed. The strip is the one bold element; keep everything else quiet.
