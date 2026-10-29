#!/bin/zsh
# bisect_com5.sh: the sim_suite real case com+5 (asbuilt 10-15 manifest, COM 5 mm forward, 7.0 V, 4 % drops, 10 s walk)
# against the open-loop stand neck (D-030 0.25 vs NEUTRAL 0.35), a COM sweep, and the plugged (saddle) manifest the
# D-030 study calibrated. One JSON summary line per run to results/bisect_com5.jsonl. Mac mini.
set -u
HERE=${0:A:h}
MAC=$HERE/..
PY=~/.venvs/microduck-dyn/bin/python
OUT=$HERE/results/bisect_com5.jsonl
: > $OUT
cd $MAC
run() {  # label neck args...
  local label=$1 neck=$2; shift 2
  local line=$($PY $HERE/stand_neck_run.py $neck brain_sim_check.py --model asbuilt --walk-s 10 --volt 7.0 --drop 0.04 "$@" 2>/dev/null | grep '^{' | tail -1)
  print -r -- "{\"label\": \"$label\", \"neck\": $neck, \"args\": \"$*\", \"r\": $line}" >> $OUT
}
for neck in 0.25 0.35; do
  for com in 0 2 3 4 5; do
    # the asbuilt config names this manifest by an absolute MacBook path; the same file, named here for the Mac mini
    run asbuilt_com$com $neck --manifest ../../../hardware-design-20260912/whole-robot-20260912/dynamics/asbuilt-20261015/asbuilt-mass-manifest.json --com-x $com &
  done
  wait
done
# plugged manifest (saddle, D-030 calibration): robot COM = model -2.25 mm; +5 mm from there is --com-x 2.75
for neck in 0.25 0.35; do
  for com in -2.25 0.75 2.75; do
    run plugged_com$com $neck --manifest ../../../microduck_rl/cmu/model/manifests/plugged.json --com-x $com &
  done
  wait
done
