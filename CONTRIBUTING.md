# Contributing to ZoneMinder for Home Assistant

Thanks for your interest in improving this integration! Contributions of all
kinds are welcome — bug reports, fixes, docs, and features.

## Getting started

```bash
git clone https://github.com/stevengilvarry/zmha
cd zmha
./scripts/setup_dev.sh          # create a virtualenv and install dependencies
```

A Docker test stack (Home Assistant + Mosquitto) is provided:

```bash
docker compose up -d            # HA available at http://localhost:8123
```

The integration source lives in `custom_components/zoneminder/`. Backend clients
are in `custom_components/zoneminder/client/`:

- `base.py` — the `ZoneMinderClient` contract every backend implements
- `legacy.py` — ZoneMinder's built-in CakePHP API
- `v3.py` — the standalone [`zm-api`](https://github.com/SteveGilvarry/zm-api) v3 REST server

Anything that the rest of the integration relies on should be part of the
`ZoneMinderClient` contract so both backends stay interchangeable.

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
