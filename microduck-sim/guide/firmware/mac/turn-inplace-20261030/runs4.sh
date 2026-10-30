#!/bin/zsh
cd ~/code/robotics/microduck-sim/guide/firmware/mac
S=/private/tmp/claude-501/-Users-xiangzheng-code-robotics/e6cf309d-3d5a-4ae0-8f06-2a205f29db02/scratchpad/turn/d
B=(--model asbuilt --volt 7.0 --drop 0.04 --vx 0 --walk-at 3 --walk-s 25 --head-yaw 0 --head-pitch -0.75)
run() { name=$1; shift; ~/.venvs/microduck-dyn/bin/python brain_sim_check.py $B "$@" --tick-log $S/sim_$name.jsonl 2>/dev/null | tail -1 > $S/sim_$name.json; echo "$name done"; }
for t in 0.005 0.01 0.02 0.04; do run R_tors$t --vtheta -0.5 --sole-torsion $t; done
run L_tors0.02 --vtheta 0.5 --sole-torsion 0.02
