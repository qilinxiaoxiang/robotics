#!/bin/zsh
# Stage B0T of ../TRAIN-CONTRACT.json: the validation of the fan-thrust test (b0t_thrust.py) ON the Mac mini, detached,
# under the mirror's lock. Nothing is trained.
#   cd ~/code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110
#   nohup zsh train/b0t_thrust.sh [key=value ...] > /dev/null 2>&1 < /dev/null &
# Heartbeat train/logs/b0t_thrust_heartbeat.txt (one line per cell, last line DONE or FAILED), log
# train/logs/b0t_thrust.log; with out=<name> both carry _<name>. The mirror needs, beside train/: sim/flight.py with the
# --ground-hold options, sim/out/manifest_pack_nominal.json and sim/out/visual/manifest_pack_nominal.json (copied with
# their times kept, so the drawn-pack copy stays newer than its source); b0t_thrust.py checks them before any episode.
FL=$HOME/code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110
PY=$HOME/.venvs/flight-sim/bin/python
T=b0t_thrust
for a in "$@"; do case $a in out=yardstick_b0t) ;; out=*) T=b0t_thrust_${a#out=};; esac; done
cd $FL
mkdir -p train/logs
HBF=train/logs/${T}_heartbeat.txt
# the line of this start: an older run's DONE is then never the last line when this run leaves none of its own
print -P "%D{%Y-%m-%dT%H:%M:%S} QUEUED pid $$ (waiting for train/mini_lock.sh)" >> $HBF
zsh train/mini_lock.sh run $PY train/b0t_thrust.py "$@" > train/logs/$T.log 2>&1
RC=$?
# a run that left no DONE or FAILED line (the lock refused, the interpreter died) gets one here
if ! tail -1 $HBF | grep -qE "DONE|FAILED"; then
  {
    print -n -P "%D{%Y-%m-%dT%H:%M:%S} FAILED exit $RC: "
    grep -E 'Error|assert|refus|REFUSED' train/logs/$T.log | tail -1 | cut -c1-300 | tr -d '\n'
    print
  } >> $HBF
fi
