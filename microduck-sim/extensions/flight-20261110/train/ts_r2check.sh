#!/bin/zsh
# Round 2, step 1 (TEACHER-STUDENT-PLAN.md "Round 2"): does the training env with a given loop delay reproduce the
# runtime simulation's ordering at full pack (start point holds, tsc_999 falls)?
#   zsh train/ts_r2check.sh <tag> [<tag> ...]      tag = file train/delay/<tag>.json (flight_audit.py --delay-mods)
# Per tag: tsc_999 and the start point at full pack, vx 0.25 held (case walk025) beside the env's sampled commands
# -> out/tsep_c999_full_<tag>.json, out/tsep_start_full_<tag>.json. One Mac mini job at a time, each under 10 minutes.
set -e
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
zsh $T/ts_round.sh push
for TG in "$@"; do
  [ -f $T/out/tsep_c999_full_$TG.json ] || zsh $T/ts_round.sh tdelay c999 $T/ckpt/tsc_999/walk61.onnx full $TG $T/delay/$TG.json walk025
  [ -f $T/out/tsep_start_full_$TG.json ] || zsh $T/ts_round.sh tdelay start $T/ckpt/ts_start/walk61.onnx full $TG $T/delay/$TG.json walk025
done
echo R2CHECKDONE
