#!/bin/zsh
cd ~/code/robotics/microduck-sim/guide/firmware/mac
S=/private/tmp/claude-501/-Users-xiangzheng-code-robotics/e6cf309d-3d5a-4ae0-8f06-2a205f29db02/scratchpad/turn/c
B=(--model asbuilt --volt 7.0 --drop 0.04 --vx 0 --walk-at 3 --walk-s 25 --head-yaw 0 --head-pitch -0.75 --vtheta -0.5)
run() { name=$1; shift; ~/.venvs/microduck-dyn/bin/python brain_sim_check.py $B "$@" --tick-log $S/sim_$name.jsonl 2>/dev/null | tail -1 > $S/sim_$name.json; echo "$name done"; }
run mu2 --floor-mu 2.0
run mu3 --floor-mu 3.0
run soft --sole-solref 0.06 0.5
run playyaw5 --foot-play 5 --foot-play-axis yaw
run playyaw10 --foot-play 10 --foot-play-axis yaw
run playpitch6 --foot-play 6
run playroll6 --foot-play 6 --foot-play-axis roll
run fric3 --bam-friction-scale 3
