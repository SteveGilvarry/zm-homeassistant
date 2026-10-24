# README screenshots

`take.py` regenerates the images in `docs/images/` from a running Home
Assistant, so they can be refreshed whenever the UI changes.

## What's real and what's staged

Every interface element is the real Home Assistant frontend or the real
`zoneminder-card`, rendered by the code in this repo. Nothing is drawn,
painted over or generated. What's staged is the content, so that no real
camera, name or address appears:

- **The card** (`card.jpg`) is the real card given four made-up cameras and a
  generated day of events (`demo.js`). Its pictures are stock photos.
- **The device page** (`device.png`) is a real camera's page. In the browser
  only, its name becomes "Driveway", the server's address becomes
  `homeserver`, its thumbnail is swapped for a stock photo, and the cards
  that aren't shown are hidden.
- **The setup dialog** (`setup.png`) is shown as is, then closed without
  being submitted.

The stock photos are public domain or CC0, from Wikimedia Commons. They're
listed in `frames/SOURCES.md`, and `make_frames.py` rebuilds them. It crops
each to 16:9 and adds a ZoneMinder-style name and time label in the corner.

## Regenerating

You need Home Assistant running with this integration set up and at least one
ZoneMinder camera that isn't rotated, plus Google Chrome.

1. In Home Assistant, open your profile > Security and create a long-lived
   access token.
2. Put it in `.env` at the repo root (git ignores that file):

   ```
   HA_TOKEN=your-token
   ```

3. Run:

   ```bash
   pip install playwright
   python docs/screenshots/take.py
   ```

Options: `--url` (default `http://localhost:8123`), `--dashboard` (the
dashboard view the card is drawn over, whose title shows above it; default
`/zm-cameras/all`) and `--headed` to watch it work.

Images are taken at twice screen resolution at 1440×900, in the dark theme.
