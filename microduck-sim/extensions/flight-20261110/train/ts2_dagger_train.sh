#!/bin/zsh
# Round 2 DAgger: run ts2_dagger_train.py on the Mac mini CPU under the mirror's lock and bring the checkpoints back.
#   zsh train/ts2_dagger_train.sh <tag> <init pt, relative to train/> <epochs> <save every> <data npz, relative to train/> [...]
#   e.g. zsh train/ts2_dagger_train.sh s2r1 ckpt/s2g_200/model_200.pt 30 10 out/dagger/r1.npz
set -e
LOCAL=/Users/xiangzheng/code/robotics/microduck-sim
REMOTE=code/flight-train-mirror/robotics/microduck-sim
FL=extensions/flight-20261110
T=$LOCAL/$FL/train
TAG=$1; INIT=$2; EPOCHS=$3; EVERY=$4
shift 4
DATA=""
for f in "$@"; do DATA="$DATA \$HOME/$REMOTE/$FL/train/$f"; done
SSH_GUARD_LIMIT=3400  # the fine-tune runs up to 55 min (2026-11-19: the default 640 s cut the call at epoch 14 and retried)
source $T/ssh_guard.sh
zsh $T/mini.sh push
zsh $T/ts_round.sh push
ssh mac-mini "cd $REMOTE/microduck_rl && zsh \$HOME/$REMOTE/$FL/train/mini_lock.sh run timeout 3300 .venv/bin/python \$HOME/$REMOTE/$FL/train/ts2_dagger_train.py \
  --init \$HOME/$REMOTE/$FL/train/$INIT --template \$HOME/$REMOTE/$FL/train/ckpt/s2g_200/walk61.onnx --tag $TAG --epochs $EPOCHS --save-every $EVERY --mb ${MB:-64} --lr ${LR:-5e-5} ${=EXTRA} \
  --data $DATA 2>&1" > $T/logs/dagger_$TAG.log || true
grep -E "\[dagger\]|\[mini_lock\]|Error|Traceback|assert" $T/logs/dagger_$TAG.log | cut -c1-400 | tail -8
rsync -a --include="${TAG}_*/" --include="${TAG}_*/*" --exclude='*' mac-mini:$REMOTE/$FL/train/ckpt/ $T/ckpt/
rsync -a mac-mini:$REMOTE/$FL/train/out/dagger/${TAG}_log.json $T/out/dagger/
