# Building ZoneMinder Card

This document describes how to build and deploy the ZoneMinder Card for development and production.

## Prerequisites

- Node.js 18+ and npm
- Git

## Initial Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/zoneminder-card.git
cd zoneminder-card

# Install dependencies
npm install
```

## Development

### Development Server

Start the development server with hot reload:

```bash
npm run dev
```

This will:
- Build the card
- Start a local server on `http://localhost:5000`
- Watch for file changes and rebuild automatically

### Add to Home Assistant (Development)

1. In Home Assistant, go to Settings → Dashboards → Resources
2. Add a new resource:
   ```yaml
   url: http://localhost:5000/zoneminder-card.js
   type: module
   ```
3. Add the card to a dashboard:
   ```yaml
   type: custom:zoneminder-card
   monitors:
     - entity: camera.front_door
   ```

**Note**: Your browser must be able to access `localhost:5000`. If running HA in Docker or remote, you may need to use your computer's IP address instead.

## Building for Production

### Build

```bash
npm run build
```

This creates a production build in the `dist/` directory with:
- Minified JavaScript
- Source maps removed
- Optimized for size

### Build Output

```
dist/
├── zoneminder-card.js    # Main bundle (use this)
└── zoneminder-card.d.ts  # TypeScript definitions
```

## Testing the Production Build

### Local Testing

After building, you can test locally:

1. Copy `dist/zoneminder-card.js` to your HA `config/www/` directory
2. Update your Lovelace resource:
   ```yaml
   url: /local/zoneminder-card.js
   type: module
   ```
3. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
4. Reload the dashboard

### Docker Testing

If running HA in Docker:

```bash
# Copy to HA config directory
docker cp dist/zoneminder-card.js homeassistant:/config/www/

# Or mount as volume in docker-compose.yml:
volumes:
  - ./dist:/config/www/zoneminder-card:ro
```

## Code Quality

### Linting

```bash
npm run lint
```

Checks TypeScript code for errors and style issues.

### Formatting

```bash
npm run format
```

Formats all TypeScript files using Prettier.

### Pre-commit Checks

Before committing, run:

```bash
npm run lint
npm run format
npm run build
```

## Publishing to HACS

### Prerequisites

1. Create a GitHub repository
2. Ensure `hacs.json` is configured correctly
3. Tag a release

### Steps

1. **Prepare the release**:
   ```bash
   npm run build
   git add dist/
   git commit -m "Build v0.1.0"
   git tag v0.1.0
   git push origin v0.1.0
   ```

2. **Create GitHub Release**:
   - Go to GitHub → Releases → Create new release
   - Choose tag `v0.1.0`
   - Title: `v0.1.0 - Initial Release`
   - Description: Release notes
   - Attach `dist/zoneminder-card.js` as asset
   - Publish

3. **Submit to HACS**:
   - Fork [hacs/default](https://github.com/hacs/default)
   - Add your repository to `plugins` category
   - Create pull request
   - Wait for approval

### Release Checklist

- [ ] Version bumped in `package.json`
- [ ] CHANGELOG.md updated
- [ ] Code linted and formatted
- [ ] Production build created
- [ ] Git tag created
- [ ] GitHub release published
- [ ] Release notes written
- [ ] HACS PR submitted (for new repos)

## Versioning

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Example:
```bash
npm version patch  # 0.1.0 → 0.1.1
npm version minor  # 0.1.1 → 0.2.0
npm version major  # 0.2.0 → 1.0.0
```

## Troubleshooting

### Build Fails

**Error: Module not found**
```bash
rm -rf node_modules package-lock.json
npm install
```

**TypeScript errors**
```bash
npm run lint
# Fix errors, then rebuild
```

### Development Server Issues

**Port 5000 already in use**
```bash
# Edit rollup.config.mjs and change port
# Or kill the process:
lsof -ti:5000 | xargs kill
```

**Card not loading in HA**
- Check browser console for errors
- Verify URL is accessible
- Clear browser cache
- Check CORS if accessing from different origin

### Hot Reload Not Working

The dev server should auto-reload when you save files. If not:
- Restart the dev server
- Check file watch limits on Linux:
  ```bash
  echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
  sudo sysctl -p
  ```

## Project Structure

```
zoneminder-card/
├── src/
│   ├── zoneminder-card.ts      # Main card component
│   ├── webrtc-player.ts        # WebRTC player component
│   └── types.ts                # TypeScript definitions
├── dist/                       # Build output (gitignored)
├── node_modules/               # Dependencies (gitignored)
├── package.json                # NPM configuration
├── tsconfig.json              # TypeScript configuration
├── rollup.config.mjs          # Rollup build configuration
├── hacs.json                  # HACS metadata
├── README.md                  # User documentation
├── BUILDING.md                # This file
└── LICENSE                    # MIT License
```

## Dependencies

### Runtime
- **lit**: 3.x - Web component framework

### Development
- **rollup**: 4.x - Bundler
- **typescript**: 5.x - TypeScript compiler
- **@rollup/plugin-***: Rollup plugins
- **eslint**: 8.x - Linter
- **prettier**: 3.x - Code formatter

## Further Reading

- [Lit Documentation](https://lit.dev)
- [Home Assistant Frontend Development](https://developers.home-assistant.io/docs/frontend/)
- [HACS Documentation](https://hacs.xyz)
- [Rollup Documentation](https://rollupjs.org)
