#!/bin/bash
BASEDIR="$(cd "$(dirname "$0")" && pwd)"
echo "Starting WSI-Service..."
"$BASEDIR/wsi-service/wsi_service_binary" &
sleep 3
echo "Starting xOpat..."
"$BASEDIR/xopat/xopat_binary" &
sleep 2
xdg-open "http://localhost:9000/"