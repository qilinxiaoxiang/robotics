#!/bin/zsh
# Round 3: push the gain-reading teacher pair (delta universal5tg: universal5t plus the position-gain scale as the
# teacher's eighth privileged input; train/out/gain_split.json) into the first free Kaggle GPU session, then start
# its follow-up (ts3_after_kaggle.sh). GPU 0 ts3-teach-g from ts_start, GPU 1 ts3-teach-h from walk61 with
# --track-grace 700 (walk61 cannot walk in this env at the start). Polling only; tries every 2 minutes for 2 hours.
#   python3 train/detach.py train/logs/ts3_push_tg.out zsh train/ts3_push_tg.sh
# Heartbeat: train/logs/ts3_push_tg_heartbeat.txt (last line DONE or FAILED); the pair's own heartbeat is
# train/logs/ts3_teach_gh_heartbeat.txt, folders ckpt/t3g_*, ckpt/t3h_*.
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
RL=/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl
H=$T/logs/ts3_push_tg_heartbeat.txt
hb() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*" >> $H }
echo "$(date +%Y-%m-%dT%H:%M:%S) START pid $$" > $H
cd $RL
F="--delta universal5tg --manifest /root/assets/manifests/flightpack-none.json --max-iters 1000 --max-hours 1.6 --save-interval 125 --warmup-iters 100 --max-lr 0.0001 --guard-fraction 0.0 --track-guard 2.0 --seed 1"
for i in $(seq 1 60); do
  OUT=$(python3 cmu/finetune/flight/kaggle_flight.py push run --run-name ts3-teach-g --pair-run-name ts3-teach-h -- --onnx /root/assets/init/ts_start.onnx ${=F} -- --onnx /root/assets/init/walk61.onnx ${=F} --track-grace 700 2>&1)
  if echo "$OUT" | grep -q "successfully pushed"; then
    hb "pushed microduck-ts3-teach-g (ts3-teach-g from ts_start, ts3-teach-h from walk61 with --track-grace 700; universal5tg, 1000 iterations, --max-hours 1.6)"
    hb "quota: $(python3 cmu/finetune/flight/kaggle_flight.py quota 2>&1 | grep GPU | tr -s ' ')"
    python3 $T/detach.py $T/logs/ts3_teach_gh.out zsh $T/ts3_after_kaggle.sh ts3-teach-g ts3-teach-h t3g t3h ts3_teach_gh >> $H
    hb "DONE"
    exit 0
  fi
  [ $((i % 5)) -eq 1 ] && hb "push refused (try $i): $(echo "$OUT" | grep -i "error\|gate\|refus\|maximum" | head -1 | cut -c1-160)"
  sleep 120
done
hb "FAILED push refused for 2 h"
exit 1
