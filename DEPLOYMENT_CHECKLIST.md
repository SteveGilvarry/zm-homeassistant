# Deployment Checklist

Use this checklist when deploying the ZoneMinder Card to production.

## Pre-Deployment

### Code Quality
- [ ] All TypeScript files compile without errors
- [ ] ESLint passes: `npm run lint`
- [ ] Code formatted: `npm run format`
- [ ] No console.log statements in production code
- [ ] All TODOs resolved or documented

### Testing
- [ ] Tested WebRTC streaming with real cameras
- [ ] Tested motion indicators with MQTT events
- [ ] Tested on Chrome desktop
- [ ] Tested on Firefox desktop
- [ ] Tested on Safari (Mac or iOS)
- [ ] Tested on mobile browsers
- [ ] Tested in HA mobile app
- [ ] Tested with 1, 2, and 4+ cameras
- [ ] Tested fallback modes (MSE, HLS, MJPEG)
- [ ] Tested reconnection after network drop

### Documentation
- [ ] README.md complete and accurate
- [ ] Example configurations tested
- [ ] BUILDING.md has correct instructions
- [ ] QUICKSTART.md verified
- [ ] All screenshots/demos current
- [ ] Changelog updated

## Building for Release

### Version
- [ ] Version bumped in package.json
- [ ] Version matches git tag
- [ ] Breaking changes documented

### Build
```bash
npm run build
```
- [ ] Build completes without errors
- [ ] Output file exists: `dist/zoneminder-card.js`
- [ ] File size reasonable (<100KB ideally)
- [ ] No source maps in production build

### Git
```bash
git status
```
- [ ] All changes committed
- [ ] No uncommitted files
- [ ] .gitignore configured correctly
- [ ] dist/ in .gitignore (unless you commit builds)

## GitHub Release

### Repository Setup
- [ ] Repository created on GitHub
- [ ] README.md displays correctly
- [ ] License file present (MIT)
- [ ] .gitignore configured
- [ ] Repository description set
- [ ] Topics/tags added (home-assistant, lovelace, zoneminder, webrtc)

### Create Release
```bash
git tag v0.1.0
git push origin v0.1.0
```
- [ ] Tag created
- [ ] Tag pushed to GitHub
- [ ] Release created on GitHub
- [ ] Release notes written
- [ ] `dist/zoneminder-card.js` attached to release
- [ ] Installation instructions in release notes

### Release Notes Template
```markdown
## v0.1.0 - Initial Release

### Features
- Direct WebRTC streaming from ZoneMinder's go2rtc
- Multi-camera montage grid view
- Real-time motion indicators
- Multiple streaming modes (WebRTC, MSE, HLS, MJPEG)
- Customizable layout and appearance

### Installation
See [README.md](README.md) for installation instructions.

### Requirements
- Home Assistant 2024.1+
- ZoneMinder 1.37+ with go2rtc
- zmha integration

### Breaking Changes
None (initial release)

### Known Issues
None
```

## HACS Submission

### HACS Requirements
- [ ] Repository is public
- [ ] hacs.json file present and valid
- [ ] README.md present
- [ ] LICENSE file present
- [ ] At least one release with attached JS file
- [ ] Repository follows HACS naming convention

### HACS Validation
Test locally before submitting:
```bash
# Clone HACS validator
git clone https://github.com/hacs/integration.git
cd integration
python3 -m pytest tests/validate/test_plugin.py -k test_plugin_repository
```

### Submit to HACS
- [ ] Fork hacs/default repository
- [ ] Add to plugins category:
  ```json
  {
    "name": "ZoneMinder Card",
    "description": "Display ZoneMinder cameras with direct go2rtc WebRTC streaming",
    "repository": "yourusername/zoneminder-card"
  }
  ```
- [ ] Create pull request
- [ ] Respond to review comments
- [ ] Approved and merged

## Post-Deployment

### Monitoring
- [ ] Watch for GitHub issues
- [ ] Monitor HACS installation stats
- [ ] Check for bug reports

### Communication
- [ ] Announce in Home Assistant community
- [ ] Post in ZoneMinder forums
- [ ] Update zmha integration README with card link

### Maintenance
- [ ] Plan for future features
- [ ] Set up issue templates
- [ ] Consider contributing guidelines

## Rollback Plan

If issues are discovered after release:

### Minor Issues
- [ ] Document in known issues
- [ ] Plan fix for next patch release
- [ ] Provide workaround if possible

### Critical Issues
- [ ] Create hotfix branch
- [ ] Fix issue
- [ ] Release patch version ASAP
- [ ] Update HACS release

## Version History

### v0.1.0 - Initial Release
- Date: ___________
- Deployed by: ___________
- Issues: ___________

## Notes

Add any deployment-specific notes here:

---
