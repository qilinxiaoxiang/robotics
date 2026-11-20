#!/bin/zsh
# Round 3, 2026-11-19 23:10: one Kaggle kernel, two arms, then its follow-up (ts3_after_pair.py).
#   GPU 0  ts3-teach-k       teacher continuation from t3h_750 (walk61 start, gain input) under universal5tgs: both
#                            action-smoothness weights doubled, learning rate clamped at 5e-5, start noise 0.15 (the
#                            noise t3h had at 750), 100 critic warm-up iterations with the actor frozen, then 900
#                            iterations with a save every 25 -> ckpt/t3k_<iter>
#   GPU 1  ts3s-t3h-750-m    Mamba student distilled from t3h_750 as it is (env universal5) -> ckpt/s3h_<iter>
#   python3 train/detach.py train/logs/ts3_push_k.out zsh train/ts3_push_k.sh
# Heartbeat: train/logs/ts3_push_k_heartbeat.txt (last line DONE or FAILED); the kernel's own heartbeat is
# train/logs/ts3_pair_k_heartbeat.txt. Polling only; tries every 2 minutes for 1 hour.
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
RL=/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl
H=$T/logs/ts3_push_k_heartbeat.txt
hb() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*" >> $H }
echo "$(date +%Y-%m-%dT%H:%M:%S) START pid $$" > $H
cd $RL
A="--onnx /root/assets/init/ts3t_t3h_750.onnx --delta universal5tgs --manifest /root/assets/manifests/flightpack-none.json --max-iters 1000 --max-hours 1.9 --save-interval 25 --warmup-iters 100 --init-std 0.15 --max-lr 0.00005 --guard-fraction 0.0 --track-guard 2.0 --seed 1"
B="--distill --delta universal5 --teacher-onnx /root/assets/init/ts3t_t3h_750.onnx --manifest /root/assets/manifests/flightpack-none.json --max-iters 160 --max-hours 2.2 --save-interval 20 --warmup-iters 2 --beta-iters 30 --bptt-steps 100 --epochs 2 --mb-envs 256 --stop-after 100 --seed 1 --drop-max 0.08 --core mamba"
hb "quota before: $(python3 cmu/finetune/flight/kaggle_flight.py quota 2>&1 | grep GPU | tr -s ' ')"
for i in $(seq 1 30); do
  OUT=$(python3 cmu/finetune/flight/kaggle_flight.py push run --run-name ts3-teach-k --pair-run-name ts3s-t3h-750-m -- ${=A} -- ${=B} 2>&1)
  echo "$OUT" > $T/logs/launch_ts3-teach-k.log
  if echo "$OUT" | grep -q "successfully pushed"; then
    hb "pushed microduck-ts3-teach-k (teacher ts3-teach-k: universal5tgs from t3h_750, 1000 iterations, save every 25; student ts3s-t3h-750-m: Mamba from t3h_750, 160 iterations)"
    PID=$(python3 $T/detach.py $T/logs/ts3_pair_k.out python3 $T/ts3_after_pair.py ts3-teach-k ts3-teach-k t3k ts3s-t3h-750-m s3h ts3_pair_k teacher_min=125)
    hb "follow-up pid $PID, heartbeat logs/ts3_pair_k_heartbeat.txt"
    hb "DONE"
    exit 0
  fi
  [ $((i % 5)) -eq 1 ] && hb "push refused (try $i): $(echo "$OUT" | grep -i "error\|gate\|refus\|maximum\|exit" | head -1 | cut -c1-200)"
  sleep 120
done
hb "FAILED push refused for 1 h"
exit 1
