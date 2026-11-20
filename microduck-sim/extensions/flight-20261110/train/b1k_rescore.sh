#!/bin/zsh
# Stage B1 of ../TRAIN-CONTRACT.json, attempt 2 (b1k_rescore.py), ON the Mac mini, detached, under the mirror's lock.
# One phase per launch:
#   phase=1 (the default)  the reference and the with-pack specialist fq2_1999 alone, all 20 cells (24 cells x 60
#                          episodes) -> train/out/rescore_b1k/summary.json with its own verdict
#   phase=2                the reference and the four round 3 teachers fed "known" and "as_trained" (164 cells),
#                          started separately later -> train/out/rescore_b1k/summary_teachers.json
#   cd ~/code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110
#   nohup zsh train/b1k_rescore.sh [phase=1|phase=2] [wait=<hours>] [key=value ...] > /dev/null 2>&1 < /dev/null &
# The whole chain of a phase is this one script: it first waits, without taking anything, while another job (attempt
# 1, or the other phase) holds the mirror's lock (mini_lock.sh by itself gives up after 90 min; wait=<hours>, default
# 12, whole hours), then runs the feed check and the scoring as one python job under train/mini_lock.sh run. A restart
# keeps finished cells. Heartbeat train/logs/b1k_rescore_heartbeat.txt (both phases; one line per finished cell, last
# line DONE or FAILED), log train/logs/b1k_rescore.log (appended). Other key=value arguments go to b1k_rescore.py
# (workers=, only=, check=only). A bare 1 or 2 is read as the phase.
FL=$HOME/code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110
PY=$HOME/.venvs/flight-sim/bin/python
LOCK=$HOME/.flight-mirror-sim.lock
WAIT_H=12
PHASE=1
ARGS=()
for a in "$@"; do case $a in wait=*) WAIT_H=${a#wait=};; phase=*) PHASE=${a#phase=};; 1|2) PHASE=$a;; *) ARGS+=("$a");; esac; done
cd $FL || exit 2
mkdir -p train/logs
HBF=train/logs/b1k_rescore_heartbeat.txt
case $PHASE in 1|2) ;; *) echo "$(date +%Y-%m-%dT%H:%M:%S) FAILED: phase=$PHASE is not 1 or 2; nothing ran" >> $HBF; exit 2;; esac
N0=0
[ -f $HBF ] && N0=$(wc -l < $HBF | tr -d ' ')
T0=$(date +%s)
NOTED=0
while h=$(cat $LOCK 2>/dev/null) && [ -n "$h" ] && kill -0 $h 2>/dev/null; do
  if [ $NOTED -eq 0 ]; then
    echo "$(date +%Y-%m-%dT%H:%M:%S) WAITING phase $PHASE pid $$: the mirror's lock is held by pid $h; looking every 60 s for up to $WAIT_H h" >> $HBF
    NOTED=1
  fi
  if [ $(( $(date +%s) - T0 )) -ge $(( WAIT_H * 3600 )) ]; then
    echo "$(date +%Y-%m-%dT%H:%M:%S) FAILED phase $PHASE: the mirror's lock was still held by pid $h after $WAIT_H h; nothing ran" >> $HBF
    exit 3
  fi
  sleep 60
done
echo "$(date +%Y-%m-%dT%H:%M:%S) b1k_rescore.sh pid $$ phase $PHASE args: ${ARGS[*]}" >> train/logs/b1k_rescore.log
zsh train/mini_lock.sh run $PY train/b1k_rescore.py phase=$PHASE "${ARGS[@]}" >> train/logs/b1k_rescore.log 2>&1
RC=$?
# a run that left no DONE or FAILED line of its own (the lock refused, the interpreter died) gets one here; an older
# run's DONE above line N0 does not count
tail -n +$((N0 + 1)) $HBF 2>/dev/null | tail -1 | grep -qE "DONE|FAILED" || echo "$(date +%Y-%m-%dT%H:%M:%S) FAILED phase $PHASE exit $RC: $(grep -E 'Error|assert|refus|REFUSED' train/logs/b1k_rescore.log | tail -1 | cut -c1-300)" >> $HBF
exit $RC
