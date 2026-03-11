#!/bin/bash
set -e
echo "=== Build xOpat (Linux) ==="

ROOT_DIR=$(dirname "$(realpath "$0")")/../..
XOPAT_DIR="$ROOT_DIR/external/xopat"
ROOT_DIST="$ROOT_DIR/dist"
OUTPUT_BIN="$XOPAT_DIR/xopat_binary"

if [ ! -d "$XOPAT_DIR" ]; then echo "Missing submodule: $XOPAT_DIR"; exit 1; fi

cd "$XOPAT_DIR"
npm install
cp "$XOPAT_DIR/env/env.default.json" "$XOPAT_DIR/env/env.json"
npm run build
pkg . --targets node18-linux-x64 --output "$OUTPUT_BIN"

if [ ! -f "$OUTPUT_BIN" ]; then echo "Build failed: $OUTPUT_BIN not found"; exit 1; fi

mkdir -p "$ROOT_DIST/xopat"
cp "$OUTPUT_BIN" "$ROOT_DIST/xopat/xopat_binary"

echo "OK: $ROOT_DIST/xopat/xopat_binary"