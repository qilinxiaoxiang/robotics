#!/bin/zsh
# Universal-plan smoke test on the Mac mini (never the MacBook): mirror microduck_rl + the flight manifests, build its
# uv venv there once, then run flight_worker.py --delta universal for a few iterations on CPU and keep the log.
#   zsh train/mini_train_smoke.sh push     mirror code + manifests (no .venv, no .git)
#   zsh train/mini_train_smoke.sh setup    uv sync in the mirror (first time only)
#   zsh train/mini_train_smoke.sh run [iters] [envs]   smoke run; log -> train/logs/universal_smoke.log
set -e
LOCAL=/Users/xiangzheng/code/robotics/microduck-sim
REMOTE=code/flight-train-mirror/robotics/microduck-sim
RL=microduck_rl
FL=extensions/flight-20261110
case "$1" in
  push)
    ssh mac-mini "mkdir -p $REMOTE/$RL $REMOTE/$FL/train/manifests $REMOTE/smoke-assets"
    rsync -a --exclude='.git' --exclude='.venv' --exclude='cmu/hardware' --exclude='cmu/simulator' \
      --exclude='cmu/real-logs' --exclude='cmu/planning' --exclude='cmu/model/scans' --exclude='__pycache__' \
      $LOCAL/$RL/ mac-mini:$REMOTE/$RL/
    rsync -a $LOCAL/$FL/train/manifests/ mac-mini:$REMOTE/$FL/train/manifests/
    ;;
  setup)
    ssh mac-mini "cd $REMOTE/$RL && /opt/homebrew/bin/uv sync 2>&1 | tail -5"
    ;;
  run)
    # $4 = smoke tag, $5.. = extra universal_smoke.py flags (--delta universal2, --task ..., --init <mirror path>)
    IT=${2:-3}
    NE=${3:-64}
    TG=${4:-universal}
    XA="${@:5}"
    zsh $LOCAL/$FL/train/mini.sh run true
    mkdir -p $LOCAL/$FL/train/logs
    ssh mac-mini "cd $REMOTE/$RL && FLIGHT_MANIFESTS=\$HOME/$REMOTE/$FL/train/manifests timeout 590 .venv/bin/python \
      cmu/finetune/flight/universal_smoke.py --envs $NE --iters $IT $XA --out /tmp/${TG}_smoke.json 2>&1" \
      > $LOCAL/$FL/train/logs/${TG}_smoke.log || true
    scp -q mac-mini:/tmp/${TG}_smoke.json $LOCAL/$FL/train/out/${TG}_smoke.json || true
    grep -E "\[payload\]|\[smoke\]|\[style\]|\[pack\]|\[asbuilt\] total|Error|Traceback" $LOCAL/$FL/train/logs/${TG}_smoke.log | cut -c1-400 | head -60
    ;;
  audit)
    zsh $LOCAL/$FL/train/mini.sh run true  # waits while another agent's simulation runs on the mini
    # universal-env degenerate audit on CPU (UNIVERSAL-PLAN.md section 4): assets laid out as the training image's
    # /root/assets (walk61/stand61 = today's runtime models, fq2 = the with-pack choice, manifests, mass audit)
    NE=${2:-128}
    ST=${3:-500}
    A=\$HOME/$REMOTE/smoke-assets
    ssh mac-mini "mkdir -p $REMOTE/smoke-assets/manifests && cd $REMOTE && \
      cp $RL/cmu/whole/runtime-overlay/models/walk61.onnx $RL/cmu/whole/runtime-overlay/models/stand61.onnx smoke-assets/ && \
      cp $RL/cmu/whole/electrical/existing-model-mass-audit.json smoke-assets/ && cp $FL/train/manifests/flightpack-*.json smoke-assets/manifests/"
    rsync -a $LOCAL/$FL/train/ckpt/fq2_1999/walk61.onnx mac-mini:$REMOTE/smoke-assets/fq2_1999.onnx
    ssh mac-mini "cd $REMOTE/$RL && timeout 5400 .venv/bin/python cmu/finetune/flight/flight_audit.py --jobs universal \
      --device cpu --num-envs $NE --steps $ST --assets $A --policy fq2=$A/fq2_1999.onnx --walker fq2 --out /tmp/universal_audit 2>&1" \
      > $LOCAL/$FL/train/logs/universal_audit.log || true
    scp -q mac-mini:/tmp/universal_audit/audit.json $LOCAL/$FL/train/out/universal_audit.json || true
    grep -E "\[audit\]|Traceback|Error" $LOCAL/$FL/train/logs/universal_audit.log | head -30
    ;;
  audit2)
    # reward-redesign audit, one load per call (full | nobatt | none), under 10 minutes each: stand, shuffle and
    # lean-and-hold against the intended walk, with the candidate terms at weight 1e-6 (--diag) so designs are priced
    # offline by train/reward_design.py; $4 = optional reward_mods JSON for a confirmation run of the chosen design
    LD=$2
    NE=${3:-128}
    ST=${4:-400}
    RM=${5:-}
    TAG=${6:-diag}
    zsh $LOCAL/$FL/train/mini.sh run true
    A=\$HOME/$REMOTE/smoke-assets
    rsync -a $LOCAL/$FL/train/ckpt/fq2_1999/walk61.onnx mac-mini:$REMOTE/smoke-assets/fq2_1999.onnx
    mkdir -p $LOCAL/$FL/train/logs
    print -r -- "$RM" > $LOCAL/$FL/train/logs/rm_$TAG.json
    scp -q $LOCAL/$FL/train/logs/rm_$TAG.json mac-mini:/tmp/flight_rm_$TAG.json
    ssh mac-mini "cd $REMOTE/$RL && timeout 590 .venv/bin/python cmu/finetune/flight/flight_audit.py --jobs universal2 \
      --loads $LD --diag --reward-mods \"\$(cat /tmp/flight_rm_$TAG.json)\" --device cpu --num-envs $NE --steps $ST \
      --assets $A --policy fq2=$A/fq2_1999.onnx --walker fq2 --out /tmp/audit2_${TAG}_$LD 2>&1" \
      > $LOCAL/$FL/train/logs/audit2_${TAG}_$LD.log || true
    scp -q mac-mini:/tmp/audit2_${TAG}_$LD/audit.json $LOCAL/$FL/train/out/audit2_${TAG}_$LD.json || true
    grep -E "\[audit\]|\[style\]|Traceback|Error" $LOCAL/$FL/train/logs/audit2_${TAG}_$LD.log | head -30
    ;;
  bendaudit)
    # bend incentive audit (BEND-PLAN.md section 5), one load per call: $2 load, $3 envs, $4 steps, $5 intended
    # correction (reward/s, the static extra torque cost x1.5), $6 tag, $7 optional reward_mods JSON
    LD=$2
    NE=${3:-128}
    ST=${4:-400}
    CO=${5:-0}
    TAG=${6:-bend}
    RM=${7:-}
    zsh $LOCAL/$FL/train/mini.sh run true
    A=\$HOME/$REMOTE/smoke-assets
    rsync -a $LOCAL/$FL/train/ckpt/fq2_1999/walk61.onnx mac-mini:$REMOTE/smoke-assets/fq2_1999.onnx
    rsync -a $LOCAL/$FL/train/ckpt/bend_spec/groundpick61.onnx mac-mini:$REMOTE/smoke-assets/groundpick61.onnx
    mkdir -p $LOCAL/$FL/train/logs
    print -r -- "$RM" > $LOCAL/$FL/train/logs/rm_$TAG.json
    scp -q $LOCAL/$FL/train/logs/rm_$TAG.json mac-mini:/tmp/flight_rm_$TAG.json
    ssh mac-mini "cd $REMOTE/$RL && timeout 590 .venv/bin/python cmu/finetune/flight/bend_audit.py --load $LD --diag \
      --reward-mods \"\$(cat /tmp/flight_rm_$TAG.json)\" --device cpu --num-envs $NE --steps $ST --assets $A \
      --policy fq2=$A/fq2_1999.onnx --policy groundpick61=$A/groundpick61.onnx --intended-correction $CO ${8:+--manifest $8} \
      --delta ${9:-bend} --out /tmp/bendaudit_${TAG}_$LD 2>&1" > $LOCAL/$FL/train/logs/bendaudit_${TAG}_$LD.log || true
    scp -q mac-mini:/tmp/bendaudit_${TAG}_$LD/audit.json $LOCAL/$FL/train/out/bendaudit_${TAG}_$LD.json || true
    grep -E "\[bend-audit\]|\[payload\]|Traceback|Error" $LOCAL/$FL/train/logs/bendaudit_${TAG}_$LD.log | cut -c1-700 | head -30
    ;;
  bendaccept)
    # bend acceptance in the training env (BEND-PLAN.md section 6, bend_accept.py), one load per call:
    # $2 load, $3 bend policy ONNX (local path), $4 stand-slot policy ONNX (local path), $5 tag, $6 envs
    LD=$2
    TAG=${5:-bend}
    NE=${6:-20}
    zsh $LOCAL/$FL/train/mini.sh run true
    A=\$HOME/$REMOTE/smoke-assets
    rsync -a $3 mac-mini:$REMOTE/smoke-assets/accept_${TAG}_bend.onnx
    rsync -a $4 mac-mini:$REMOTE/smoke-assets/accept_${TAG}_stander.onnx
    mkdir -p $LOCAL/$FL/train/logs $LOCAL/$FL/train/eval
    ssh mac-mini "cd $REMOTE/$RL && timeout 590 .venv/bin/python cmu/finetune/flight/bend_accept.py --load $LD \
      --device cpu --num-envs $NE --assets $A --policy bend=$A/accept_${TAG}_bend.onnx \
      --policy stander=$A/accept_${TAG}_stander.onnx --out /tmp/bendaccept_${TAG}_$LD 2>&1" \
      > $LOCAL/$FL/train/logs/bendaccept_${TAG}_$LD.log || true
    scp -q mac-mini:/tmp/bendaccept_${TAG}_$LD/accept.json $LOCAL/$FL/train/eval/bendaccept_${TAG}_$LD.json || true
    grep -E "\[bend-accept\]|Traceback|Error" $LOCAL/$FL/train/logs/bendaccept_${TAG}_$LD.log | cut -c1-900 | head -20
    ;;
esac
