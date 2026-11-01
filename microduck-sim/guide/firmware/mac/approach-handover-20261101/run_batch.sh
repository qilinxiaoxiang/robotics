#!/bin/zsh
# Approach hand-over batch: approach_sim.py on a grid of 12 mm ball placements, 6 at a time. Run on the Mac mini.
#   [SIM=variant.py VARIANT_*=...] [EXTRA="--pitch-offset 2"] zsh run_batch.sh <out_dir>
cd "$(dirname "$0")/.." || exit 1
OUT="${1:-approach-handover-20261101/runs}"
mkdir -p "$OUT"
PY="$HOME/.venvs/microduck-dyn/bin/python"
for r in ${=RADII:-0.30 0.45 0.60 0.75 0.90}; do
  for b in -40 -20 0 20 40; do
    x=$(python3 -c "import math;print(round($r*math.cos(math.radians($b)),3))")
    y=$(python3 -c "import math;print(round($r*math.sin(math.radians($b)),3))")
    echo "$x $y r${r}_b${b}"
  done
done | while read x y t; do [ -f "$OUT/$t.json" ] && continue; echo "$x $y $t"; done | xargs -P 6 -L 1 zsh -c '"'"$PY"'" ${SIM:-approach_sim.py} --obj $0 $1 --obj-height 0.012 ${=EXTRA} --out "'"$OUT"'/$2.json" > "'"$OUT"'/$2.txt" 2>&1; true'
echo done
