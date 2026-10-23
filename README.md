# ZoneMinder card

A Lovelace card for the ZoneMinder integration in [zmha](https://github.com/stevengilvarry/zmha). Each camera shows its live view, with a strip underneath covering the last 24 hours:

- Blue bands are when the camera was recording. Gaps mean it wasn't.
- Amber marks are motion. Taller marks mean a higher alarm score.
- Hover the strip to see a frame from that moment. Click to play from there. Clips play on into the next one, at 1×, 4× or 16×.
- Cameras that ZoneMinder rotates are shown upright. Sideways cameras get tall tiles.
- Cameras that can pan and tilt show a direction pad when you hover over them.

The card talks only to Home Assistant. Live video uses Home Assistant's camera stream, and recordings and thumbnails come through the integration's media proxy. The browser never needs a ZoneMinder login and never connects to ZoneMinder directly, so the card works away from home too.

## Install

Nothing to do: the ZoneMinder integration ships this card and loads it on every
dashboard. Add `type: custom:zoneminder-card` to a dashboard and it's there.

To work on the card, build it and copy it into the integration:

```bash
npm install
npm run ship   # builds, then copies to ../zmha/custom_components/zoneminder/www/
```

If an older setup also lists `/local/zoneminder-card.js` as a dashboard resource, remove
that resource. The card won't load twice, but the copy in `/local` will go stale.

## Configure

```yaml
type: custom:zoneminder-card
```

That shows every ZoneMinder camera. Options:

| Option | Default | What it does |
|---|---|---|
| `entities` | all ZoneMinder cameras | Cameras to show, as entity ids or `{entity, name}` |
| `columns` | fits the width | Fixed number of columns |
| `hours` | 24 | How far back the strip goes, 1 to 168 |
| `ptz` | true | Show the pan and tilt pad on cameras that support it |

## Keyboard

Tab to a strip, then:
- Left and Right arrows move one minute (hold Shift for ten).
- Home and End jump to the start and to now.
- Enter plays from the selected moment.
- Escape goes back to live.
