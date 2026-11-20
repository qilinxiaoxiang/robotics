#!/bin/zsh
# Stage B1 of ../TRAIN-CONTRACT.json: the 60-episode rescore of the deployable round 3 saves (b1_rescore.py) ON the Mac
# mini, detached, under the mirror's lock.
#   cd ~/code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110
#   nohup zsh train/b1_rescore.sh [key=value ...] > /dev/null 2>&1 < /dev/null &
# Heartbeat train/logs/b1_<out>_heartbeat.txt (default out rescore_b1; one line per cell, last line DONE or FAILED), log
# train/logs/b1_<out>.log. With smoke=1 both names carry _smoke (the feed check; b1_rescore.py's docstring).
FL=$HOME/code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110
PY=$HOME/.venvs/flight-sim/bin/python
O=rescore_b1
S=""
for a in "$@"; do case $a in out=*) O=${a#out=};; smoke=0|smoke=) ;; smoke=*) S=_smoke;; esac; done
cd $FL
mkdir -p train/logs
HBF=train/logs/b1_${O}${S}_heartbeat.txt
N0=0
[ -f $HBF ] && N0=$(wc -l < $HBF | tr -d ' ')
zsh train/mini_lock.sh run $PY train/b1_rescore.py "$@" > train/logs/b1_$O$S.log 2>&1
RC=$?
# a run that left no DONE or FAILED line of its own (the lock refused, the interpreter died) gets one here; an older
# run's DONE above line N0 does not count
tail -n +$((N0 + 1)) $HBF 2>/dev/null | tail -1 | grep -qE "DONE|FAILED" || echo "$(date +%Y-%m-%dT%H:%M:%S) FAILED exit $RC: $(grep -E 'Error|assert|refus|REFUSED' train/logs/b1_$O$S.log | tail -1 | cut -c1-300)" >> $HBF
