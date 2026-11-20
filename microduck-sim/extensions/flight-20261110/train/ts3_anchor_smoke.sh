#!/bin/zsh
# Round 3, 2026-11-20: smoke of the walk61 anchor in distillation. Runs ON the Mac mini as one detached chain
# (nohup, parent 1), CPU only, every stage under the mirror's lock and under 10 minutes; heartbeat after each stage.
#   nohup zsh train/ts3_anchor_smoke.sh <tag> <stages> <anchor w> <anchor head> <case share> [lr] > /dev/null 2>&1 &
# Continues the trained student s3h_160 (smoke-assets/s3h_160.pt, distilled from t3h_750 in env universal5) with
# the same teacher, so a few iterations show what the anchor does to an already trained student:
#   stage 0   3 iterations with learning rate 0 and the anchor only measured (w 0): the student as it is
#   stage 1+  <stages> stages of at most 9 minutes each with the anchor, each resuming the last save
# Output: /tmp/ts3_anchor_<tag>/ (model_<it>.pt / .onnx, progress.csv with "by_load"), heartbeat
# ~/code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110/train/logs/ts3_anchor_<tag>_heartbeat.txt
TAG=$1; STAGES=$2; W=$3; HEADROWS=$4; SHARE=$5; LR=${6:-0.0005}
M=$HOME/code/flight-train-mirror/robotics/microduck-sim
FL=$M/extensions/flight-20261110
A=$M/smoke-assets
LK=$FL/train/mini_lock.sh
OUT=/tmp/ts3_anchor_$TAG
HB=$FL/train/logs/ts3_anchor_${TAG}_heartbeat.txt
mkdir -p $OUT $FL/train/logs
hb() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*" >> $HB; }
hb "START tag $TAG stages $STAGES anchor w $W head rows $HEADROWS case share $SHARE lr $LR pid $$"
cd $M/microduck_rl
# TSTEACHER=<onnx> another teacher, TSDELTA=<delta> another env (the full run's: m3s_450 and universal5c)
COMMON=(--distill --root $OUT --teacher-onnx ${TSTEACHER:-$A/ts3t_t3h_750.onnx} --core mamba --device cpu --num-envs 512
  --bptt-steps 100 --delta ${TSDELTA:-universal5} --warmup-iters 0 --beta-iters 1 --epochs 2 --mb-envs 128 --drop-max 0.08
  --stop-after 100000 --manifest $FL/train/manifests/flightpack-none.json --audit $A/existing-model-mass-audit.json
  --anchor-onnx $A/ts3_walk61.onnx)
export FLIGHT_MANIFESTS=$FL/train/manifests
# stage 0: the student as it is
zsh $LK run timeout 590 .venv/bin/python cmu/finetune/flight/flight_worker.py $COMMON --run-name base \
  --resume-pt ${TSBASEPT:-$A/s3h_160.pt} --max-iters ${TSBASEMAX:-163} --save-interval ${TSBASEN:-3} --lr 0 --lr-final 0 --anchor-w 0 ${=TSEXTRA} \
  --case-share $SHARE --max-hours 0.15 > $OUT/stage0.log 2>&1
hb "stage 0 exit $?: $(grep -E '^\[load\]' $OUT/stage0.log | tail -1 | cut -c1-600)"
grep -qE "Traceback|Error" $OUT/stage0.log && { hb "FAILED stage 0: $(grep -E 'Error' $OUT/stage0.log | tail -1 | cut -c1-300)"; exit 1; }
hb "stage 0 stop rows: $(grep -E '^\[stop\]' $OUT/stage0.log | tail -1 | cut -c1-1500)"
# TSBASEPT / TSBASEMAX / TSBASEN: stage 0's student save, last iteration and save interval; TSEXTRA: extra worker
# flags for every stage; <stages> 0 = stage 0 only
[ "$STAGES" = 0 ] && { hb "DONE stage 0 only"; exit 0; }
PT=${TSPT:-$A/s3h_160.pt}   # TSPT=<model_<it>.pt> continues another smoke's save; TSZERO=1 zeroes the head command
ZH=(); [ -n "$TSZERO" ] && ZH=(--anchor-zero-head)   # in the anchor target (smoke a1 ran that way, then the default)
for S in $(seq 1 $STAGES); do
  zsh $LK run timeout 590 .venv/bin/python cmu/finetune/flight/flight_worker.py $COMMON --run-name anch \
    --resume-pt $PT --max-iters 400 --save-interval 2 --lr $LR --lr-final $LR --anchor-w $W --anchor-head $HEADROWS \
    --case-share $SHARE --max-hours 0.13 $ZH ${=TSEXTRA} > $OUT/stage$S.log 2>&1
  RC=$?
  hb "stage $S stop rows: $(grep -E '^\[stop\]' $OUT/stage$S.log | tail -1 | cut -c1-1500)"
  LAST=$(ls $OUT/anch/model_*.pt 2>/dev/null | grep -v best | sed -E 's/.*model_([0-9]+)\.pt/\1/' | sort -n | tail -1)
  hb "stage $S exit $RC last save $LAST: $(grep -E '^\[load\]' $OUT/stage$S.log | tail -1 | cut -c1-600)"
  hb "stage $S speed: $(grep -E '^\[cap\]' $OUT/stage$S.log | tail -1 | cut -c1-200)"
  [ -z "$LAST" ] && { hb "FAILED stage $S: no save ($(grep -E 'Error|Traceback' $OUT/stage$S.log | tail -1 | cut -c1-300))"; exit 1; }
  PT=$OUT/anch/model_$LAST.pt
done
hb "DONE last save $LAST"
