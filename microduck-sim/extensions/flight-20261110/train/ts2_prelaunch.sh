#!/bin/zsh
# Round 2 pre-launch on the Mac mini (TEACHER-STUDENT-PLAN.md "Round 2"): teacher smoke with the loop-delay delta, then
# the incentive audit of each delta named, one load per job (stand still, shuffle, lean forward / back against the
# intended walk; 128 envs, 250 steps), recorded in out/audit_gate.json.
#   zsh train/ts2_prelaunch.sh [smoke] <delta> [<delta> ...]
set -e
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
CS=stand,shuffle,lean_fwd,lean_back
zsh $T/ts_round.sh push
zsh $T/ts_round.sh start $T/ckpt/ts_start/walk61.onnx
if [ "$1" = "smoke" ]; then
  shift
  zsh $T/ts_round.sh teacher 3 64 $1
fi
for DL in "$@"; do
  for LD in full nobatt none; do
    [ -f $T/out/audit_r2${DL}_${CS}_$LD.json ] || TSSTEPS=250 zsh $T/ts_round.sh audit $CS $LD r2$DL $T/rm_universal3.json $DL
  done
  python3 $T/audit_gate.py record $DL $T/out/audit_r2${DL}_${CS}_full.json $T/out/audit_r2${DL}_${CS}_nobatt.json $T/out/audit_r2${DL}_${CS}_none.json || true
done
echo PRELAUNCHDONE
