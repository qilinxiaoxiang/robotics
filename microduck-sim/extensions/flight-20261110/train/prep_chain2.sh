#!/bin/zsh
# 2026-11-11 remaining preparation jobs on the Mac mini, one at a time, each under 10 minutes (no training):
# seeing pick without the pack, quack reruns, no-pack hand-back diff, then the reward audit with the runtime command
# ranges (UNIVERSAL-PLAN.md section 4)
LOCAL=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110
cd $LOCAL
zsh train/mini.sh push
zsh train/mini_train_smoke.sh push
SP="--walk-at 1 --walk-s 0 --sp-at 2"
zsh train/mini.sh run "timeout 590 \$PY train/style_eval.py --name bend_sp_spec_none --models train/ckpt/bend_spec --manifest train/manifests/flightpack-load000.json --case stand --episodes 20 --workers 8 --extra=\"$SP\" --out train/eval/st_bend_sp_spec_none.json 2>&1 | tail -1" 2>&1 | grep -v "^busy" | cut -c1-400
zsh train/mini.sh run 'timeout 590 zsh train/style_probe.sh fixq 20 8' 2>&1 | grep -v "^busy" | cut -c1-400
zsh train/mini.sh run 'timeout 590 $PY train/handback_diff.py --episodes 6 --out train/out/handback_diff.json' 2>&1 | grep -v "^busy" | tail -20 | cut -c1-600
zsh train/mini.sh pull
rsync -a mac-mini:code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110/train/out/handback_diff.json train/out/ || true
RM='{"cmd_ranges":{"lin_vel_x":[-0.05,0.3],"lin_vel_y":[-0.05,0.05],"ang_vel_z":[-0.5,0.5]}}'
for L in full nobatt none; do
  zsh train/mini_train_smoke.sh audit2 $L 128 400 "$RM" cmd 2>&1 | grep -v "^busy" | grep -E "verdict|Traceback|Error" | cut -c1-500
done
