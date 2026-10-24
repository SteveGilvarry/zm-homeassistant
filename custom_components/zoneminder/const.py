# SPDX-License-Identifier: Apache-2.0
"""Constants for the ZoneMinder integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "zoneminder"

# -- Config entry keys -------------------------------------------------------

CONF_BACKEND: Final = "backend"
CONF_MQTT_ENABLED: Final = "mqtt_enabled"
#: Signs the per-event links put in notifications. Created on first setup.
CONF_NOTIFY_KEY: Final = "notify_key"
CONF_MQTT_TOPIC: Final = "mqtt_topic"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_VERIFY_SSL: Final = "verify_ssl"
#: Optional URL of the ZoneMinder web UI, used for "Visit device" links.
CONF_WEB_URL: Final = "web_url"

# -- Polling -----------------------------------------------------------------

DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=30)
MQTT_SCAN_INTERVAL: Final = timedelta(minutes=5)
#: Server-wide data (storage, daemons, per-monitor summaries) is slow to change.
SERVER_INFO_INTERVAL: Final = timedelta(minutes=5)
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 3600

#: How many recent events to pull per refresh (bucketed across all monitors).
EVENT_FETCH_LIMIT: Final = 200
#: Events kept in coordinator data per monitor.
EVENTS_PER_MONITOR: Final = 10

#: A motion state driven by MQTT is dropped back to poll-derived state if the
#: matching "event end" never arrives. Protects against a lost message pinning
#: a binary sensor on forever.
MQTT_MOTION_TIMEOUT: Final = timedelta(minutes=15)

# -- MQTT --------------------------------------------------------------------

#: ZoneMinder's ZM_MQTT_TOPIC_PREFIX default. Case matters.
DEFAULT_MQTT_TOPIC: Final = "ZoneMinder"

SIGNAL_MQTT_EVENT: Final = "zoneminder_mqtt_event_{}"
#: A monitor's live alarm state from the event stream: idle, prealarm, alarm, alert.
SIGNAL_ALARM_STATE: Final = "zoneminder_alarm_state_{}"

# -- Services ----------------------------------------------------------------

SERVICE_TRIGGER_EVENT: Final = "trigger_event"
SERVICE_CANCEL_EVENT: Final = "cancel_event"
SERVICE_PTZ: Final = "ptz"
SERVICE_SET_MONITOR_STATE: Final = "set_monitor_state"
SERVICE_SAVE_RUN_STATE: Final = "save_run_state"

#: Path prefix for the authenticating media proxy registered by http.py.
PROXY_URL_BASE: Final = "/api/zoneminder"

# -- Platforms ---------------------------------------------------------------

PLATFORMS: Final = [
    "binary_sensor",
    "button",
    "camera",
    "event",
    "select",
    "sensor",
]
