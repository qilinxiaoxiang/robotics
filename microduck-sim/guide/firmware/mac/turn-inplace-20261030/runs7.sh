#!/bin/zsh
cd ~/code/robotics/microduck-sim/guide/firmware/mac
S=${S:-./sim/tether}
B=(--model asbuilt --volt 7.0 --drop 0.04 --walk-at 3)
run() { name=$1; shift; ~/.venvs/microduck-dyn/bin/python brain_sim_check.py $B "$@" --tick-log $S/sim_$name.jsonl > $S/$name.out 2>&1; tail -1 $S/$name.out > $S/sim_$name.json; echo "$name done"; }
for seed in 0 1 2 3 4; do
run turnR_s$seed --vx 0 --vtheta -0.5 --walk-s 25 --tether --seed $seed
run walk_s$seed --vx 0.25 --walk-s 12 --tether --seed $seed
done
run walk_none --vx 0.25 --walk-s 12
