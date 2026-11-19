#!/bin/zsh
# Round 2 cause study, check 3: run ts2_parity_env.py (the distillation env's observation around a held tick) on the
# Mac mini CPU under the mirror's lock (one job, under 10 min), then copy the record back to eval/.
#   zsh train/ts2_parity_env.sh
set -e
LOCAL=/Users/xiangzheng/code/robotics/microduck-sim
REMOTE=code/flight-train-mirror/robotics/microduck-sim
RL=microduck_rl
FL=extensions/flight-20261110
T=$LOCAL/$FL/train
source $T/ssh_guard.sh
zsh $T/mini.sh push
zsh $T/ts_round.sh push
rsync -a $T/ckpt/ts2a999_teacher/teacher.onnx mac-mini:$REMOTE/smoke-assets/ts_teacher_x.onnx
ssh mac-mini "cd $REMOTE/$RL && FLIGHT_MANIFESTS=\$HOME/$REMOTE/$FL/train/manifests zsh \$HOME/$REMOTE/$FL/train/mini_lock.sh run timeout 590 .venv/bin/python \$HOME/$REMOTE/$FL/train/ts2_parity_env.py \
  --teacher-onnx \$HOME/$REMOTE/smoke-assets/ts_teacher_x.onnx \
  --manifest \$HOME/$REMOTE/$FL/train/manifests/flightpack-none.json --audit \$HOME/$REMOTE/smoke-assets/existing-model-mass-audit.json \
  --out \$HOME/$REMOTE/$FL/train/eval/cz_parity_env.json 2>&1" > $T/logs/ts2_parity_env.log || true
grep -E "\[parity_env\]|\[delay\]|\[mini_lock\]|Error|Traceback|assert" $T/logs/ts2_parity_env.log | cut -c1-400 | head -20
zsh $T/mini.sh pull
