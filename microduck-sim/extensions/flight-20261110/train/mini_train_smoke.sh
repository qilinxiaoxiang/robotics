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
    IT=${2:-3}
    NE=${3:-64}
    mkdir -p $LOCAL/$FL/train/logs
    ssh mac-mini "cd $REMOTE/$RL && FLIGHT_MANIFESTS=\$HOME/$REMOTE/$FL/train/manifests timeout 1500 .venv/bin/python \
      cmu/finetune/flight/universal_smoke.py --envs $NE --iters $IT --out /tmp/universal_smoke.json 2>&1" \
      > $LOCAL/$FL/train/logs/universal_smoke.log || true
    scp -q mac-mini:/tmp/universal_smoke.json $LOCAL/$FL/train/out/universal_smoke.json || true
    grep -E "\[payload\]|\[smoke\]|\[asbuilt\] total|Error|Traceback" $LOCAL/$FL/train/logs/universal_smoke.log | head -60
    ;;
  audit)
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
esac
