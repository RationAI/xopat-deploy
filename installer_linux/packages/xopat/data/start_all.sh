#!/bin/bash
BASEDIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$BASEDIR/wsi-service/.env"
export WSI_PORT=8050
export XOPAT_NODE_PORT=9001
export XOPAT_CACHE_DIR="$BASEDIR/xopat/cache"

# If xOpat is already running, open the browser and exit.
if lsof -i :"$XOPAT_NODE_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "xOpat is already running."
    xdg-open "http://localhost:$XOPAT_NODE_PORT/" 2>/dev/null &
    sleep 2
    exit 0
fi

# First run: ask for slides directory if not set
DATA_DIR=$(grep "^WS_DATA_DIR=" "$ENV_FILE" | cut -d'=' -f2)
if [ -z "$DATA_DIR" ]; then
    echo "No slides folder configured."
    read -rp "Would you like to set it now? [Y/n] " answer
    if [ "$answer" != "n" ] && [ "$answer" != "N" ]; then
        "$BASEDIR/change_slides_dir.sh"
        # Reload after setting
        DATA_DIR=$(grep "^WS_DATA_DIR=" "$ENV_FILE" | cut -d'=' -f2)
        if [ -z "$DATA_DIR" ]; then
            echo "Still no folder configured. Exiting."
            read -rp "Press Enter to close."
            exit 1
        fi
    else
        exit 0
    fi
fi

cleanup() {
    echo "Stopping servers..."
    kill $WSI_PID $XOPAT_PID 2>/dev/null
    wait $WSI_PID $XOPAT_PID 2>/dev/null
}
trap cleanup EXIT

echo "Starting WSI-Service..."
cd "$BASEDIR/wsi-service"
./wsi_service_binary > "$BASEDIR/wsi-service.log" 2>&1 &
WSI_PID=$!
cd "$BASEDIR"
sleep 3
echo "Starting xOpat..."
"$BASEDIR/xopat/xopat_binary" > "$BASEDIR/xopat.log" 2>&1 &
XOPAT_PID=$!
sleep 2
echo "Slides folder: $DATA_DIR"
echo "To change it, run change_slides_dir.sh and restart xOpat."
xdg-open "http://localhost:$XOPAT_NODE_PORT/" 2>/dev/null

echo "xOpat is running. Close this window to stop."
wait