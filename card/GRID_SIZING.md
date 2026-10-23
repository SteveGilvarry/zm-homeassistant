# Grid Sizing for Rotated Cameras

The ZoneMinder card now supports custom grid sizing for each camera, which is particularly useful for cameras with rotated orientations.

## Configuration

Each monitor in the card configuration can specify:
- `rows`: Number of grid rows to span (default: 1)
- `columns`: Number of grid columns to span (default: 1)

## Example: Rotated Cameras

For cameras that are rotated 90° or 270° (portrait orientation), you can make them span 2 rows to give them more vertical space:

```yaml
type: custom:zoneminder-card
title: Security Cameras
zoneminder_go2rtc_url: http://192.168.0.45:1984
monitors:
  - entity: camera.hikvision_ds_2cd2087g2_lu_2
    rows: 2  # Camera is rotated, give it more height
  - entity: camera.driveway_east_2
    rows: 2  # Camera is rotated, give it more height
  - entity: camera.laneway_south_high_res_2
    # Normal orientation, default 1 row
  - entity: camera.hikvision_ds_2cd2642fwd_izs_2
    columns: 2  # Make this camera span 2 columns (wider)
columns: 2
streaming_mode: webrtc
show_motion_indicator: true
```

## How It Works

The card uses CSS Grid with:
- Configurable column count (via `columns` parameter on the card)
- Auto-flowing rows with minimum 200px height
- Dense packing to fill gaps
- Custom span values per camera

This allows you to create flexible layouts that accommodate different camera orientations and importance levels.

## Verified Behavior

**Grid Spanning**: ✅ Working correctly
- Monitors with `rows: 2` properly span 2 grid rows
- Height increases from ~200px (1 row) to ~408px (2 rows)
- `aspectRatio: auto` allows monitors to fill their grid cells

**Video Display**: ⚠️ Letterboxing remains
- Videos use `object-fit: contain` to maintain aspect ratio
- Rotated portrait videos will still have black bars on sides
- This is expected behavior to prevent cropping

To further reduce letterboxing on rotated cameras, you can:
1. Increase the `rows` value (e.g., `rows: 3` for even more vertical space)
2. Adjust the card's `columns` value to change overall layout proportions
3. Use `columns: 2, rows: 2` on a rotated camera to give it a larger square area

## Tips

1. **Rotated Cameras**: Use `rows: 2` for cameras with `ROTATE_90` or `ROTATE_270` orientation
2. **Important Cameras**: Use `columns: 2` and `rows: 2` to make a camera take up a large area
3. **Grid Layout**: The card will automatically pack cameras densely to minimize gaps
4. **Aspect Ratio**: Videos use `object-fit: contain` to maintain aspect ratio without cropping
5. **Experimentation**: Try different row/column combinations to find the best layout for your cameras
