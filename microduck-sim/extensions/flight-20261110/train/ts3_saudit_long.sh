#!/bin/zsh
# Round 3, 2026-11-20: one longer rerun of the failing walk cell of the degenerate-policy audit (no pack, gain 400,
# command 0.25) to separate "the student does not walk there" from "5 s windows from a cold recurrent state".
# 48 envs x 750 steps (15 s). Runs ON the Mac mini, detached, under the mirror's lock; nothing is trained.
#   nohup zsh train/ts3_saudit_long.sh > /dev/null 2>&1 < /dev/null &
# Output train/out/saudit_long/student_audit_none_g2.0_c0.25.json, log train/logs/saudit_long_none_g2.0_c0.25.log,
# heartbeat train/logs/ts3_saudit_long_heartbeat.txt (last line DONE or FAILED).
M=$HOME/code/flight-train-mirror/robotics/microduck-sim
FL=$M/extensions/flight-20261110
A=$M/smoke-assets
MODELS=$M/microduck_rl/cmu/whole/runtime-overlay/models
HB=$FL/train/logs/ts3_saudit_long_heartbeat.txt
LOG=$FL/train/logs/saudit_long_none_g2.0_c0.25.log
mkdir -p $FL/train/out/saudit_long
hb() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*" >> $HB; }
hb "START pid $$"
cd $M/microduck_rl
export FLIGHT_MANIFESTS=$FL/train/manifests
zsh $FL/train/mini_lock.sh run timeout 590 .venv/bin/python cmu/finetune/flight/student_audit.py \
  --out $FL/train/out/saudit_long --load none --gain 2.0 --cmd 0.25 --teacher-onnx $A/ts3t_t3h_750.onnx \
  --student-pt $FL/train/ckpt/s3AB_140/model_140.pt --stand-onnx $MODELS/stand61.onnx --walk-onnx $MODELS/walk61.onnx \
  --gain-flag-col 59 --manifest $FL/train/manifests/flightpack-none.json --audit $A/existing-model-mass-audit.json \
  --num-envs 48 --steps 750 > $LOG 2>&1
RC=$?
V=$(grep -E "^\[saudit\] verdict" $LOG | cut -c1-400)
[ -z "$V" ] && { hb "FAILED exit $RC: $(grep -E 'Error|Traceback|assert' $LOG | tail -1 | cut -c1-300)"; exit 1; }
hb "exit $RC: $V"
hb "DONE"
