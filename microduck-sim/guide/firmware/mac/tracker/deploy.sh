#!/bin/bash
# One-way deploy of the tracker sources, MacBook -> Mac mini. Never copy back.
# Weights (.pt), .venv, testdata and runs are excluded; they live on the Mac mini only.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/"
DST="mac-mini:/Users/shawnxiang/code/robotics/microduck-sim/guide/firmware/mac/tracker/"
rsync -az --delete --exclude .venv --exclude weights --exclude testdata --exclude runs --exclude uv.lock \
  --exclude '*.pt' --exclude '*.ts' --exclude '*.jsonl' --exclude '__pycache__' "$SRC" "$DST"
echo "deployed to $DST"
