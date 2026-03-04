#!/bin/bash
set -e
echo "=== Build xOpat (Linux) ==="

ROOT_DIR=$(dirname "$(realpath "$0")")/../..
XOPAT_DIR="$ROOT_DIR/external/xopat"
ROOT_DIST="$ROOT_DIR/dist"
OUTPUT_BIN="$XOPAT_DIR/xopat_binary"
# TODO: remove once package.json is updated in xopat
CUSTOM_JSON_PACKAGE="$ROOT_DIR/scripts/linux/xopat_package.json"
JSON_PACKAGE="$XOPAT_DIR/package.json"
# TODO: remove once env is handled differently
ENV_SRC="$ROOT_DIR/envs/xopat_env.json"
ENV_TARGET="$XOPAT_DIR/env/env.json"

if [ ! -d "$XOPAT_DIR" ]; then echo "Missing submodule: $XOPAT_DIR"; exit 1; fi

# TODO: remove once package.json is updated in xopat
if [ ! -f "$CUSTOM_JSON_PACKAGE" ]; then echo "Missing: $CUSTOM_JSON_PACKAGE"; exit 1; fi
cp "$CUSTOM_JSON_PACKAGE" "$JSON_PACKAGE"

# TODO: remove once env is handled differently
if [ ! -f "$ENV_SRC" ]; then echo "Missing: $ENV_SRC"; exit 1; fi
mkdir -p "$XOPAT_DIR/env"
cp "$ENV_SRC" "$ENV_TARGET"

cd "$XOPAT_DIR"
npm install
npm run build
pkg . --targets node18-linux-x64 --output "$OUTPUT_BIN"

if [ ! -f "$OUTPUT_BIN" ]; then echo "Build failed: $OUTPUT_BIN not found"; exit 1; fi

mkdir -p "$ROOT_DIST/xopat"
cp "$OUTPUT_BIN" "$ROOT_DIST/xopat/xopat_binary"

echo "OK: $ROOT_DIST/xopat/xopat_binary"