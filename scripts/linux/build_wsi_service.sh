#!/bin/bash
set -e
echo "=== Build WSI-Service (Linux) ==="

REPO_ROOT=$(dirname "$(realpath "$0")")/../..
WSI_DIR="$REPO_ROOT/external/wsi-service"
WSI_DIST_DIR="$WSI_DIR/dist/wsi_service_binary"
ROOT_DIST="$REPO_ROOT/dist"
RUN_SRC="$REPO_ROOT/scripts/run/run_wsi_service_linux.py"
SPEC_SRC="$REPO_ROOT/scripts/specs/wsi_service_linux.spec"
RUN_DST="$WSI_DIR/run_wsi_service.py"
SPEC_DST="$WSI_DIR/wsi_service.spec"
LIBS_LINUX_DIR="$REPO_ROOT/libs/linux"

if [ ! -d "$WSI_DIR" ]; then echo "Missing submodule: $WSI_DIR"; exit 1; fi
if [ ! -f "$RUN_SRC" ]; then echo "Missing: $RUN_SRC"; exit 1; fi
if [ ! -f "$SPEC_SRC" ]; then echo "Missing: $SPEC_SRC"; exit 1; fi

cd "$WSI_DIR"

if [ -d "venv" ]; then rm -rf venv; fi
python3 -m venv venv
source venv/bin/activate

pip install -U pip wheel setuptools pyinstaller
pip install poetry
poetry lock
poetry install

cp "$RUN_SRC" "$RUN_DST"
cp "$SPEC_SRC" "$SPEC_DST"

if [ ! -d "$LIBS_LINUX_DIR" ]; then echo "WARNING: missing $LIBS_LINUX_DIR (OpenSlide libs)"; fi

pyinstaller --clean wsi_service.spec

if [ ! -d "$WSI_DIST_DIR" ]; then echo "Build failed: $WSI_DIST_DIR not found"; exit 1; fi

mkdir -p "$ROOT_DIST"
cp -r "$WSI_DIST_DIR" "$ROOT_DIST/"

echo "OK: $ROOT_DIST/wsi_service_binary/wsi_service_binary"