#!/bin/zsh
# Mirror the flight-simulation inputs to the Mac mini and run there (heavy-compute rule: the MacBook swaps).
# Edits stay on the MacBook; the mirror is disposable.
#   zsh sim/mini.sh setup              create the venv on the mini (python 3.12, mujoco 3.10.0, onnxruntime 1.24.4, bam)
#   zsh sim/mini.sh push               copy inputs (rsync, only changed files)
#   zsh sim/mini.sh run '<command>'    run in the mirrored flight-20261110 folder; $PY is the mini venv python
#   zsh sim/mini.sh pull               copy sim/out back
set -e
LOCAL=/Users/xiangzheng/code/robotics
REMOTE=code/flight-sim-mirror/robotics
SIM=microduck-sim
RL=$SIM/microduck_rl
FL=$SIM/extensions/flight-20261110
VENV=.venvs/flight-sim
case "$1" in
  setup)
    ssh mac-mini "/opt/homebrew/bin/uv venv --python 3.12 $VENV && /opt/homebrew/bin/uv pip install --python $VENV/bin/python mujoco==3.10.0 onnxruntime==1.24.4 numpy==2.4.1 scipy==1.18.0 imageio==2.37.2 imageio-ffmpeg==0.6.0 pillow"
    rsync -a --delete $LOCAL/$RL/.venv/lib/python3.12/site-packages/bam/ mac-mini:$VENV/lib/python3.12/site-packages/bam/
    ;;
  push)
    ssh mac-mini "mkdir -p $REMOTE/$RL $REMOTE/$FL"
    rsync -a $LOCAL/$SIM/CURRENT-STATE.json mac-mini:$REMOTE/$SIM/
    rsync -a --delete --exclude='.git' --exclude='.venv' --exclude='cmu/finetune' --exclude='cmu/hardware' \
      --exclude='cmu/simulator' --exclude='cmu/real-logs' --exclude='cmu/planning' --exclude='cmu/model/scans' \
      --exclude='__pycache__' $LOCAL/$RL/ mac-mini:$REMOTE/$RL/
    rsync -a --exclude='*.html' --exclude='duck_mesh.json' --exclude='duck_poses.json' --exclude='cad/build/pose_clouds.npz' \
      --exclude='sim/out/' --exclude='wiring/' $LOCAL/$FL/ mac-mini:$REMOTE/$FL/
    ;;
  run)
    ssh mac-mini "cd $REMOTE/$FL && PY=\$HOME/$VENV/bin/python && export PY && $2"
    ;;
  pull)
    mkdir -p $LOCAL/$FL/sim/out
    rsync -a mac-mini:$REMOTE/$FL/sim/out/ $LOCAL/$FL/sim/out/
    ;;
esac
