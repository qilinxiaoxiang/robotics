#!/bin/zsh
# Round 3: when the first teacher kernel has returned, read whether its walk61-start arm (ts3-teach-b) was stopped by
# the tracking guard before iteration 900; if so push the walk61 start again as a pair with --track-grace 700
# (ts3-teach-e seed 2, ts3-teach-f seed 3; Modal ts3m-w61g is seed 1) into the freed GPU session and start its
# follow-up (ts3_after_kaggle.sh). Polling only.
#   python3 train/detach.py train/logs/ts3_relaunch_w61.out zsh train/ts3_relaunch_w61.sh
# Heartbeat: train/logs/ts3_relaunch_w61_heartbeat.txt (last line DONE or FAILED); the pair's own heartbeat is
# train/logs/ts3_teach_ef_heartbeat.txt.
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
RL=/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl
H=$T/logs/ts3_relaunch_w61_heartbeat.txt
hb() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*" >> $H }
echo "$(date +%Y-%m-%dT%H:%M:%S) START pid $$ waiting for the fetch of ts3-teach-a" > $H
for i in $(seq 1 90); do
  grep -q "fetch EXIT\|FAILED" $T/logs/ts3_teach_heartbeat.txt && break
  sleep 60
done
P=$T/kaggle/out/ts3-teach-a/runs/ts3-teach-b/progress.json
if [ ! -f $P ]; then hb "FAILED no progress.json of ts3-teach-b after the fetch"; exit 1; fi
IT=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['iter'])" $P)
hb "ts3-teach-b last iteration $IT"
if [ $IT -ge 900 ]; then hb "ts3-teach-b ran to the end, no relaunch"; hb "DONE"; exit 0; fi
cd $RL
F="--delta universal5t --onnx /root/assets/init/walk61.onnx --manifest /root/assets/manifests/flightpack-none.json --max-iters 1000 --max-hours 1.6 --save-interval 125 --warmup-iters 100 --max-lr 0.0001 --guard-fraction 0.0 --track-guard 2.0 --track-grace 700"
for i in $(seq 1 30); do
  OUT=$(python3 cmu/finetune/flight/kaggle_flight.py push run --run-name ts3-teach-e --pair-run-name ts3-teach-f -- ${=F} --seed 2 -- ${=F} --seed 3 2>&1)
  if echo "$OUT" | grep -q "successfully pushed"; then
    hb "pushed microduck-ts3-teach-e (ts3-teach-e seed 2, ts3-teach-f seed 3, walk61 start, --track-grace 700, --max-hours 1.6)"
    hb "quota: $(python3 cmu/finetune/flight/kaggle_flight.py quota 2>&1 | grep GPU | tr -s ' ')"
    python3 $T/detach.py $T/logs/ts3_teach_ef.out zsh $T/ts3_after_kaggle.sh ts3-teach-e ts3-teach-f t3e t3f ts3_teach_ef >> $H
    hb "DONE"
    exit 0
  fi
  hb "push refused: $(echo "$OUT" | grep -i "error\|gate\|refus\|maximum" | head -1 | cut -c1-160)"
  sleep 120
done
hb "FAILED push refused for 1 h"
exit 1
