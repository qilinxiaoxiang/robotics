#!/bin/zsh
# Push the approved bend pair (BEND-PLAN.md, delta bend3) to Kaggle as soon as a GPU session is free (Kaggle allows 2 at
# once; the scratch pair and the universal pair hold both until the scratch pair ends). Retries every 2 min while the
# push answers "Maximum batch GPU session count", gives up after 3 h. Run from anywhere:
#   zsh train/push_bend_when_free.sh
RL=/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl
cd $RL || exit 1
F="--task Mjlab-GroundPick-Flat-MicroDuck --delta bend3 --onnx /root/assets/init/groundpick61.onnx \
--manifest /root/assets/manifests/flightpack-none.json --max-iters 2500 --max-hours 3.0 --save-interval 100 \
--warmup-iters 100 --max-lr 0.0003 --guard-fraction 0.0"
for i in $(seq 1 90); do
  if python3 cmu/finetune/flight/kaggle_flight.py status fk-scratch-s1 2>&1 | grep -q RUNNING; then
    sleep 120  # no push (and no dataset re-upload) while the scratch pair still holds its session
    continue
  fi
  OUT=$(python3 cmu/finetune/flight/kaggle_flight.py push run --run-name fk-bend-a --pair-run-name fk-bend-b -- \
        ${=F} --seed 1 -- ${=F} --seed 2 2>&1)
  if print -r -- "$OUT" | grep -q "Maximum batch GPU session"; then
    print "$(date +%T) GPU sessions full, retry in 2 min"
    sleep 120
    continue
  fi
  print -r -- "$OUT" | grep -vE "outdated|%\|" | tail -6
  print "PUSHED $(date +%T)"
  exit 0
done
print "GAVE UP $(date +%T)"
exit 1
