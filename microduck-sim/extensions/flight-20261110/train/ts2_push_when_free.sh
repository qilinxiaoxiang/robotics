#!/bin/zsh
# Round 2: push the students of teacher A at iteration 999 (Mamba on GPU 0, LSTM on GPU 1) as soon as Kaggle has a
# free GPU session (it allows two; a refused push says "Maximum batch GPU session count"). Tries every 2 minutes for
# up to 2.5 h.
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
cd /Users/xiangzheng/code/robotics/microduck-sim/microduck_rl
D="--distill --delta universal4 --teacher-onnx /root/assets/init/ts2a999_teacher.onnx --manifest /root/assets/manifests/flightpack-none.json --max-iters 140 --max-hours 1.7 --save-interval 20 --warmup-iters 2 --beta-iters 30 --bptt-steps 100 --epochs 2 --mb-envs 256 --stop-after 100 --seed 1"
for i in $(seq 1 75); do
  OUT=$(python3 cmu/finetune/flight/kaggle_flight.py push run --run-name ts2-mamba-c --pair-run-name ts2-lstm-c -- ${=D} --core mamba -- ${=D} --core lstm 2>&1)
  if echo "$OUT" | grep -q "successfully pushed"; then
    echo "$(date +%T) pushed"; echo "$OUT" | tail -4 | cut -c1-200; exit 0
  fi
  echo "$(date +%T) $(echo "$OUT" | grep -i "error\|gate\|refus" | head -1 | cut -c1-160)"
  sleep 120
done
echo "gave up $(date +%T)"; exit 1
