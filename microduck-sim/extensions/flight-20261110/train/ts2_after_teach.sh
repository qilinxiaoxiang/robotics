#!/bin/zsh
# Round 2: wait for the two teacher kernels, and as each one ends fetch it, stage every checkpoint and run the
# runtime-simulation selection cases on it (ts2_pick.py). When the first one ends, the one-frame control pair takes
# the freed Kaggle session. Gives up 2 h 15 min after its start (the kernels' own cap is 1.6 h plus setup).
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
RL=/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl
C="--onnx /root/assets/init/ts_start.onnx --manifest /root/assets/manifests/flightpack-none.json --max-iters 1000 --max-hours 1.6 --save-interval 125 --warmup-iters 100 --max-lr 0.0001 --guard-fraction 0.0 --track-guard 2.0 --seed 1"
cd $RL
typeset -A TAG
TAG=(ts2-teach t2a ts2-teach-b t2b)
typeset -A DONE
CTRL=0
for i in $(seq 1 135); do
  for R in ts2-teach ts2-teach-b; do
    [ -n "$DONE[$R]" ] && continue
    ST=$(python3 cmu/finetune/flight/kaggle_flight.py status $R 2>&1 | tail -1)
    case "$ST" in
      *RUNNING*|*QUEUED*) ;;
      *COMPLETE*|*ERROR*|*CANCEL*)
        DONE[$R]=1
        echo "$(date +%T) $R: $ST"
        python3 cmu/finetune/flight/kaggle_flight.py fetch $R > $T/logs/fetch_$R.log 2>&1
        if [ $CTRL -eq 0 ]; then
          CTRL=1
          python3 cmu/finetune/flight/kaggle_flight.py push run --run-name ts2-ctrl --pair-run-name ts2-ctrl-b -- --delta universal4 ${=C} -- --delta universal4b ${=C} 2>&1 | tail -4 | cut -c1-200
        fi
        DIRS=($(zsh $T/ts2_stage.sh $R $R $TAG[$R]))
        echo "$(date +%T) staged $DIRS"
        python3 $T/ts2_pick.py $DIRS > $T/logs/ts2_pick_$TAG[$R].log 2>&1
        grep "total falls" $T/logs/ts2_pick_$TAG[$R].log | cut -c1-330
        ;;
      *) echo "$(date +%T) $R: $ST" ;;
    esac
  done
  [ -n "$DONE[ts2-teach]" ] && [ -n "$DONE[ts2-teach-b]" ] && break
  sleep 60
done
echo "AFTERTEACHDONE $(date +%T)"
