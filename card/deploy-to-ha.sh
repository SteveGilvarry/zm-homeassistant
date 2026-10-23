#!/bin/bash

# Deploy ZoneMinder Card to Home Assistant Docker Container
# Usage: ./deploy-to-ha.sh [container_name]

set -e

# Configuration
CONTAINER_NAME="${1:-homeassistant}"
HA_CONFIG_PATH="/config"
CARD_FILE="dist/zoneminder-card.js"
DEST_PATH="$HA_CONFIG_PATH/www/zoneminder-card.js"

echo "🚀 Deploying ZoneMinder Card to Home Assistant"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if card file exists
if [ ! -f "$CARD_FILE" ]; then
    echo "❌ Error: $CARD_FILE not found"
    echo "   Run 'npm run build' first"
    exit 1
fi

# Check if Docker container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Error: Container '$CONTAINER_NAME' not found or not running"
    echo "   Available containers:"
    docker ps --format '  - {{.Names}}'
    exit 1
fi

echo "📦 Container: $CONTAINER_NAME"
echo "📁 Source: $CARD_FILE"
echo "📍 Destination: $DEST_PATH"
echo ""

# Create www directory if it doesn't exist
echo "📂 Creating www directory if needed..."
docker exec "$CONTAINER_NAME" mkdir -p "$HA_CONFIG_PATH/www"

# Copy the card file
echo "📋 Copying card file..."
docker cp "$CARD_FILE" "$CONTAINER_NAME:$DEST_PATH"

# Verify the file was copied
if docker exec "$CONTAINER_NAME" test -f "$DEST_PATH"; then
    FILE_SIZE=$(docker exec "$CONTAINER_NAME" stat -c%s "$DEST_PATH" 2>/dev/null || docker exec "$CONTAINER_NAME" stat -f%z "$DEST_PATH")
    echo "✅ Card deployed successfully! (${FILE_SIZE} bytes)"
else
    echo "❌ Error: Failed to copy file"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Next Steps:"
echo ""
echo "1. Add Lovelace Resource:"
echo "   Settings → Dashboards → Resources → Add Resource"
echo "   URL: /local/zoneminder-card.js"
echo "   Type: JavaScript Module"
echo ""
echo "2. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)"
echo ""
echo "3. Add card to dashboard:"
echo "   type: custom:zoneminder-card"
echo "   monitors:"
echo "     - entity: camera.front_door"
echo "     - entity: camera.backyard"
echo ""
echo "📚 Documentation: https://github.com/yourusername/zoneminder-card"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
