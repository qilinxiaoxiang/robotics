#!/bin/zsh
# Round 2: smoke of distill_worker.py --resume-pt on the Mac mini CPU (under 10 minutes): continue a saved student for
# two iterations past its saved iteration and print the worker's lines.
#   zsh train/ts2_resume_smoke.sh <lstm|mamba> <model_<iter>.pt> <iter>
set -e
LOCAL=/Users/xiangzheng/code/robotics/microduck-sim
REMOTE=code/flight-train-mirror/robotics/microduck-sim
RL=microduck_rl
FL=extensions/flight-20261110
T=$LOCAL/$FL/train
CORE=$1
IT=$3
source $T/ssh_guard.sh
zsh $T/ts_round.sh push
rsync -a "$2" mac-mini:$REMOTE/smoke-assets/ts_resume_$CORE.pt
rsync -a $T/ckpt/ts2a999_teacher/teacher.onnx mac-mini:$REMOTE/smoke-assets/ts_teacher_x.onnx
ssh mac-mini "mkdir -p /tmp/ts_distill && cd $REMOTE/$RL && FLIGHT_MANIFESTS=\$HOME/$REMOTE/$FL/train/manifests zsh \$HOME/$REMOTE/$FL/train/mini_lock.sh run timeout 590 .venv/bin/python cmu/finetune/flight/flight_worker.py --distill \
  --run-name resume_$CORE --root /tmp/ts_distill --teacher-onnx \$HOME/$REMOTE/smoke-assets/ts_teacher_x.onnx --core $CORE --device cpu --num-envs 64 \
  --resume-pt \$HOME/$REMOTE/smoke-assets/ts_resume_$CORE.pt --max-iters $((IT + 3)) --bptt-steps 100 --delta universal4 --warmup-iters 1 \
  --save-interval 1 --mb-envs 32 --epochs 2 --lr 0.00025 --lr-final 0.00005 --max-hours 0.15 \
  --manifest \$HOME/$REMOTE/$FL/train/manifests/flightpack-none.json --audit \$HOME/$REMOTE/smoke-assets/existing-model-mass-audit.json 2>&1" \
  > $T/logs/resume_smoke_$CORE.log || true
grep -E "\[distill\]|\[cap\]|\[done\]|Error|Traceback|assert" $T/logs/resume_smoke_$CORE.log | cut -c1-420 | head -20
