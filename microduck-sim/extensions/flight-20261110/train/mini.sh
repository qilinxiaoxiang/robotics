#!/bin/zsh
# Mirror the probe code and this train folder to the Mac mini and run evaluations there (the MacBook swaps).
# Uses the existing flight-sim venv on the mini (mujoco 3.10.0, onnxruntime, bam; built by sim/mini.sh setup) read-only.
#   zsh train/mini.sh push            copy microduck_rl (code, models, manifests) + train/ to the mirror
#   zsh train/mini.sh run '<command>' run in the mirrored flight-20261110 folder; $PY is the venv python
#   zsh train/mini.sh pull            copy train/eval back
set -e
LOCAL=/Users/xiangzheng/code/robotics
REMOTE=code/flight-train-mirror/robotics
SIM=microduck-sim
RL=$SIM/microduck_rl
FL=$SIM/extensions/flight-20261110
VENV=.venvs/flight-sim
case "$1" in
  push)
    ssh mac-mini "mkdir -p $REMOTE/$RL $REMOTE/$FL/train"
    rsync -a $LOCAL/$SIM/CURRENT-STATE.json mac-mini:$REMOTE/$SIM/
    rsync -a --delete --exclude='.git' --exclude='.venv' --exclude='cmu/finetune' --exclude='cmu/hardware' \
      --exclude='cmu/simulator' --exclude='cmu/real-logs' --exclude='cmu/planning' --exclude='cmu/model/scans' \
      --exclude='__pycache__' $LOCAL/$RL/ mac-mini:$REMOTE/$RL/
    rsync -a --exclude='kaggle/out/' --exclude='eval/' --exclude='video/' $LOCAL/$FL/train/ mac-mini:$REMOTE/$FL/train/
    ;;
  run)
    ssh mac-mini "cd $REMOTE/$FL && PY=\$HOME/$VENV/bin/python && export PY && $2"
    ;;
  pull)
    mkdir -p $LOCAL/$FL/train/eval
    rsync -a mac-mini:$REMOTE/$FL/train/eval/ $LOCAL/$FL/train/eval/
    ;;
esac
