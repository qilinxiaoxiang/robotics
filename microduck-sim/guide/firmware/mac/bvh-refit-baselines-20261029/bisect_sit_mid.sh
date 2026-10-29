#!/bin/zsh
# bisect_sit_mid.sh: teleop sit_stand_from_stand61 (seeds 0-2, 7.0 V, 4 % drops, current code, D-030 neck 0.25) on the
# plugged manifests between the 10-19 one and now: microduck_rl e0194611 (saddle lid on) and 1f2ab62c (A7Z to the
# saddle), so the step that moved seed 2 is pinned to 87979d52 (V1.35 saddle). Results/bisect_sit_mid.jsonl. Mac mini.
set -u
HERE=${0:A:h}
PY=~/.venvs/microduck-dyn/bin/python
OUT=$HERE/results/bisect_sit_mid.jsonl
: > $OUT
MAC=$HERE/..
run() {  # label manifest seed
  local label=$1 man=$2 seed=$3
  local line=$(cd $MAC && $PY $HERE/stand_neck_run.py 0.25 brain_sim_check.py --model asbuilt --manifest $man --volt 7.0 \
      --drop 0.04 --walk-s 0 --sit-at 4 --unsit-at 10 --seed $seed 2>/dev/null | grep '^{' | tail -1)
  print -r -- "{\"label\": \"$label\", \"seed\": $seed, \"neck\": 0.25, \"r\": ${line:-null}}" >> $OUT
}
for seed in 0 1 2; do
  run e0194611 ~/sims/bvh-refit-20261029/plugged-e0194611.json $seed &
  run 1f2ab62c ~/sims/bvh-refit-20261029/plugged-1f2ab62c.json $seed &
done
wait
