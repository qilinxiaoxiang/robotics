#!/bin/zsh
# Per-load probe for UNIVERSAL-PLAN.md, run on the Mac mini through mini.sh (never the MacBook):
#   zsh train/mini.sh push && zsh train/mini.sh run 'zsh train/payload_probe.sh <episodes>' && zsh train/mini.sh pull
# Policies: fq2 1999 (the with-pack choice, policy from the first tick) and today's stand61/walk61 (the runtime
# models, started as the no-pack robot starts today: --stand-s default 0.3 s open-loop stand). Loads: the six
# manifests from make_payload_manifests.py. Cases stand and walk. Output: train/eval/pl_<policy>_<load>_<case>.json
set -e
EP=${1:-20}
SPEC=../../microduck_rl/cmu/whole/runtime-overlay/models
for load in load000 load025 load050 nobatt load075 load100; do
  for c in walk stand; do
    $PY train/flight_eval.py --models train/ckpt/fq2_1999 --manifest train/manifests/flightpack-$load.json --case $c \
      --episodes $EP --workers 8 --extra="--stand-s 0" --out train/eval/pl_fq2_1999_${load}_$c.json 2>&1 | tail -1
    $PY train/flight_eval.py --models $SPEC --manifest train/manifests/flightpack-$load.json --case $c \
      --episodes $EP --workers 8 --out train/eval/pl_spec_${load}_$c.json 2>&1 | tail -1
  done
done
