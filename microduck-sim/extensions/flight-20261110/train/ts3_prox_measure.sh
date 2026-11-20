#!/bin/zsh
# Round 3, 2026-11-20 08:45: how much of the student-driven training data is failure-proximal now, and how large
# the student's error to the teacher is there. Runs ON the Mac mini as one detached chain (nohup, parent 1), CPU,
# each stage under the mirror's lock and under 10 minutes. No learning: learning rate 0.
#   cd ~/code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110
#   nohup zsh train/ts3_prox_measure.sh > /dev/null 2>&1 < /dev/null &
# The student is run AB's save 140 (ckpt/s3AB_140/model_140.pt) under run AB's own sampler: env universal5, teacher
# t3h_750, case share 0.25, stop share 0.25, gain flag in column 59, dropped ticks to 0.08, action noise on half
# the envs. Iteration 141 is teacher-driven (the resume baseline), 142 onward student-driven; the [prox] line of the
# last save counts the student-driven rows only. Two seeds.
# Output /tmp/ts3_prox/seed<k>.log, heartbeat train/logs/ts3_prox_heartbeat.txt (last line DONE or FAILED).
M=$HOME/code/flight-train-mirror/robotics/microduck-sim
FL=$M/extensions/flight-20261110
A=$M/smoke-assets
LK=$FL/train/mini_lock.sh
OUT=/tmp/ts3_prox
HB=$FL/train/logs/ts3_prox_heartbeat.txt
mkdir -p $OUT $FL/train/logs
hb() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*" >> $HB; }
hb "START pid $$"
cd $M/microduck_rl
export FLIGHT_MANIFESTS=$FL/train/manifests
for SEED in 1 2; do
  zsh $LK run timeout 590 .venv/bin/python cmu/finetune/flight/flight_worker.py --distill --root $OUT \
    --teacher-onnx $A/ts3t_t3h_750.onnx --core mamba --device cpu --num-envs 512 --bptt-steps 100 --delta universal5 \
    --warmup-iters 1 --beta-iters 1 --epochs 2 --mb-envs 128 --drop-max 0.08 --stop-after 100000 \
    --manifest $FL/train/manifests/flightpack-none.json --audit $A/existing-model-mass-audit.json \
    --anchor-onnx $A/ts3_walk61.onnx --anchor-w 1.0 --anchor-head all --case-share 0.25 --stop-share 0.25 \
    --gain-flag-col 59 --prox-diag --run-name seed$SEED --seed $SEED --resume-pt $FL/train/ckpt/s3AB_140/model_140.pt \
    --max-iters 148 --save-interval 8 --lr 0 --lr-final 0 --max-hours 0.15 > $OUT/seed$SEED.log 2>&1
  RC=$?
  grep -qE "^\[prox\]" $OUT/seed$SEED.log || { hb "FAILED seed $SEED exit $RC: $(grep -E 'Error|Traceback' $OUT/seed$SEED.log | tail -1 | cut -c1-300)"; exit 1; }
  hb "seed $SEED exit $RC: $(grep -E '^\[cap\]' $OUT/seed$SEED.log | tail -1 | cut -c1-260)"
  cp $OUT/seed$SEED.log $FL/train/logs/ts3_prox_seed$SEED.log
done
hb "DONE"
