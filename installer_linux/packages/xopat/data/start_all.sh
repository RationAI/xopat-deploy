#!/bin/bash
BASEDIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$BASEDIR/wsi-service/.env"

# First run: prompt for data directory if not set
DATA_DIR=$(grep "^WS_DATA_DIR=" "$ENV_FILE" | cut -d'=' -f2)
if [ -z "$DATA_DIR" ]; then
    echo "No slides folder configured."
    echo "Run change_data_dir.sh to set it."
    exit 1
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
echo "Slides folder: $DATA_DIR"
echo "To change it, run change_data_dir.sh and restart xOpat."
xdg-open "http://localhost:9000/"

echo "xOpat is running. Close this window to stop."
wait