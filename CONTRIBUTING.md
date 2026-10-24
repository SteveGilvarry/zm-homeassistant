# Contributing to ZoneMinder for Home Assistant

Thanks for your interest in improving this integration! Contributions of all
kinds are welcome — bug reports, fixes, docs, and features.

## Getting started

```bash
git clone https://github.com/SteveGilvarry/zm-homeassistant
cd zm-homeassistant
./scripts/setup_dev.sh          # create a virtualenv and install dependencies
```

A Docker test stack (Home Assistant + Mosquitto) is provided:

```bash
docker compose up -d            # HA available at http://localhost:8123
```

The integration source lives in `custom_components/zoneminder/`. Talking to
ZoneMinder is done by [aiozoneminder](https://github.com/SteveGilvarry/aiozoneminder),
a separate library with one client per API: API v3
([zm-api](https://github.com/SteveGilvarry/zm-api)) and the built-in API v2.
Changes to how ZoneMinder is called belong there. This repo holds the Home
Assistant side: entities, the config flow, the media proxy and so on.

To work on both at once, check aiozoneminder out next to this repo and install
it in editable mode:

```bash
pip install -e ../aiozoneminder
```

## Code style

This project follows Home Assistant Core conventions:

- Fully async (`aiohttp`), type-hinted code
- Formatted and linted with [Ruff](https://docs.astral.sh/ruff/)

Before opening a PR:

```bash
ruff check custom_components/zoneminder
ruff format --check custom_components/zoneminder
```

CI also runs Home Assistant's `hassfest` and HACS validation.

## Pull requests

1. Branch off `main`.
2. Keep changes focused; update `README.md`/`docs/` and translations
   (`strings.json` + `translations/en.json`) when behavior or config changes.
3. Bump `version` in `manifest.json` for user-facing releases.
4. Describe what you changed and how you tested it (which backend, ZM version).

## Reporting bugs

Open an issue with your Home Assistant version, ZoneMinder (or zm-api) version,
the backend you selected, and relevant logs (`Settings → System → Logs`, filtered
for `zoneminder`).

## License

By contributing, you agree that your contributions are licensed under the
project's **AGPL-3.0-or-later** license.
