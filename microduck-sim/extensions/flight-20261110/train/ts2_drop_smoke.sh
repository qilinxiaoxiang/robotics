#!/bin/zsh
# Round 2: smoke of distill_worker.py --drop-max on the Mac mini CPU, under the mirror's lock (one job, under 10 min):
# three iterations of a Mamba student with dropped ticks, from scratch or resumed from a saved state.
#   zsh train/ts2_drop_smoke.sh scratch
#   zsh train/ts2_drop_smoke.sh resume <model_<iter>.pt> <iter>
set -e
LOCAL=/Users/xiangzheng/code/robotics/microduck-sim
REMOTE=code/flight-train-mirror/robotics/microduck-sim
RL=microduck_rl
FL=extensions/flight-20261110
T=$LOCAL/$FL/train
MODE=$1
source $T/ssh_guard.sh
zsh $T/mini.sh push
zsh $T/ts_round.sh push
rsync -a $T/ckpt/ts2a999_teacher/teacher.onnx mac-mini:$REMOTE/smoke-assets/ts_teacher_x.onnx
if [ "$MODE" = "resume" ]; then
  rsync -a "$2" mac-mini:$REMOTE/smoke-assets/ts_resume_drop.pt
  MORE="--resume-pt \$HOME/$REMOTE/smoke-assets/ts_resume_drop.pt --max-iters $(($3 + 4)) --warmup-iters 1 --lr 0.00025 --lr-final 0.00005"
else
  MORE="--max-iters 3 --warmup-iters 1 --beta-iters 1"
fi
ssh mac-mini "mkdir -p /tmp/ts_distill && cd $REMOTE/$RL && FLIGHT_MANIFESTS=\$HOME/$REMOTE/$FL/train/manifests zsh \$HOME/$REMOTE/$FL/train/mini_lock.sh run timeout 590 .venv/bin/python cmu/finetune/flight/flight_worker.py --distill \
  --run-name drop_$MODE --root /tmp/ts_distill --teacher-onnx \$HOME/$REMOTE/smoke-assets/ts_teacher_x.onnx --core mamba --device cpu --num-envs 64 \
  --drop-max 0.08 $MORE --bptt-steps 100 --delta universal4 --stop-after 100 \
  --save-interval 1 --mb-envs 32 --epochs 2 --max-hours 0.15 \
  --manifest \$HOME/$REMOTE/$FL/train/manifests/flightpack-none.json --audit \$HOME/$REMOTE/smoke-assets/existing-model-mass-audit.json 2>&1" \
  > $T/logs/drop_smoke_$MODE.log || true
grep -E "\[distill\]|\[cap\]|\[done\]|\[mini_lock\]|Error|Traceback|assert" $T/logs/drop_smoke_$MODE.log | cut -c1-330 | head -20
