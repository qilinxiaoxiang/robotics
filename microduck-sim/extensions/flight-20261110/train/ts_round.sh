#!/bin/zsh
# Teacher-student round (TEACHER-STUDENT-PLAN.md): Mac mini jobs, one at a time, each under 10 minutes, CPU only.
#   zsh train/ts_round.sh push                      copy cmu/finetune/flight + manifests to the mirror
#   zsh train/ts_round.sh start <one-frame.onnx>    the start policy for the smokes and audits (smoke-assets/ts_start.onnx)
#   zsh train/ts_round.sh teacher [iters] [envs]    teacher_smoke.py; keeps ckpt/ts_teacher_m0/teacher.onnx
#   zsh train/ts_round.sh distill <lstm|mamba> [iters] [envs] [bptt] [teacher.onnx]   distill_worker.py on CPU
#   zsh train/ts_round.sh audit <case> <load> <tag> [rm.json] [job]   one incentive-audit case in the teacher env
#   zsh train/ts_round.sh teval <name> <policy.onnx> <load>      the intended walk alone in the teacher env (gate)
#   zsh train/ts_round.sh adapt <name> <student.pt> <teacher.onnx> <load>   adapt_eval.py
# Round 2 (delta universal4 / universal4t): teacher takes a 4th argument (delta), distill a 7th; teval / tdelay read
# TSJOB (audit job, default universal3t) and teval TSCASE (default none); adapt reads TSDELTA (default universal3).
set -e
LOCAL=/Users/xiangzheng/code/robotics/microduck-sim
REMOTE=code/flight-train-mirror/robotics/microduck-sim
RL=microduck_rl
FL=extensions/flight-20261110
T=$LOCAL/$FL/train
A="\$HOME/$REMOTE/smoke-assets"
ENVV="FLIGHT_MANIFESTS=\$HOME/$REMOTE/$FL/train/manifests"
source $T/ssh_guard.sh  # ssh / scp / rsync with keepalives, a local wall-clock limit and one retry

wait_idle() {
  # one simulation at a time on the Mac mini, this mirror's own jobs included (mini_busy.sh skips them)
  for i in $(seq 1 360); do
    if ! ssh mac-mini "pgrep -f 'style_eval.py|flight_eval.py|flight_audit.py|_smoke.py|distill_worker.py|adapt_eval.py|brain_sim_check|bend_accept.py' > /dev/null"; then
      zsh $T/mini.sh run true && return 0
    fi
    sleep 10
  done
  echo "mini still busy after 60 min"; exit 3
}

mkdir -p $T/logs $T/out
case "$1" in
  push)
    ssh mac-mini "mkdir -p $REMOTE/$RL/cmu/finetune/flight $REMOTE/$FL/train/manifests $REMOTE/smoke-assets/manifests"
    rsync -a --exclude='__pycache__' --exclude='.last_call_*' $LOCAL/$RL/cmu/finetune/flight/ mac-mini:$REMOTE/$RL/cmu/finetune/flight/
    rsync -a $T/manifests/ mac-mini:$REMOTE/$FL/train/manifests/
    ssh mac-mini "cd $REMOTE && cp $RL/cmu/whole/electrical/existing-model-mass-audit.json smoke-assets/ && cp $FL/train/manifests/flightpack-*.json smoke-assets/manifests/"
    ;;
  start)
    rsync -a "$2" mac-mini:$REMOTE/smoke-assets/ts_start.onnx
    ssh mac-mini "shasum -a 256 $REMOTE/smoke-assets/ts_start.onnx | cut -c1-16"
    ;;
  teacher)
    IT=${2:-3}; NE=${3:-64}; DL=${4:-universal3t}
    wait_idle
    ssh mac-mini "cd $REMOTE/$RL && $ENVV timeout 590 .venv/bin/python cmu/finetune/flight/teacher_smoke.py \
      --init $A/ts_start.onnx --envs $NE --iters $IT --delta $DL --outdir /tmp/teacher_smoke 2>&1" > $T/logs/teacher_smoke.log || true
    scp -q mac-mini:/tmp/teacher_smoke/teacher_smoke.json $T/out/teacher_smoke.json || true
    mkdir -p $T/ckpt/ts_teacher_m0
    scp -q mac-mini:/tmp/teacher_smoke/teacher_m0.onnx $T/ckpt/ts_teacher_m0/teacher.onnx || true
    ssh mac-mini "cp /tmp/teacher_smoke/teacher_m0.onnx $REMOTE/smoke-assets/ts_teacher_m0.onnx" || true
    grep -E "\[smoke\]|\[teacher\]|Error|Traceback" $T/logs/teacher_smoke.log | cut -c1-500 | head -40
    ;;
  distill)
    CORE=$2; IT=${3:-3}; NE=${4:-64}; BP=${5:-100}; DL=${7:-universal3}
    TE="$A/ts_teacher_m0.onnx"
    if [ -n "$6" ]; then rsync -a "$6" mac-mini:$REMOTE/smoke-assets/ts_teacher_x.onnx; TE="$A/ts_teacher_x.onnx"; fi
    wait_idle
    ssh mac-mini "mkdir -p /tmp/ts_distill && cd $REMOTE/$RL && $ENVV timeout 590 .venv/bin/python cmu/finetune/flight/flight_worker.py --distill \
      --run-name smoke_$CORE --root /tmp/ts_distill --teacher-onnx $TE --core $CORE --device cpu --num-envs $NE \
      --max-iters $IT --bptt-steps $BP --delta $DL --warmup-iters 1 --beta-iters 1 --save-interval 1 --mb-envs 32 --max-hours 0.15 \
      --manifest \$HOME/$REMOTE/$FL/train/manifests/flightpack-none.json --audit $A/existing-model-mass-audit.json 2>&1" \
      > $T/logs/distill_smoke_$CORE.log || true
    mkdir -p $T/ckpt/ts_smoke_$CORE
    scp -q mac-mini:/tmp/ts_distill/smoke_$CORE/run_record.json $T/out/distill_smoke_$CORE.json || true
    scp -q mac-mini:/tmp/ts_distill/smoke_$CORE/smoke_$CORE.onnx $T/ckpt/ts_smoke_$CORE/walk61.onnx || true
    cp $T/ckpt/ts_smoke_$CORE/walk61.onnx $T/ckpt/ts_smoke_$CORE/stand61.onnx || true
    grep -E "\[distill\]|\[cap\]|\[done\]|\[teacher\]|Error|Traceback" $T/logs/distill_smoke_$CORE.log | cut -c1-700 | head -30
    ;;
  audit)
    CS=$2; LD=$3; TAG=$4; RM=${5:-$T/rm_universal3.json}; JOB=${6:-universal3t}
    scp -q $RM mac-mini:/tmp/ts_rm_$TAG.json
    wait_idle
    ssh mac-mini "cd $REMOTE/$RL && timeout 590 .venv/bin/python cmu/finetune/flight/flight_audit.py --jobs $JOB \
      --cases $CS --loads $LD --reward-mods \"\$(cat /tmp/ts_rm_$TAG.json)\" --device cpu --num-envs 128 --steps ${TSSTEPS:-400} \
      --assets $A --policy start=$A/ts_start.onnx --walker start --out /tmp/ts_audit_${TAG}_${CS}_$LD 2>&1" \
      > $T/logs/audit_${TAG}_${CS}_$LD.log || true
    scp -q mac-mini:/tmp/ts_audit_${TAG}_${CS}_$LD/audit.json $T/out/audit_${TAG}_${CS}_$LD.json || true
    grep -E "\[audit\].*verdict|Traceback|Error" $T/logs/audit_${TAG}_${CS}_$LD.log | cut -c1-400 | head -5
    ;;
  teval)
    NM=$2; LD=$4
    rsync -a "$3" mac-mini:$REMOTE/smoke-assets/ts_eval_$NM.onnx
    wait_idle
    ssh mac-mini "cd $REMOTE/$RL && timeout 590 .venv/bin/python cmu/finetune/flight/flight_audit.py --jobs ${TSJOB:-universal3t} \
      --cases ${TSCASE:-none} --loads $LD --reward-mods \"\$(cat \$HOME/$REMOTE/$FL/train/rm_universal3.json)\" --device cpu --num-envs 128 --steps 500 \
      --assets $A --policy p=$A/ts_eval_$NM.onnx --walker p --out /tmp/ts_teval_${NM}_$LD 2>&1" \
      > $T/logs/teval_${NM}_$LD.log || true
    scp -q mac-mini:/tmp/ts_teval_${NM}_$LD/audit.json $T/out/teval_${NM}_$LD.json || true
    grep -E "\[audit\] universal|Traceback|Error" $T/logs/teval_${NM}_$LD.log | cut -c1-300 | head -5
    ;;
  tdelay)
    # zsh train/ts_round.sh tdelay <name> <policy.onnx> <load> <tag> <delay.json>
    # teval with flight_audit.py --delay-mods: the training env with its delays switched (-> out/tsep_<name>_<load>_<tag>.json)
    # optional 7th argument: the audit case to add beside the intended walk (walk025 = vx 0.25 held; default none)
    NM=$2; LD=$4; TG=$5; CS=${7:-none}
    rsync -a "$3" mac-mini:$REMOTE/smoke-assets/ts_eval_$NM.onnx
    rsync -a "$6" mac-mini:$REMOTE/smoke-assets/ts_delay_$TG.json
    wait_idle
    ssh mac-mini "cd $REMOTE/$RL && timeout 590 .venv/bin/python cmu/finetune/flight/flight_audit.py --jobs ${TSJOB:-universal3t} \
      --cases $CS --loads $LD --reward-mods \"\$(cat \$HOME/$REMOTE/$FL/train/rm_universal3.json)\" --device cpu --num-envs 128 --steps 500 \
      --delay-mods \"\$(cat \$HOME/$REMOTE/smoke-assets/ts_delay_$TG.json)\" \
      --assets $A --policy p=$A/ts_eval_$NM.onnx --walker p --out /tmp/ts_tsep_${NM}_${LD}_$TG 2>&1" \
      > $T/logs/tsep_${NM}_${LD}_$TG.log || true
    scp -q mac-mini:/tmp/ts_tsep_${NM}_${LD}_$TG/audit.json $T/out/tsep_${NM}_${LD}_$TG.json || true
    grep -E "\[audit\] universal|\[delay\]|Traceback|Error" $T/logs/tsep_${NM}_${LD}_$TG.log | cut -c1-300 | head -6
    ;;
  adapt)
    NM=$2; LD=$5
    rsync -a "$3" mac-mini:$REMOTE/smoke-assets/ts_adapt_$NM.pt
    rsync -a "$4" mac-mini:$REMOTE/smoke-assets/ts_adapt_teacher.onnx
    wait_idle
    ssh mac-mini "cd $REMOTE/$RL && $ENVV timeout 590 .venv/bin/python cmu/finetune/flight/adapt_eval.py \
      --student-pt $A/ts_adapt_$NM.pt --teacher-onnx $A/ts_adapt_teacher.onnx --load $LD --envs 64 --delta ${TSDELTA:-universal3} \
      --out /tmp/ts_adapt_${NM}_$LD.json 2>&1" > $T/logs/adapt_${NM}_$LD.log || true
    scp -q mac-mini:/tmp/ts_adapt_${NM}_$LD.json $T/out/adapt_${NM}_$LD.json || true
    grep -E "\[adapt\]|Traceback|Error" $T/logs/adapt_${NM}_$LD.log | cut -c1-400 | head -8
    ;;
esac
