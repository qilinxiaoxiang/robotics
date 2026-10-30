#!/bin/zsh
cd ~/code/robotics/microduck-sim/guide/firmware/mac
S=/private/tmp/claude-501/-Users-xiangzheng-code-robotics/e6cf309d-3d5a-4ae0-8f06-2a205f29db02/scratchpad/turn
B=(--model asbuilt --volt 7.0 --drop 0.04 --vx 0 --walk-at 3 --walk-s 25)
run() { name=$1; shift; ~/.venvs/microduck-dyn/bin/python brain_sim_check.py $B "$@" --tick-log $S/sim_$name.jsonl 2>/dev/null | tail -1 > $S/sim_$name.json; echo "$name done"; }
for seed in 0 1; do
run R_headdef_s$seed --vtheta -0.5 --seed $seed
run R_head075_s$seed --vtheta -0.5 --head-yaw 0 --head-pitch -0.75 --seed $seed
run L_head025_s$seed --vtheta 0.5 --head-yaw 0 --head-pitch -0.25 --seed $seed
run R_head075_drift_s$seed --vtheta -0.5 --head-yaw 0 --head-pitch -0.75 --imu-pitch 4 --yaw-torque 0.020 --seed $seed
run R_head075_mu05_s$seed --vtheta -0.5 --head-yaw 0 --head-pitch -0.75 --floor-mu 0.5 --seed $seed
run R_head075_fric15_s$seed --vtheta -0.5 --head-yaw 0 --head-pitch -0.75 --bam-friction-scale 1.5 --seed $seed
done
