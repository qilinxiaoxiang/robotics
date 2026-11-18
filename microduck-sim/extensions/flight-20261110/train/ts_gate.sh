#!/bin/zsh
# Teacher gate of TEACHER-STUDENT-PLAN.md section 6, after `kaggle_flight.py fetch ts-teach`.
#   zsh train/ts_gate.sh stage            teacher .pt -> ckpt/ts_teach_<iter>/teacher.onnx; control -> ckpt/tsc_<iter>/
#   zsh train/ts_gate.sh teval <iter>...  teacher and control at those iterations, the intended walk alone in the
#                                         teacher env at full / nobatt / none (out/teval_{t,c}<iter>_<load>.json)
#   zsh train/ts_gate.sh table            falls per env-minute, speed and torque-margin cost per checkpoint and load
set -e
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
RL=/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl
K=$T/kaggle/out/ts-teach/runs
case "$1" in
  stage)
    for PT in $K/ts-teach/model_[0-9]*.pt; do
      IT=${${PT:t:r}#model_}
      [ "$IT" = "0" ] && continue
      mkdir -p $T/ckpt/ts_teach_$IT
      $RL/.venv/bin/python $RL/cmu/finetune/modal/ckpt2onnx.py $PT $T/ckpt/ts_teach_$IT/teacher.onnx $K/ts-teach/model_0.onnx | tail -1 | cut -c1-80
    done
    python3 $T/screen_checkpoints.py stage ts-ctrl --kernel ts-teach --tag tsc | tail -3
    ;;
  teval)
    shift
    for IT in "$@"; do
      for LD in full nobatt none; do
        [ -f $T/out/teval_t${IT}_$LD.json ] || zsh $T/ts_round.sh teval t$IT $T/ckpt/ts_teach_$IT/teacher.onnx $LD
        [ -f $T/out/teval_c${IT}_$LD.json ] || zsh $T/ts_round.sh teval c$IT $T/ckpt/tsc_$IT/walk61.onnx $LD
      done
    done
    ;;
  table)
    python3 $T/ts_gate_table.py
    ;;
esac
