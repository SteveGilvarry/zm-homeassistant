# Linking ZMHA Integration with ZoneMinder Card

This document explains how the **ZMHA integration** and **ZoneMinder Card** work together and how users will discover and install both.

## Architecture Overview

### Two-Component System

**Component 1: ZMHA Integration** (HACS Integration)
- Provides camera entities
- Provides binary motion sensors
- MQTT real-time events
- Auto-detects go2rtc configuration
- Works independently without the card

**Component 2: ZoneMinder Card** (HACS Lovelace)
- Custom Lovelace card for enhanced viewing
- Direct WebRTC streaming
- Multi-camera montage
- Real-time motion indicators
- **Optional** - users can use standard camera cards instead

### Why Not a Hard Requirement?

HACS does **not support hard dependencies** between integrations and Lovelace cards. This is by design:

1. **Flexibility**: Users may prefer different viewing methods
2. **Compatibility**: Standard camera cards still work fine
3. **Progressive Enhancement**: Card provides enhanced experience, not required functionality

## How Users Discover the Card

### 1. Post-Installation Notification

When the integration is first installed, users see a persistent notification:

```
ZoneMinder integration is now set up! 🎉

💡 Tip: For the best camera viewing experience with ultra-low latency
WebRTC streaming, install the companion ZoneMinder Card via HACS → Frontend.

The integration works great with standard camera cards too!
```

**Implementation**: [__init__.py:66-76](custom_components/zoneminder/__init__.py#L66-L76)

### 2. README Prominence

The integration README has **three mentions**:

1. **Top callout box** (most prominent)
   ```markdown
   > 💡 Enhanced Viewing Experience: For the best camera viewing
   > experience with ultra-low latency WebRTC streaming, install
   > the companion ZoneMinder Card
   ```

2. **Companion Card section** in features list

3. **Dedicated section** after installation with install instructions

**File**: [README.md](README.md)

### 3. GitHub Issue Template

When users open an issue, they see a link to the card:

```yaml
contact_links:
  - name: 🎨 ZoneMinder Card (Enhanced Viewing)
    url: https://github.com/yourusername/zoneminder-card
    about: For the best camera viewing experience...
```

**File**: [.github/ISSUE_TEMPLATE/config.yml](.github/ISSUE_TEMPLATE/config.yml)

### 4. HACS Discovery

When users browse HACS:
- **Integration** shows in "Integrations" category
- **Card** shows in "Frontend" category
- Both mention each other in descriptions
- Both link to each other in READMEs

## Data Flow Between Components

### Integration Provides to Card

The integration exposes data via **entity attributes** that the card consumes:

```python
# camera.py
@property
def extra_state_attributes(self) -> dict[str, Any]:
    return {
        "monitor_id": monitor.id,
        "go2rtc_stream_id": str(monitor.id),  # Card uses this
        "go2rtc_available": True,  # Card checks this
        # ... other attributes
    }
```

### Card Reads from Integration

```typescript
// zoneminder-card.ts
const cameraEntity = this.hass.states[monitorConfig.entity];
const streamId = cameraEntity.attributes.go2rtc_stream_id;
const go2rtcUrl = this._config.zoneminder_go2rtc_url; // Or auto-detect
```

### Motion Detection Integration

```typescript
// Card monitors binary sensor
const motionEntityId = cameraEntity.replace('camera.', 'binary_sensor.') + '_motion';
const motionEntity = this.hass.states[motionEntityId];
const isMotion = motionEntity?.state === 'on';
```

## Installation Scenarios

### Scenario 1: Integration First (Most Common)

1. User installs **ZMHA integration** via HACS
2. Sets up ZoneMinder connection
3. Sees **persistent notification** about card
4. Goes to HACS → Frontend
5. Installs **ZoneMinder Card**
6. Adds card to dashboard

### Scenario 2: Card First (Less Common)

1. User discovers **ZoneMinder Card** in HACS
2. Reads README and sees it requires **ZMHA integration**
3. Goes to HACS → Integrations
4. Installs **ZMHA integration**
5. Returns to configure card

### Scenario 3: Neither (Standard HA Features)

1. User installs **ZMHA integration** only
2. Dismisses card notification
3. Uses standard Lovelace camera cards (picture-entity, etc.)
4. **Integration works perfectly fine** with MJPEG streaming

## User Communication Strategy

### Integration README

**Tone**: "The card is **recommended** for enhanced experience"
- Highlight benefits (WebRTC, low latency)
- Show it's **optional**
- Provide clear install instructions

### Card README

**Tone**: "Requires the **ZMHA integration**"
- List integration as prerequisite
- Link to integration repository
- Explain what integration provides

### Both READMEs

- Cross-link prominently
- Explain the relationship
- Show examples of both together

## Version Compatibility

### Current Approach: Loose Coupling

**Integration version**: `0.1.0`
**Card version**: `0.1.0`

No hard version requirements - both evolve independently.

### Future Considerations

If card requires specific integration features:

**In Card README**:
```markdown
## Requirements
- ZMHA Integration v0.2.0 or newer
```

**In Card Code**:
```typescript
// Check for required attributes
if (!cameraEntity.attributes.go2rtc_stream_id) {
  console.warn('ZMHA integration too old - please update');
}
```

## HACS Metadata

### Integration (hacs.json not needed for default repo)

When submitting to HACS default repository:
```json
{
  "name": "ZoneMinder",
  "description": "ZoneMinder integration with MQTT real-time events. Install companion ZoneMinder Card for enhanced WebRTC viewing.",
  "repository": "yourusername/zmha"
}
```

### Card (hacs.json)

```json
{
  "name": "ZoneMinder Card",
  "render_readme": true,
  "filename": "zoneminder-card.js"
}
```

## Benefits of This Approach

### For Users

✅ **Choice**: Can use standard cards or enhanced card
✅ **Discovery**: Multiple touchpoints to learn about card
✅ **Flexibility**: Integration works independently
✅ **Progressive Enhancement**: Can add card later

### For Developers

✅ **Independent Versioning**: Card and integration version separately
✅ **Separate Repos**: Easier to manage
✅ **Clear Separation**: Integration = data, Card = presentation
✅ **HACS Compatible**: Follows HACS best practices

### For HACS

✅ **No Dependency Hell**: No cross-category dependencies
✅ **Standard Pattern**: Follows existing practices (e.g., mini-graph-card)
✅ **Easy Discovery**: Users find both through search

## Similar Patterns in HACS

This pattern is used by many popular integrations:

| Integration | Card | Pattern |
|-------------|------|---------|
| Frigate | frigate-card | Optional companion card |
| Unifi | unifi-card | Optional companion card |
| AdGuard | adguard-card | Optional companion card |
| Weather | weather-card | Optional companion card |

## Implementation Checklist

### Integration Side

- [x] Add card mention to README (top callout)
- [x] Add companion card section to features
- [x] Add install instructions for card
- [x] Create GitHub issue template with card link
- [x] Add persistent notification on setup
- [x] Expose required attributes (go2rtc_stream_id, etc.)

### Card Side

- [ ] Add integration as prerequisite in README
- [ ] Link to integration repository
- [ ] Document required entity attributes
- [ ] Show example with integration
- [ ] Test auto-detection of go2rtc URL

### HACS Submission

- [ ] Submit integration to HACS default
- [ ] Submit card to HACS frontend
- [ ] Cross-link in HACS descriptions
- [ ] Test discovery flow

## Future Enhancements

### Automatic Card Installation Prompt

**Not currently possible in HACS**, but could be added in the future:

```python
# In integration's config flow
async def async_step_user(self, user_input=None):
    # After successful setup
    if success:
        # Suggest card installation
        return self.async_show_menu(
            menu_options=["continue", "install_card"]
        )
```

### Service for Card Detection

The integration could provide a service to check if the card is installed:

```python
# In __init__.py
@callback
def has_zoneminder_card(hass):
    """Check if ZoneMinder Card is installed."""
    return "zoneminder-card" in hass.data.get("lovelace", {}).get("resources", [])
```

### Home Assistant Recommendations (Future)

Home Assistant is working on a recommendations system that could:
- Automatically suggest the card when integration is installed
- Show card in UI when viewing camera entities
- Provide in-app installation

## Testing the User Experience

### Test Scenario 1: New User

1. Install integration via HACS
2. See notification about card
3. Click notification link
4. Install card via HACS
5. Add card to dashboard
6. Verify WebRTC streaming works

### Test Scenario 2: Integration Only

1. Install integration via HACS
2. Dismiss notification
3. Add standard picture-entity card
4. Verify MJPEG streaming works
5. (Optional) Install card later

### Test Scenario 3: Updates

1. Update integration
2. Verify card still works
3. Update card
4. Verify integration still works

## Summary

The **ZMHA integration** and **ZoneMinder Card** are designed as:

🔗 **Loosely Coupled**: Work independently
🤝 **Complementary**: Better together
🎯 **User-Friendly**: Multiple discovery paths
📦 **HACS-Native**: Follow HACS best practices
✨ **Progressive Enhancement**: Card enhances, doesn't replace

This approach provides maximum flexibility while guiding users toward the best experience.
