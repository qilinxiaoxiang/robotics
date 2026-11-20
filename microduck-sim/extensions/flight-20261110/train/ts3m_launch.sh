#!/bin/zsh
# Round 3 parallel arms: launch one teacher arm on Modal, detached (spawned call), A10.
#   zsh train/ts3m_launch.sh <run> <delta> <start onnx under /root/assets/init> <iters> <max hours> [seed]
# Prints the cost line and the "spawned" line; the call id is kept in microduck_rl/cmu/finetune/flight/.last_call_<run>.
set -e
RL=/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl
MODAL=/Users/xiangzheng/code/robotics/omx-local/.venv/bin/modal
LOG=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train/logs/launch_$1.log
cd $RL
FLIGHT_RUN=$1 FLIGHT_HOURS=$5 MICRODUCK_GPU=A10 $MODAL run --detach cmu/finetune/flight/flight_modal.py::run -- \
  --delta $2 --onnx /root/assets/init/$3 --manifest /root/assets/manifests/flightpack-none.json \
  --max-iters $4 --max-hours $5 --save-interval 125 --warmup-iters 100 --max-lr 0.0001 --guard-fraction 0.0 \
  --track-guard 2.0 --seed ${6:-1} ${@:7} > $LOG 2>&1   # further worker flags after the seed, e.g. --track-grace 1000
grep -E "rate \\$|spawned" $LOG | cut -c1-400
