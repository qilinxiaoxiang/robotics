#!/bin/zsh
# Round 3, 2026-11-20: degenerate-policy audit before PPO on the distilled student (student_audit.py). Runs ON the
# Mac mini as one detached chain (nohup, parent 1), CPU, one cell per stage under the mirror's lock, each under 10
# minutes. Nothing is trained and no reward is changed.
#   cd ~/code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110
#   nohup zsh train/ts3_saudit_chain.sh > /dev/null 2>&1 < /dev/null &
# Cells: load none / full x gain scale 1.0 / 2.0 (KP 200 / 400) x forward command 0 / 0.25 in env universal5.
# Output train/out/student_audit_<load>_g<gain>_c<cmd>.json, logs train/logs/saudit_<cell>.log, heartbeat
# train/logs/ts3_saudit_heartbeat.txt (last line DONE or FAILED).
M=$HOME/code/flight-train-mirror/robotics/microduck-sim
FL=$M/extensions/flight-20261110
A=$M/smoke-assets
MODELS=$M/microduck_rl/cmu/whole/runtime-overlay/models
LK=$FL/train/mini_lock.sh
HB=$FL/train/logs/ts3_saudit_heartbeat.txt
mkdir -p $FL/train/out $FL/train/logs
hb() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*" >> $HB; }
hb "START pid $$"
cd $M/microduck_rl
export FLIGHT_MANIFESTS=$FL/train/manifests
for LOAD in full none; do for GAIN in 1.0 2.0; do for CMD in 0.25 0.0; do
  CELL=${LOAD}_g${GAIN}_c${CMD}
  zsh $LK run timeout 590 .venv/bin/python cmu/finetune/flight/student_audit.py --out $FL/train/out --load $LOAD \
    --gain $GAIN --cmd $CMD --teacher-onnx $A/ts3t_t3h_750.onnx --student-pt $FL/train/ckpt/s3AB_140/model_140.pt \
    --stand-onnx $MODELS/stand61.onnx --walk-onnx $MODELS/walk61.onnx --gain-flag-col 59 \
    --manifest $FL/train/manifests/flightpack-none.json --audit $A/existing-model-mass-audit.json \
    --num-envs ${SAENVS:-96} --steps ${SASTEPS:-250} > $FL/train/logs/saudit_$CELL.log 2>&1
  RC=$?
  V=$(grep -E "^\[saudit\] verdict" $FL/train/logs/saudit_$CELL.log | cut -c1-400)
  [ -z "$V" ] && { hb "FAILED cell $CELL exit $RC: $(grep -E 'Error|Traceback|assert' $FL/train/logs/saudit_$CELL.log | tail -1 | cut -c1-300)"; exit 1; }
  hb "cell $CELL exit $RC: $V"
done; done; done
hb "DONE"
