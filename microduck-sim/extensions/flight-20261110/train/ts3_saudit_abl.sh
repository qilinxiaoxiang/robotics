#!/bin/zsh
# Round 3, 2026-11-20: why does the gate episode have s3AB_140 walking at no pack / gain 400 (0 falls, 0.073 m/s)
# while the audit env (student_audit.py, universal5) has it not walking? Stage "flag" prints what the student's gain
# flag column holds in the audit's own setting. Then the cell is rerun with every env disturbance off and a 2 s
# stand61 lead-in (the gate episode's shape), and the disturbances are switched on one at a time.
# Runs ON the Mac mini, detached, one stage at a time under the mirror's lock; nothing is trained.
#   nohup zsh train/ts3_saudit_abl.sh > /dev/null 2>&1 < /dev/null &
# Output train/out/saudit_abl/student_audit_none_g2.0_c0.25_<stage>.json, logs train/logs/saudit_abl_<stage>.log,
# heartbeat train/logs/ts3_saudit_abl_heartbeat.txt (last line DONE or FAILED).
M=$HOME/code/flight-train-mirror/robotics/microduck-sim
FL=$M/extensions/flight-20261110
A=$M/smoke-assets
MODELS=$M/microduck_rl/cmu/whole/runtime-overlay/models
HB=$FL/train/logs/ts3_saudit_abl_heartbeat.txt
mkdir -p $FL/train/out/saudit_abl
hb() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*" >> $HB; }
hb "START pid $$"
cd $M/microduck_rl
export FLIGHT_MANIFESTS=$FL/train/manifests
OFF="--no-push --no-dr --no-noise --no-delay --fixed-head"
run() {  # run <stage> <envs> <steps> <flags...>
  local S=$1 E=$2 T=$3; shift 3
  local LOG=$FL/train/logs/saudit_abl_$S.log
  zsh $FL/train/mini_lock.sh run timeout 590 .venv/bin/python cmu/finetune/flight/student_audit.py \
    --out $FL/train/out/saudit_abl --load none --gain 2.0 --cmd 0.25 --teacher-onnx $A/ts3t_t3h_750.onnx \
    --student-pt $FL/train/ckpt/s3AB_140/model_140.pt --stand-onnx $MODELS/stand61.onnx --walk-onnx $MODELS/walk61.onnx \
    --gain-flag-col 59 --manifest $FL/train/manifests/flightpack-none.json --audit $A/existing-model-mass-audit.json \
    --policies student,teacher --tag _$S --num-envs $E --steps $T "$@" > $LOG 2>&1
  local RC=$?
  if ! grep -q "subset done" $LOG; then
    hb "FAILED stage $S exit $RC: $(grep -E 'Error|Traceback|assert' $LOG | tail -1 | cut -c1-300)"; exit 1
  fi
  hb "stage $S exit $RC: $(grep -E '^\[saudit\] (flag|none)' $LOG | cut -c1-330 | tr '\n' '|')"
}
[ -z "$SKIPFLAG" ] && run flag 16 130 --print-flag
run a0_alloff_lead 64 750 ${=OFF} --lead-in-s 2
run a1_push 64 750 --no-dr --no-noise --no-delay --fixed-head --lead-in-s 2
run a2_dr 64 750 --no-push --no-noise --no-delay --fixed-head --lead-in-s 2
run a3_noise 64 750 --no-push --no-dr --no-delay --fixed-head --lead-in-s 2
run a4_delay 64 750 --no-push --no-dr --no-noise --fixed-head --lead-in-s 2
run a5_head 64 750 --no-push --no-dr --no-noise --no-delay --lead-in-s 2
run a6_alloff_nolead 64 750 ${=OFF}
run a7_allon_lead 64 750 --lead-in-s 2
hb "DONE"
