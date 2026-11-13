#!/bin/bash
# T7 sims on the Mac mini: run_batch.sh "tag:flags" ... (at most 6), each the lean-t3 base sequence plus the flags.
cd "$HOME/code/robotics/microduck-sim/guide/firmware/mac" || exit 1
OUT="$HOME/sims/lean-t7"
mkdir -p "$OUT"
for c in "$@"; do
  n="${c%%:*}"; x="${c#*:}"
  # shellcheck disable=SC2086
  "$HOME/.venvs/microduck-dyn/bin/python" brain_sim_check.py --model asbuilt --manifest current --volt 7.6 --drop 0.036 \
    --imu-pitch 2 --walk-at 4 --walk-s 3.6 --vx 0.25 --after-walk 30 $x --tick-log "$OUT/$n.jsonl" > "$OUT/$n.out" 2>&1 &
done
wait
for c in "$@"; do
  n="${c%%:*}"
  "$HOME/.venvs/microduck-dyn/bin/python" "$OUT/t7_course.py" "$OUT/$n.jsonl" --quiet --end-summary 20
  tail -1 "$OUT/$n.out" | "$HOME/.venvs/microduck-dyn/bin/python" -c "import sys,json
try:
    d=json.loads(sys.stdin.read()); print('    fell_at', d.get('fell_at'), 'max_tilt', d.get('max_tilt'), 'dist_x', d.get('dist_x'))
except Exception as e:
    print('    no result line:', e)"
done
