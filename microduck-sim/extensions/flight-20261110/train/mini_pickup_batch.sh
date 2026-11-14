#!/bin/zsh
# Runs ON the Mac mini, started detached by pickup_batch.sh, so a sleeping MacBook cannot stall the tests.
# Pickup test (12 mm ball, 20 dev seeds, as pickup_ckpt.sh) for each job "<ckpt> <load> <delay>" given as arguments in
# triples; delay is "d44" (runtime default, about 44 ms sample to applied goal) or "sd0" (--sensor-delay 0, about 24 ms).
# One job at a time, each limited to 540 s. Results: train/eval/pk_<ckpt>[sd0]_<load>_ball.json, log train/eval/batch_<tag>.log
cd $HOME/code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110
PY=$HOME/.venvs/flight-sim/bin/python
TAG=$1; shift
LOG=train/eval/batch_$TAG.log
echo "START $(date +%H:%M:%S) $*" > $LOG
SP0="--stand-s 0 --walk-at 1 --walk-s 0 --wired-guards --sp-at 4 --sp-cone elliptic --sp-impratio 10 --sp-shape ball --sp-size 0.012"
while [ $# -ge 3 ]; do
  CK=$1; LD=$2; DL=$3; shift 3
  SP="$SP0"; R=$CK
  S0=0
  case "$DL" in *h) S0=100; DL=${DL%h};; esac    # a trailing h (d44h, sd0h): held-out seeds 100..119, names get "h"
  if [ "$DL" = "sd0" ]; then SP="$SP0 --sensor-delay 0"; R=${CK}sd0; fi
  [ $S0 -ne 0 ] && R=${R}h
  for i in $(seq 1 60); do zsh train/mini_busy.sh && break; sleep 10; done
  echo "== $R $LD $(date +%H:%M:%S)" >> $LOG
  perl -e 'alarm 540; exec @ARGV' $PY train/style_eval.py --name pk_${R}_${LD}_ball --models train/ckpt/$CK \
    --manifest train/manifests/flightpack-$LD.json --case stand --episodes 20 --seed0 $S0 --workers 8 --extra="$SP" \
    --out train/eval/pk_${R}_${LD}_ball.json > /dev/null 2>&1
  echo "   exit $? $(date +%H:%M:%S)" >> $LOG
done
echo "ALL DONE $(date +%H:%M:%S)" >> $LOG
