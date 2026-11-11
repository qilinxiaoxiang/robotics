#!/bin/zsh
# 2026-11-11 preparation jobs on the Mac mini, one at a time, each under 10 minutes (no training):
#   zsh train/prep_chain.sh audit      reward-redesign audit per load (runtime-style intended walker)
#   zsh train/prep_chain.sh probes     seeing-pick and quack reruns, bend statics, no-pack hand-back diff
LOCAL=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110
cd $LOCAL
zsh train/mini.sh push
zsh train/mini_train_smoke.sh push
case "$1" in
  audit)
    for L in full nobatt none; do
      zsh train/mini_train_smoke.sh audit2 $L 128 400 "" rt 2>&1 | grep -v "^busy" | grep -E "verdict|Traceback|Error"
    done
    ;;
  probes)
    zsh train/mini.sh run 'mkdir -p train/eval train/out && timeout 590 zsh train/style_probe.sh fixsp 20 8' 2>&1 | grep -v "^busy"
    zsh train/mini.sh run 'timeout 590 zsh train/style_probe.sh fixq 20 8' 2>&1 | grep -v "^busy"
    zsh train/mini.sh run 'timeout 590 $PY train/bend_statics.py --grid 9 --out train/out/bend_statics.json' 2>&1 | grep -v "^busy" | tail -8
    zsh train/mini.sh run 'timeout 590 $PY train/handback_diff.py --episodes 6 --out train/out/handback_diff.json' 2>&1 | grep -v "^busy" | tail -20
    zsh train/mini.sh pull
    rsync -a mac-mini:code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110/train/out/bend_statics.json \
      mac-mini:code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110/train/out/handback_diff.json train/out/ || true
    ;;
esac
