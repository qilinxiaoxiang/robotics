#!/bin/sh
# Run on the MacBook: mirror this folder to the Mac mini, run a command there, bring build/ back.
#   sh tools/sync_build.sh                 fetch deps if needed, build, run both checks
#   sh tools/sync_build.sh sh tools/fetch_deps.sh
# Edits stay on the MacBook; .deps and build stay on the Mac mini (build/ is copied back for the .uf2 and reports).
set -eu

HERE=$(cd "$(dirname "$0")/.." && pwd)
REMOTE_DIR="code/robotics/microduck-sim/head-usb-board-20261111/firmware"
HOST=mac-mini

ssh "$HOST" "mkdir -p '$REMOTE_DIR'"
rsync -a --delete --exclude .deps --exclude build --exclude __pycache__ "$HERE/" "$HOST:$REMOTE_DIR/"
if [ "$#" -eq 0 ]; then
    set -- sh tools/build.sh
fi
ssh "$HOST" "cd '$REMOTE_DIR' && PATH=/opt/homebrew/bin:\$PATH $*"
mkdir -p "$HERE/build"
rsync -a --include '*.uf2' --include '*.elf' --include '*.bin' --include '*.dis' --include '*.map' \
    --include '*.json' --include '*.log' --include '*.txt' --include '*.pio.h' --exclude '*/' --exclude '*' \
    "$HOST:$REMOTE_DIR/build/" "$HERE/build/" 2>/dev/null || true
