#!/bin/bash
BASEDIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$BASEDIR/wsi-service/.env"

if command -v zenity &>/dev/null; then
    CHOSEN=$(zenity --file-selection --directory --title="xOpat — Select slides folder" 2>/dev/null)
else
    echo "Select a folder containing slides."
    read -rp "Path to slides folder: " CHOSEN
fi

if [ -z "$CHOSEN" ]; then
    echo "No folder selected."
    exit 1
fi

if [ ! -d "$CHOSEN" ]; then
    echo "Error: '$CHOSEN' does not exist or is not a directory."
    exit 1
fi

sed -i "s|^WS_DATA_DIR=.*|WS_DATA_DIR=$CHOSEN|" "$ENV_FILE"
echo "Slides folder set to: $CHOSEN"
if pgrep -f wsi_service_binary &>/dev/null; then
    echo "Restart xOpat for the change to take effect."
fi