#!/bin/zsh
# Runs ON the Mac mini, detached (round 3). Stages one after another under mini_lock.sh, a heartbeat line after every
# stage. Started from the MacBook with train/ts3_mini_start.sh, which returns at once; the chain's parent is launchd.
#   zsh ts3_mini_chain.sh <name> <stage> [<stage> ...]
# Stages: smoke_a (teacher_smoke.py, delta universal5t, start ts_start), smoke_b (same, start walk61).
# Heartbeat: ~/flight-heartbeat/<name>.txt, one line per event: time, stage, START | EXIT <code>, and a last line
# DONE or FAILED. Logs: ~/flight-heartbeat/<name>_<stage>.log; results under /tmp/ts3_<stage>/.
NAME=$1; shift
M=$HOME/code/flight-train-mirror/robotics/microduck-sim
FL=$M/extensions/flight-20261110/train
A=$M/smoke-assets
HB=$HOME/flight-heartbeat
mkdir -p $HB
H=$HB/$NAME.txt
echo "$(date +%Y-%m-%dT%H:%M:%S) chain START pid $$ stages $*" > $H
BAD=0
for ST in "$@"; do
  echo "$(date +%Y-%m-%dT%H:%M:%S) $ST START" >> $H
  case $ST in
    smoke_a) INIT=ts_start.onnx ;;
    smoke_b) INIT=ts3_walk61.onnx ;;
    *) echo "$(date +%Y-%m-%dT%H:%M:%S) $ST EXIT 64 unknown stage" >> $H; BAD=1; continue ;;
  esac
  cd $M/microduck_rl
  FLIGHT_MANIFESTS=$FL/manifests FLIGHT_ANCHOR_ONNX=$A/ts3_walk61.onnx zsh $FL/mini_lock.sh run timeout 590 \
    .venv/bin/python cmu/finetune/flight/teacher_smoke.py --init $A/$INIT --envs 64 --iters 5 --delta universal5t \
    --outdir /tmp/ts3_$ST > $HB/${NAME}_$ST.log 2>&1 < /dev/null
  RC=$?
  [ -f /tmp/ts3_$ST/teacher_smoke.json ] || RC=${RC/#0/65}
  echo "$(date +%Y-%m-%dT%H:%M:%S) $ST EXIT $RC" >> $H
  [ $RC -eq 0 ] || BAD=1
done
if [ $BAD -eq 0 ]; then echo "$(date +%Y-%m-%dT%H:%M:%S) chain DONE" >> $H; else echo "$(date +%Y-%m-%dT%H:%M:%S) chain FAILED" >> $H; fi
