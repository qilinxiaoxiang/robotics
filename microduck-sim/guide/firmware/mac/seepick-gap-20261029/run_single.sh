#!/bin/zsh
# run_single.sh NAME [extra brain_sim_check flags]: one matched runtime episode of the centre box draw (box 15 x 15 x 14 mm,
# 3 g, mu 0.7, yaw 0, deterministic camera: delay 0.2 s, no drops, bias, noise or stalls; no read drops), the case the
# 2026-10-27 traces (traces-20261027/) compared against the training env. Trace to results/single/NAME.jsonl, the run's
# JSON to results/single/NAME.out. MacBook: one sim at a time (sim_host_guard).
set -u
HERE=${0:A:h}
MAC=$HERE/..
name=$1; shift
mkdir -p $HERE/results/single
cd $MAC
~/.venvs/microduck-dyn/bin/python brain_sim_check.py --model asbuilt --manifest ../../../microduck_rl/cmu/model/manifests/plugged.json \
  --com-x -2.25 --volt 7.0 --drop 0 --wired-guards --walk-s 0 --sp-at 4 --sp-shape box --sp-half 0.0075 0.0075 0.007 --sp-mass 3 \
  --sp-friction 0.7 --sp-object-yaw 0 --sp-camera-delay 0.2 --sp-camera-drop 0 --sp-camera-bias 0 0 --sp-camera-noise 0 \
  --sp-no-stalls --seed 0 --sp-trace $HERE/results/single/$name.jsonl "$@" > $HERE/results/single/$name.out 2>&1
echo "$name: $(grep -o '"held_ticks": [0-9]*' $HERE/results/single/$name.out | head -1) $(grep -o '"at_handback": {[^}]*}' $HERE/results/single/$name.out | head -1 | cut -c1-120)"
