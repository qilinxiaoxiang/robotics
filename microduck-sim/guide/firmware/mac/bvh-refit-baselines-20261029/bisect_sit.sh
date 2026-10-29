#!/bin/zsh
# bisect_sit.sh: teleop sit_stand_from_stand61 (seeds 0-2, 7.0 V, 4 % drops) against the plugged manifest of 10-19
# (microduck_rl 2da47f88, the one teleop-sim-check.json was made with on 10-20) and of now (87979d52, V1.35 saddle),
# the open-loop stand neck (D-030 0.25 vs 0.35), and the 10-20 brain/runtime (var-t1020: walk_brain, brain_sim_check,
# walk_wired, stand_pose at 8bbaef9). One line per run to results/bisect_sit.jsonl. Mac mini.
set -u
HERE=${0:A:h}
PY=~/.venvs/microduck-dyn/bin/python
OUT=$HERE/results/bisect_sit.jsonl
OLDM=~/sims/bvh-refit-20261029/plugged-20261019.json
: > $OUT
run() {  # label root manifest neck seed
  local label=$1 root=$2 man=$3 neck=$4 seed=$5
  local mac=$root/microduck-sim/guide/firmware/mac
  local line=$(cd $mac && $PY $HERE/stand_neck_run.py $neck brain_sim_check.py --model asbuilt --manifest $man --volt 7.0 \
      --drop 0.04 --walk-s 0 --sit-at 4 --unsit-at 10 --seed $seed 2>/dev/null | grep '^{' | tail -1)
  print -r -- "{\"label\": \"$label\", \"seed\": $seed, \"neck\": $neck, \"r\": ${line:-null}}" >> $OUT
}
RT=~/sims/bvh-refit-20261029/rt
NEWM=$RT/microduck-sim/microduck_rl/cmu/model/manifests/plugged.json
for seed in 0 1 2; do
  run now $RT $NEWM 0.25 $seed &
  run now_neck035 $RT $NEWM 0.35 $seed &
  run oldman $RT $OLDM 0.25 $seed &
  run oldman_neck035 $RT $OLDM 0.35 $seed &
  wait
  run t1020_oldman ~/sims/bvh-refit-20261029/var-t1020 $OLDM 0.35 $seed &
  run t1020_newman ~/sims/bvh-refit-20261029/var-t1020 $NEWM 0.35 $seed &
  wait
done
