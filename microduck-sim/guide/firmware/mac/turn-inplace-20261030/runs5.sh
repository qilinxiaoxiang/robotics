#!/bin/zsh
cd ~/code/robotics/microduck-sim/guide/firmware/mac
S=/private/tmp/claude-501/-Users-xiangzheng-code-robotics/e6cf309d-3d5a-4ae0-8f06-2a205f29db02/scratchpad/turn/e
B=(--model asbuilt --volt 7.0 --drop 0.04 --vx 0 --walk-at 3 --walk-s 25 --head-yaw 0 --head-pitch -0.75)
run() { name=$1; shift; ~/.venvs/microduck-dyn/bin/python brain_sim_check.py $B "$@" --tick-log $S/sim_$name.jsonl 2>/dev/null | tail -1 > $S/sim_$name.json; echo "$name done"; }
for k in 0.005 0.01 0.02; do run R_spring$k --vtheta -0.5 --yaw-spring $k; done
run L_spring0.01 --vtheta 0.5 --yaw-spring 0.01
