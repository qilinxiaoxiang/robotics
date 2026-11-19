#!/bin/zsh
# Runs ON the Mac mini in the mirrored flight-20261110 folder (zsh train/mini.sh run 'zsh train/ts3_like.sh [extra probe flags]').
# Like-for-like with the robot fall of 2026-11-19: no pack, stand mode then walk mode at zero command for the whole
# episode (case stand), one seed, a tick log per policy, then the an2.py statistics (ts3_chatter_stats.py).
# TAG names the output set; extra probe flags (a simulation condition) are passed through to brain_sim_check.
TAG=${TAG:-base}
EXTRA="$*"
OUT=train/out/chatter
mkdir -p $OUT
for M in s2r6_4 walk61; do
  if [ $M = walk61 ]; then DIR=../../microduck_rl/cmu/whole/runtime-overlay/models; else DIR=train/ckpt/$M; fi
  $PY train/flight_eval.py --models $DIR --manifest train/manifests/flightpack-none.json --case stand --episodes 1 --workers 1 \
    --out $OUT/like_${TAG}_$M.json --extra "$EXTRA --tick-log $OUT/like_${TAG}_$M.jsonl" | cut -c1-400
done
$PY train/ts3_chatter_stats.py $OUT/like_${TAG}_s2r6_4.jsonl $OUT/like_${TAG}_walk61.jsonl --out $OUT/like_${TAG}_stats.json
