#!/bin/bash

# Add ZoneMinder Card to Dashboard
# Usage: ./add-to-dashboard.sh [container_name]

set -e

CONTAINER_NAME="${1:-zmha-homeassistant}"
DASHBOARD_FILE="/config/.storage/lovelace.dashboard_zoneminder"

echo "🎨 Adding ZoneMinder Card to Dashboard"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Error: Container '$CONTAINER_NAME' not found"
    exit 1
fi

# Backup current dashboard
echo "💾 Creating backup..."
docker exec "$CONTAINER_NAME" cp "$DASHBOARD_FILE" "${DASHBOARD_FILE}.backup"

# Create the card configuration
cat > /tmp/zoneminder-card-config.json << 'EOF'
{
  "version": 1,
  "minor_version": 1,
  "key": "lovelace.dashboard_zoneminder",
  "data": {
    "config": {
      "views": [
        {
          "title": "Home",
          "sections": [
            {
              "type": "grid",
              "cards": [
                {
                  "type": "custom:zoneminder-card",
                  "title": "Security Cameras",
                  "zoneminder_go2rtc_url": "http://192.168.0.45:1984",
                  "monitors": [
                    {
                      "entity": "camera.hikvision_ds_2cd2087g2_lu_2",
                      "rows": 2
                    },
                    {
                      "entity": "camera.driveway_east_2",
                      "rows": 2
                    }
                  ],
                  "columns": 2,
                  "streaming_mode": "webrtc",
                  "show_motion_indicator": true
                }
              ]
            }
          ]
        }
      ]
    }
  }
}
EOF

# Copy to container
echo "📝 Updating dashboard..."
docker cp /tmp/zoneminder-card-config.json "$CONTAINER_NAME:$DASHBOARD_FILE"
rm /tmp/zoneminder-card-config.json

echo "✅ Dashboard updated!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Next Steps:"
echo ""
echo "1. Go to http://localhost:8123/zoneminder"
echo "2. Refresh the page (F5 or Ctrl+R)"
echo "3. You should see the ZoneMinder Card!"
echo ""
echo "💡 Tip: If you don't see the card:"
echo "   - Clear browser cache (Ctrl+Shift+R)"
echo "   - Check browser console (F12) for errors"
echo ""
echo "🔄 To restore backup if needed:"
echo "   docker exec $CONTAINER_NAME cp ${DASHBOARD_FILE}.backup $DASHBOARD_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
