#!/bin/zsh
# Round 2 cold-start study: run ts2_start_env.py on the Mac mini CPU under the mirror's lock, one job after the other
# (each under 10 min): the env as distilled, then the pinned standing start at COM x +10 mm and 0. No training.
#   zsh train/ts2_start_env.sh
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
run() {  # $1 output stem, rest: script arguments
  local stem=$1
  shift
  ssh mac-mini "cd $REMOTE/$RL && FLIGHT_MANIFESTS=\$HOME/$REMOTE/$FL/train/manifests zsh \$HOME/$REMOTE/$FL/train/mini_lock.sh run timeout 590 .venv/bin/python \$HOME/$REMOTE/$FL/train/ts2_start_env.py $* \
    --student-pt \$HOME/$REMOTE/$FL/train/ckpt/s2g_200/model_200.pt --teacher-onnx \$HOME/$REMOTE/smoke-assets/ts_teacher_x.onnx \
    --manifest \$HOME/$REMOTE/$FL/train/manifests/flightpack-none.json --audit \$HOME/$REMOTE/smoke-assets/existing-model-mass-audit.json \
    --out \$HOME/$REMOTE/$FL/train/eval/$stem.json 2>&1" > $T/logs/$stem.log || true
  grep -E "\[start_env\]|\[payload\]|\[mini_lock\]|Error|Traceback|assert" $T/logs/$stem.log | cut -c1-500 | head -12
}
# a cell whose record is already in eval/ is not run again
[ -f $T/eval/cz_start_env_dist.json ] || run cz_start_env_dist --phase dist
[ -f $T/eval/cz_start_env_comx10.json ] || run cz_start_env_comx10 --phase start --comx 0.010
[ -f $T/eval/cz_start_env_comx0.json ] || run cz_start_env_comx0 --phase start --comx 0.0
# head and body commands at zero, COM x as the runtime's comx+10 manifest gives it (trunk COM x -6.4 mm = +11.5 mm
# whole robot), and the same three drivers again with resets on the floor (--ground)
[ -f $T/eval/cz_start_env_g115.json ] || run cz_start_env_g115 --phase start --comx 0.0115 --ground
[ -f $T/eval/cz_start_env_g0.json ] || run cz_start_env_g0 --phase start --comx 0.0 --ground
zsh $T/mini.sh pull
