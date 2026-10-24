# ZoneMinder

Live cameras, browsable recordings, real-time motion and monitor controls for
[ZoneMinder](https://zoneminder.com/), configured entirely from the Home Assistant UI.

## Highlights

- One camera entity per monitor, streamed through Home Assistant so it works in stock
  cards
- Recordings under **Media > ZoneMinder**, by camera and day, with thumbnails
- Sub-second motion over MQTT, that does not fire on continuous recording
- Capturing, analysing and recording selects matching ZoneMinder 1.37+
- Storage, event counts, capture rate and daemon health as sensors
- PTZ with presets, on the monitors that support it
- A motion notification blueprint

Works with the standalone [zm-api](https://github.com/SteveGilvarry/zm-api) server or
ZoneMinder's built-in API.

## After installing

Restart Home Assistant, then add the integration under
**Settings > Devices & Services**. You will need the server URL, a username and a
password. Set an internal Home Assistant URL under **Settings > System > Network** first,
otherwise live video cannot be proxied.

See the [README](https://github.com/SteveGilvarry/zm-homeassistant) for the MQTT and streaming
setup.
