#!/bin/zsh
# Stage B0 of ../TRAIN-CONTRACT.json: the robot-agreement yardstick run (b0_yardstick.py) ON the Mac mini, detached,
# under the mirror's lock.
#   cd ~/code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110
#   nohup zsh train/b0_yardstick.sh [key=value ...] > /dev/null 2>&1 < /dev/null &
# Heartbeat train/logs/b0_<out>_heartbeat.txt (default out yardstick_b0; last line DONE or FAILED), log
# train/logs/b0_<out>.log.
FL=$HOME/code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110
PY=$HOME/.venvs/flight-sim/bin/python
O=yardstick_b0
for a in "$@"; do case $a in out=*) O=${a#out=};; esac; done
cd $FL
mkdir -p train/logs
zsh train/mini_lock.sh run $PY train/b0_yardstick.py "$@" > train/logs/b0_$O.log 2>&1
RC=$?
tail -1 train/logs/b0_${O}_heartbeat.txt 2>/dev/null | grep -qE "DONE|FAILED" || echo "$(date +%Y-%m-%dT%H:%M:%S) FAILED exit $RC: $(grep -E 'Error|assert|refus' train/logs/b0_$O.log | tail -1 | cut -c1-300)" >> train/logs/b0_${O}_heartbeat.txt
