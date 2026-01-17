"""Constants for the ZoneMinder integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "zoneminder"

# Config flow
CONF_MQTT_ENABLED: Final = "mqtt_enabled"
CONF_MQTT_TOPIC: Final = "mqtt_topic"
DEFAULT_MQTT_TOPIC: Final = "zoneminder"

# Default values
DEFAULT_TIMEOUT: Final = 10
DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=30)
MQTT_SCAN_INTERVAL: Final = timedelta(minutes=5)  # When MQTT is active

# API endpoints (relative paths - will be joined with host)
API_LOGIN: Final = "api/host/login.json"
API_LOGOUT: Final = "api/host/logout.json"
API_VERSION: Final = "api/host/getVersion.json"
API_MONITORS: Final = "api/monitors.json"
API_MONITOR: Final = "api/monitors/{monitor_id}.json"
API_EVENTS: Final = "api/events.json"
API_EVENT: Final = "api/events/{event_id}.json"
API_ALARM_ON: Final = "api/monitors/alarm/id:{monitor_id}/command:on.json"
API_ALARM_OFF: Final = "api/monitors/alarm/id:{monitor_id}/command:off.json"

# Stream paths (relative paths - will be joined with host)
STREAM_PATH: Final = "cgi-bin/nph-zms"
EVENT_VIDEO_PATH: Final = "api/events/{event_id}.mp4"

# Event types
EVENT_TYPE_MOTION: Final = "Motion"
EVENT_TYPE_ALARM: Final = "Alarm"

# Monitor functions (modes)
MONITOR_FUNCTION_NONE: Final = "None"
MONITOR_FUNCTION_MONITOR: Final = "Monitor"
MONITOR_FUNCTION_MODECT: Final = "Modect"
MONITOR_FUNCTION_RECORD: Final = "Record"
MONITOR_FUNCTION_MOCORD: Final = "Mocord"
MONITOR_FUNCTION_NODECT: Final = "Nodect"

MONITOR_FUNCTIONS: Final = [
    MONITOR_FUNCTION_NONE,
    MONITOR_FUNCTION_MONITOR,
    MONITOR_FUNCTION_MODECT,
    MONITOR_FUNCTION_RECORD,
    MONITOR_FUNCTION_MOCORD,
    MONITOR_FUNCTION_NODECT,
]

# Services
SERVICE_TRIGGER_EVENT: Final = "trigger_event"
SERVICE_PTZ: Final = "ptz"

# PTZ commands
PTZ_CMD_MOVE_LEFT: Final = "moveLeft"
PTZ_CMD_MOVE_RIGHT: Final = "moveRight"
PTZ_CMD_MOVE_UP: Final = "moveUp"
PTZ_CMD_MOVE_DOWN: Final = "moveDown"
PTZ_CMD_ZOOM_IN: Final = "zoomIn"
PTZ_CMD_ZOOM_OUT: Final = "zoomOut"
PTZ_CMD_PRESET: Final = "preset"

# Platforms
PLATFORMS: Final = [
    "camera",
    "binary_sensor",
    "sensor",
    "button",
    "select",
]
