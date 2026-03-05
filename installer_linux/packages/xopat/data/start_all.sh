#!/bin/bash
BASEDIR="$(cd "$(dirname "$0")" && pwd)"
echo "Starting WSI-Service..."
cd "$BASEDIR/wsi-service"
./wsi_service_binary &
cd "$BASEDIR"
sleep 3
echo "Starting xOpat..."
"$BASEDIR/xopat/xopat_binary" &
sleep 2
xdg-open "http://localhost:9000/"