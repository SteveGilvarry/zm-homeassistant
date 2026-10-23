#!/bin/bash

echo "==================================================================="
echo "Motion Sensor Test - ZoneMinder MQTT Integration"
echo "==================================================================="
echo ""
echo "This will monitor:"
echo "  1. MQTT messages from ZoneMinder"
echo "  2. Home Assistant log for motion sensor updates"
echo ""
echo "Please trigger an event in ZoneMinder (wave at camera)"
echo ""
echo "==================================================================="
echo ""

# Start mosquitto_sub in background
echo "[1/2] Starting MQTT listener..."
docker exec zmha-mosquitto mosquitto_sub -t 'ZoneMinder/#' -v 2>&1 | while read line; do
    echo "[MQTT] $line"
done &
MQTT_PID=$!

# Watch HA logs
echo "[2/2] Starting Home Assistant log monitor..."
echo ""
echo "Waiting for events... (Ctrl+C to stop)"
echo ""

docker logs -f zmha-homeassistant 2>&1 | grep --line-buffered -E "(✓✓✓ MQTT EVENT|Binary sensor.*received|Event.*started|Event.*ended)" | while read line; do
    echo "[HOME ASSISTANT] $line"
done

# Cleanup on exit
trap "kill $MQTT_PID 2>/dev/null" EXIT
