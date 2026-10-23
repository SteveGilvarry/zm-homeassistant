#!/bin/bash

# Add ZoneMinder Card Section to Overview Dashboard
set -e

CONTAINER_NAME="zmha-homeassistant"
DASHBOARD_FILE="/config/.storage/lovelace"

echo "🎨 Adding ZoneMinder Card to Overview Dashboard"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Backup
echo "💾 Creating backup..."
docker exec "$CONTAINER_NAME" sh -c "cp $DASHBOARD_FILE ${DASHBOARD_FILE}.backup 2>/dev/null || true"

# Create updated config with ZoneMinder section
cat > /tmp/lovelace-config.json << 'EOF'
{
  "version": 1,
  "minor_version": 1,
  "key": "lovelace",
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
                      "entity": "camera.hikvision_ds_2cd2087g2_lu"
                    },
                    {
                      "entity": "camera.driveway_east"
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
docker cp /tmp/lovelace-config.json "$CONTAINER_NAME:$DASHBOARD_FILE"
rm /tmp/lovelace-config.json

echo "✅ Dashboard updated!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Next Steps:"
echo ""
echo "1. Refresh the Overview page (F5)"
echo "2. You should see the ZoneMinder Card!"
echo ""
echo "🔄 To restore if needed:"
echo "   docker exec $CONTAINER_NAME cp ${DASHBOARD_FILE}.backup $DASHBOARD_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
