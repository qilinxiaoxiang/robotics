#!/bin/zsh
# Round 2: after `kaggle_flight.py fetch <kernel run>`, turn every saved checkpoint of a run into a runtime models
# folder for ts2_pick.py (walk61.onnx + stand61.onnx, the same file; a teacher keeps its 68 inputs).
#   zsh train/ts2_stage.sh <kernel run> <run> <tag>     e.g.  ts2-teach ts2-teach t2a  ->  ckpt/t2a_<iter>/
# Prints the folder names, oldest first.
set -e
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
RL=/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl
K=$T/kaggle/out/$1/runs/$2
TAG=$3
for PT in $(ls $K/model_[0-9]*.pt | sort -t_ -k2 -n); do
  IT=${${PT:t:r}#model_}
  [ "$IT" = "0" ] && continue
  D=$T/ckpt/${TAG}_$IT
  mkdir -p $D
  # a fourth argument names the template ONNX and rebuilds existing files: a one-frame run's model_0.onnx carries no
  # metadata (KeyError 'observation_names' in the runtime, 2026-11-18), its start policy ckpt/ts_start/walk61.onnx does
  if [ ! -f $D/walk61.onnx ] || [ -n "$4" ]; then
    $RL/.venv/bin/python $RL/cmu/finetune/modal/ckpt2onnx.py $PT $D/walk61.onnx ${4:-$K/model_0.onnx} > $D/ckpt2onnx.log 2>&1
    cp $D/walk61.onnx $D/stand61.onnx
  fi
  echo ${TAG}_$IT
done
