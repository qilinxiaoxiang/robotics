#!/bin/zsh
# Incentive audit of the teacher delta universal3t (TEACHER-STUDENT-PLAN.md): the 18 cases of the universal3 audit
# (NEXT-PLAN.md), one case per Mac mini job, the start policy as the intended walker. Results out/audit_ts_*.json,
# then the gate record. Cases already on disk are skipped.
set -e
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
for LD in full nobatt none; do
  for CS in stand shuffle lean_fwd lean_back; do
    [ -f $T/out/audit_ts_${CS}_$LD.json ] || zsh $T/ts_round.sh audit $CS $LD ts
  done
  for CS in stand shuffle; do
    [ -f $T/out/audit_tsfast_${CS}_$LD.json ] || zsh $T/ts_round.sh audit $CS $LD tsfast $T/rm_ts_fast.json
  done
done
cd $T && python3 audit_gate.py record universal3t out/audit_ts_*.json out/audit_tsfast_*.json
