#!/bin/bash
# Mirror what fullflow_sim.py needs to the Mac mini (~/sims/fullflow-20261111/microduck-sim, same layout), and run it
# there:  fullflow_sync.sh            sync only
#         fullflow_sync.sh run SEED   sync, run seed SEED, copy the video and events back to fullflow-20261111/
set -euo pipefail
SRC="$(cd "$(dirname "$0")/../../.." && pwd)"          # microduck-sim
DST="mac-mini:sims/fullflow-20261111/microduck-sim"
ssh mac-mini 'mkdir -p ~/sims/fullflow-20261111/microduck-sim/guide/firmware ~/sims/fullflow-20261111/microduck-sim/hardware-design-20260912/whole-robot-20260912 ~/sims/fullflow-20261111/microduck-sim/microduck_rl/src/mjlab_microduck ~/sims/fullflow-20261111/microduck-sim/microduck_rl/cmu ~/sims/fullflow-20261111/microduck-sim/microduck-simulator/app/public'
R="rsync -a --delete --exclude __pycache__"
$R --include='*.py' --include='*.json' --include='*.onnx' --exclude='*/' --exclude='*' "$SRC/guide/firmware/mac/" "$DST/guide/firmware/mac/"
$R "$SRC/guide/firmware/pi/" "$DST/guide/firmware/pi/"
$R --exclude='*.mp4' --exclude='*.png' --exclude='*.jpg' --exclude='*.gif' --exclude='*.log' --exclude='*.jsonl' \
  "$SRC/hardware-design-20260912/whole-robot-20260912/" "$DST/hardware-design-20260912/whole-robot-20260912/"
$R "$SRC/microduck_rl/src/mjlab_microduck/robot/" "$DST/microduck_rl/src/mjlab_microduck/robot/"
$R "$SRC/microduck_rl/cmu/model/" "$DST/microduck_rl/cmu/model/"
$R "$SRC/microduck-simulator/app/public/policies/" "$DST/microduck-simulator/app/public/policies/"
rsync -a "$SRC/CURRENT-STATE.json" "$DST/CURRENT-STATE.json"
echo "synced"
if [ "${1:-}" = "run" ]; then
  SEED="${2:-0}"
  OUT="$SRC/guide/firmware/mac/fullflow-20261111"
  mkdir -p "$OUT"
  ssh mac-mini "cd ~/sims/fullflow-20261111/microduck-sim/guide/firmware/mac && mkdir -p out && ~/.venvs/microduck-dyn/bin/python fullflow_sim.py --seed $SEED --out out/fullflow_s$SEED.mp4 --events out/fullflow_s$SEED.json" 2>&1 | tee "$OUT/run_s$SEED.log"
  rsync -a "mac-mini:sims/fullflow-20261111/microduck-sim/guide/firmware/mac/out/fullflow_s$SEED.*" "$OUT/"
fi
