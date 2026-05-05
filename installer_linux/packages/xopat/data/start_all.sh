#!/bin/bash
BASEDIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$BASEDIR/wsi-service/.env"

# First run: prompt for data directory if not set
DATA_DIR=$(grep "^WS_DATA_DIR=" "$ENV_FILE" | cut -d'=' -f2)
if [ -z "$DATA_DIR" ]; then
    if command -v zenity &>/dev/null; then
        CHOSEN=$(zenity --file-selection --directory --title="xOpat — Select slides folder" 2>/dev/null)
    else
        read -rp "Enter path to your slides folder: " CHOSEN
    fi
    if [ -z "$CHOSEN" ]; then
        exit 0
    fi
    sed -i "s|^WS_DATA_DIR=.*|WS_DATA_DIR=$CHOSEN|" "$ENV_FILE"
fi

cleanup() {
    echo "Stopping servers..."
    kill $WSI_PID $XOPAT_PID 2>/dev/null
    wait $WSI_PID $XOPAT_PID 2>/dev/null
}
trap cleanup EXIT

echo "Starting WSI-Service..."
cd "$BASEDIR/wsi-service"
./wsi_service_binary &
WSI_PID=$!
cd "$BASEDIR"
sleep 3
echo "Starting xOpat..."
export XOPAT_CACHE_DIR="$BASEDIR/xopat/cache"
"$BASEDIR/xopat/xopat_binary" &
XOPAT_PID=$!
sleep 2
xdg-open "http://localhost:9000/"

echo "xOpat is running. Close this window to stop."
wait