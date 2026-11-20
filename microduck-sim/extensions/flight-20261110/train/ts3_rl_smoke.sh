#!/bin/zsh
# Round 3, 2026-11-20: smoke of PPO on the distilled student with the imitation term kept (distill_worker --rl-w).
# Runs ON the Mac mini as one detached chain (nohup, parent 1), CPU only, every stage under the mirror's lock and
# under 10 minutes; heartbeat after each stage.
#   cd ~/code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110
#   nohup zsh train/ts3_rl_smoke.sh > /dev/null 2>&1 < /dev/null &
# Start: run AB's save 140 (ckpt/s3AB_140/model_140.pt), env universal5 (the teacher's rewards, unchanged), teacher
# t3h_750, student inputs as s3AB (gain flag in column 59, no pack flag), case share 0.25, stop share 0.25.
#   stage 0   5 iterations, student learning rate 0, PPO rollouts on (action std 0.1 on every student env): the
#             start's falls and imitation error under the PPO rollout's own noise, and the critic's first fit
#   chains    f1 f2 = imitation 0.5 + PPO 0.5 fixed (seeds 1, 2); a1 a2 = imitation 0.5 -> 0.1 over the three
#             stages + PPO 0.5 (seeds 1, 2). Each: 3 stages of at most 9 minutes resuming the last save, lr 1e-4,
#             clip 0.1. Then the gate cells s3AB_140 fails or must keep, on the last save (10 seeds each): pack
#             walk at gain 200 and 400, no pack standing at gain 400.
#   zcmd      coordinator's addition 09:31: stepping at a zero command (footfalls, action step per tick) in the
#             training env for no pack / pack x gain 200 / 400, for the start and each chain's last save, two env
#             seeds each -> train/out/rl_zcmd/, logs train/logs/ts3_rl_zcmd_*.log, one heartbeat line each.
# Output /tmp/ts3_rl/<tag>/ (model_<it>.pt/.onnx, progress.csv), stage logs /tmp/ts3_rl/<tag>_stage<k>.log (copied to
# train/logs/ts3_rl_<tag>_stage<k>.log), cells train/logs/ts3_rl_<tag>_cells.out, heartbeat
# train/logs/ts3_rl_heartbeat.txt (last line DONE or FAILED).
M=$HOME/code/flight-train-mirror/robotics/microduck-sim
FL=$M/extensions/flight-20261110
A=$M/smoke-assets
LK=$FL/train/mini_lock.sh
PY=$HOME/.venvs/flight-sim/bin/python
OUT=/tmp/ts3_rl
HB=$FL/train/logs/ts3_rl_heartbeat.txt
mkdir -p $OUT $FL/train/logs
hb() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*" >> $HB; }
hb "START pid $$"
export FLIGHT_MANIFESTS=$FL/train/manifests
COMMON=(--distill --root $OUT --teacher-onnx $A/ts3t_t3h_750.onnx --core mamba --device cpu --num-envs 512
  --bptt-steps 100 --delta universal5 --warmup-iters 0 --beta-iters 1 --epochs 2 --mb-envs 128 --drop-max 0.08
  --stop-after 100000 --manifest $FL/train/manifests/flightpack-none.json --audit $A/existing-model-mass-audit.json
  --anchor-onnx $A/ts3_walk61.onnx --anchor-w 1.0 --anchor-head all --case-share 0.25 --stop-share 0.25
  --gain-flag-col 59 --rl-w 0.5 --rl-clip 0.1 --rl-std 0.1)
stage() {  # stage <log name> <worker flags...>
  local name=$1; shift
  cd $M/microduck_rl
  zsh $LK run timeout 590 .venv/bin/python cmu/finetune/flight/flight_worker.py $COMMON "$@" > $OUT/$name.log 2>&1
  local rc=$?
  cp $OUT/$name.log $FL/train/logs/ts3_rl_$name.log
  hb "$name exit $rc: $(grep -E '^\[cap\]' $OUT/$name.log | tail -1 | cut -c1-330)"
  hb "$name rl: $(grep -E '^\[rl\] it' $OUT/$name.log | tail -1 | cut -c1-420)"
  grep -qE "Traceback|Error" $OUT/$name.log && { hb "FAILED $name: $(grep -E 'Error' $OUT/$name.log | tail -1 | cut -c1-300)"; exit 1; }
  return 0
}
MODELS=$M/microduck_rl/cmu/whole/runtime-overlay/models
zcmd() {  # zcmd <label> <student .pt>: stepping at a ZERO command in the training env (student_audit.py, student only),
          # no pack / pack x gain 200 / 400, seeds 1 and 2: footfalls per env-second and action step per tick
  local LABEL=$1 PT=$2
  cd $M/microduck_rl
  for LOAD in none full; do for GAIN in 1.0 2.0; do for SD in 1 2; do
    zsh $LK run timeout 590 .venv/bin/python cmu/finetune/flight/student_audit.py --out $FL/train/out/rl_zcmd \
      --load $LOAD --gain $GAIN --cmd 0.0 --teacher-onnx $A/ts3t_t3h_750.onnx --student-pt $PT \
      --stand-onnx $MODELS/stand61.onnx --walk-onnx $MODELS/walk61.onnx --gain-flag-col 59 \
      --manifest $FL/train/manifests/flightpack-none.json --audit $A/existing-model-mass-audit.json \
      --policies student --tag _${LABEL}_s$SD --seed $SD --num-envs 96 --steps 500 \
      > $FL/train/logs/ts3_rl_zcmd_${LABEL}_${LOAD}_g${GAIN}_s$SD.log 2>&1
    hb "zcmd $LABEL $LOAD gain $GAIN seed $SD: $(grep -E '^\[saudit\] (none|full)' $FL/train/logs/ts3_rl_zcmd_${LABEL}_${LOAD}_g${GAIN}_s$SD.log | sed -E 's/.*student: //' | cut -c1-200)"
  done; done; done
}
last() { ls $OUT/$1/model_*.pt 2>/dev/null | grep -v best | sed -E 's/.*model_([0-9]+)\.pt/\1/' | sort -n | tail -1; }

stage base_stage0 --run-name base --seed 1 --resume-pt $FL/train/ckpt/s3AB_140/model_140.pt --max-iters 145 \
  --save-interval 5 --lr 0 --lr-final 0 --bc-w 0.5 --rl-critic-warmup 100 --max-hours 0.15
B=$(last base)
[ -z "$B" ] && { hb "FAILED stage 0: no save"; exit 1; }
zcmd start $FL/train/ckpt/s3AB_140/model_140.pt

for TAG in f1 a1 f2 a2; do
  SEED=${TAG[2]}
  PT=$OUT/base/model_$B.pt
  for S in 1 2 3; do
    if [ ${TAG[1]} = a ]; then
      case $S in 1) BW=(--bc-w 0.5 --bc-w-final 0.37);; 2) BW=(--bc-w 0.37 --bc-w-final 0.23);; 3) BW=(--bc-w 0.23 --bc-w-final 0.1);; esac
    else
      BW=(--bc-w 0.5)
    fi
    IT=$(echo $PT | sed -E 's/.*model_([0-9]+)\.pt/\1/')
    stage ${TAG}_stage$S --run-name $TAG --seed $SEED --resume-pt $PT --max-iters $((IT + 8)) --save-interval 2 \
      --lr 0.0001 --lr-final 0.0001 $BW --rl-critic-warmup 0 --max-hours 0.14
    L=$(last $TAG)
    [ -z "$L" ] && { hb "FAILED $TAG stage $S: no save"; exit 1; }
    PT=$OUT/$TAG/model_$L.pt
  done
  D=smk_rl${TAG}_$L
  mkdir -p $FL/train/ckpt/$D
  cp $OUT/$TAG/model_$L.onnx $FL/train/ckpt/$D/walk61.onnx
  cp $OUT/$TAG/model_$L.onnx $FL/train/ckpt/$D/stand61.onnx
  cp $OUT/$TAG/model_$L.pt $FL/train/ckpt/$D/model_$L.pt
  zcmd $TAG $FL/train/ckpt/$D/model_$L.pt   # annealed chains: the last save is the lowest imitation weight reached
  cd $FL
  {
    for K in 200 400; do zsh $LK run $PY train/ts3_stop_where.py $D count=10 kp=$K 2>&1 | tail -2 | cut -c1-400; done
    zsh $LK run $PY train/ts3_still_where.py $D 0,1,2,3,4,5,6,7,8,9 kp=400 2>&1 | grep -E "seed" | cut -c1-200
  } > $FL/train/logs/ts3_rl_${TAG}_cells.out 2>&1
  hb "$TAG cells ($D): $(grep 'falls of' $FL/train/logs/ts3_rl_${TAG}_cells.out | sed -E 's/.*walk gain ([0-9]+): ([0-9]+ falls of [0-9]+).*/g\1 \2/' | tr '\n' ';') stand jumps $(grep -oE 'gate jumps [0-9]+' $FL/train/logs/ts3_rl_${TAG}_cells.out | awk '{printf "%s ", $3}')"
done
hb "DONE"
