#!/bin/zsh
# smoke-fall controlled check on the Mac mini: arms given as "name|flags" in $@, each trained then evaluated
# (nominal walk, 4 episodes, --stand-s 0). Results: train/eval/fallcheck_<name>.json, train/out/fallcheck_<name>.json
LOCAL=/Users/xiangzheng/code/robotics/microduck-sim
M=code/flight-train-mirror/robotics/microduck-sim
FL=extensions/flight-20261110
T=$LOCAL/$FL/train
zsh $T/mini.sh run true
zsh $T/mini_train_smoke.sh push
ssh mac-mini "mkdir -p $M/smoke-assets"
rsync -a $T/ckpt/uni_a/walk61.onnx mac-mini:$M/smoke-assets/uni_a.onnx
for ARM in "$@"; do
  NAME=${ARM%%|*}
  FLAGS=${ARM#*|}
  ssh mac-mini "cd $M/microduck_rl && FLIGHT_MANIFESTS=\$HOME/$M/$FL/train/manifests timeout 590 .venv/bin/python \
    cmu/finetune/flight/smoke_fall_check.py --init \$HOME/$M/smoke-assets/uni_a.onnx $FLAGS --outdir /tmp/fallcheck_$NAME 2>&1 | grep -E 'fallcheck|Error|Traceback' | cut -c1-900"
  ssh mac-mini "mkdir -p $M/$FL/train/ckpt/fc_$NAME && cp /tmp/fallcheck_$NAME/policy.onnx $M/$FL/train/ckpt/fc_$NAME/walk61.onnx && \
    cp /tmp/fallcheck_$NAME/policy.onnx $M/$FL/train/ckpt/fc_$NAME/stand61.onnx"
  mkdir -p $T/ckpt/fc_$NAME
  scp -q mac-mini:/tmp/fallcheck_$NAME/policy.onnx $T/ckpt/fc_$NAME/walk61.onnx
  cp $T/ckpt/fc_$NAME/walk61.onnx $T/ckpt/fc_$NAME/stand61.onnx
  scp -q mac-mini:/tmp/fallcheck_$NAME/arm.json $T/out/fallcheck_$NAME.json
  zsh $T/mini.sh run "timeout 300 \$PY train/flight_eval.py --models train/ckpt/fc_$NAME --manifest train/manifests/flightpack-nominal.json --case walk --episodes 4 --workers 4 --extra='--stand-s 0' --out train/eval/fallcheck_$NAME.json" | grep -v '^busy' | cut -c1-260
done
zsh $T/mini.sh pull
