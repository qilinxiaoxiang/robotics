#!/bin/zsh
# Training env switched toward the runtime simulation (RUNLOG 2026-11-18 separation study).
#   zsh train/ts_tsep.sh <case> <tag> [<tag> ...]
#     <case>  audit case run beside the intended walk: none | walk025 (vx 0.25 held, the runtime acceptance command)
#     <tag>   file train/delay/<tag>.json (flight_audit.py --delay-mods; {} = the env as trained)
# Per tag: the control arm at 750 (no pack) and 999 (full pack) and the start point at both loads in the teacher env
# (128 envs, 500 steps = 10 s) -> out/tsep_<name>_<load>_<tag>.json. Sampled commands as trained: out/teval_*.json.
set -e
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
CS=$1; shift
zsh $T/ts_round.sh push
for TG in "$@"; do
  [ -f $T/out/tsep_c750_none_$TG.json ] || zsh $T/ts_round.sh tdelay c750 $T/ckpt/tsc_750/walk61.onnx none $TG $T/delay/$TG.json $CS
  [ -f $T/out/tsep_c999_full_$TG.json ] || zsh $T/ts_round.sh tdelay c999 $T/ckpt/tsc_999/walk61.onnx full $TG $T/delay/$TG.json $CS
  [ -f $T/out/tsep_start_none_$TG.json ] || zsh $T/ts_round.sh tdelay start $T/ckpt/ts_start/walk61.onnx none $TG $T/delay/$TG.json $CS
  [ -f $T/out/tsep_start_full_$TG.json ] || zsh $T/ts_round.sh tdelay start $T/ckpt/ts_start/walk61.onnx full $TG $T/delay/$TG.json $CS
done
echo TSEPDONE
