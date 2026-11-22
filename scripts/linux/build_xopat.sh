#!/bin/bash
set -e
echo "=== Build xOpat (Linux) ==="

ROOT_DIR=$(dirname "$(realpath "$0")")/../..
XOPAT_DIR="$ROOT_DIR/external/xopat"
ROOT_DIST="$ROOT_DIR/dist"
OUTPUT_BIN="$XOPAT_DIR/xopat_binary"

if [ ! -d "$XOPAT_DIR" ]; then echo "Missing submodule: $XOPAT_DIR"; exit 1; fi

cd "$XOPAT_DIR"
# npm ci, not npm install: every server bundle records a content hash of
# node_modules/.package-lock.json in its build key, so an install that silently
# moves a transitive dependency makes two releases from one commit differ.
npm ci
cp "$XOPAT_DIR/env/env.default.json" "$XOPAT_DIR/env/env.json"
# Builds the client bundles AND prebuilds every plugin/module *.server.* entry
# (grunt serverBuild). The binary carries no compiler, so an entry missing here
# answers RPC_UNKNOWN_METHOD for the life of the release.
npm run build
# @yao-pkg/pkg: the maintained fork (vercel/pkg is archived and caps out at
# node18). Pinned by the xOpat lockfile rather than a global install.
npx @yao-pkg/pkg . --targets node22-linux-x64 --output "$OUTPUT_BIN"

if [ ! -f "$OUTPUT_BIN" ]; then echo "Build failed: $OUTPUT_BIN not found"; exit 1; fi

mkdir -p "$ROOT_DIST/xopat"
cp "$OUTPUT_BIN" "$ROOT_DIST/xopat/xopat_binary"

echo "OK: $ROOT_DIST/xopat/xopat_binary"