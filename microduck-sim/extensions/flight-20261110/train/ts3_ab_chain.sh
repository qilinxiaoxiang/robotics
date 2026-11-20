#!/bin/zsh
# Round 3, 2026-11-20 08:30: reads of run AB's saves. Runs ON the Mac mini as one detached chain (nohup, parent 1),
# every stage under the mirror's lock, evaluation only (no training):
#   cd ~/code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110
#   nohup zsh train/ts3_ab_chain.sh > /dev/null 2>&1 < /dev/null &
# Stages (output train/logs/ts3_ab_chain_<stage>.out, heartbeat train/logs/ts3_ab_chain_heartbeat.txt, last line
# DONE or FAILED):
#   avg    weight means of saves 100..160 (s3ABm4_160) and 120..160 (s3ABm3_160), exported like a save
#   cells  the failing gate cells on the means and on s3AB_140: pack walk at gain 200 and 400 (10 seeds, the gate's
#          episode: nominal pack, --stand-s 0), no pack standing at gain 400 (10 seeds)
#   s140   s3AB_140: the stop at gain 200 with heading hold on and off (20 seeds), gain 400 (20 seeds), per-second
#          traces at gain 400 from the start, which joints jump
#   mode   s3AB_120 / s3AB_160 / s3AB_140 with the pack at gain 200, per second from the start (walking or not)
FL=$HOME/code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110
PY=$HOME/.venvs/flight-sim/bin/python
RLPY=$FL/../../microduck_rl/.venv/bin/python
LK=$FL/train/mini_lock.sh
HB=$FL/train/logs/ts3_ab_chain_heartbeat.txt
OFF='{"HEADING_KP": 0, "HEADING_KI": 0}'
cd $FL
hb() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*" >> $HB; }
out() { echo $FL/train/logs/ts3_ab_chain_$1.out; }
hb "START pid $$"

{
  $RLPY train/ts3_avg_saves.py s3AB s3ABm4_160 100 120 140 160
  $RLPY train/ts3_avg_saves.py s3AB s3ABm3_160 120 140 160
} > $(out avg) 2>&1
grep -q "^s3ABm3_160: mean of saves" $(out avg) || { hb "FAILED avg: $(tail -1 $(out avg) | cut -c1-300)"; exit 1; }
hb "stage avg done"

{
  for D in s3ABm4_160 s3ABm3_160 s3AB_140; do
    for K in 200 400; do zsh $LK run $PY train/ts3_stop_where.py $D count=10 kp=$K 2>&1 | tail -2 | cut -c1-400; done
    zsh $LK run $PY train/ts3_still_where.py $D 0,1,2,3,4,5,6,7,8,9 kp=400 2>&1 | grep -E "seed|first call" | cut -c1-200
  done
} > $(out cells) 2>&1
hb "stage cells done: $(grep -c 'falls of' $(out cells)) count lines"

{
  echo "gain 200 heading hold on"; zsh $LK run $PY train/ts3_stop_where.py s3AB_140 count=20 kp=200 2>&1 | tail -2 | cut -c1-400
  echo "gain 200 heading hold off"; zsh $LK run env FLIGHT_BRAIN_SET=$OFF $PY train/ts3_stop_where.py s3AB_140 count=20 kp=200 2>&1 | tail -1 | cut -c1-400
  echo "gain 400"; zsh $LK run $PY train/ts3_stop_where.py s3AB_140 count=20 kp=400 2>&1 | tail -2 | cut -c1-400
  echo "gain 400 heading hold off"; zsh $LK run env FLIGHT_BRAIN_SET=$OFF $PY train/ts3_stop_where.py s3AB_140 count=20 kp=400 2>&1 | tail -1 | cut -c1-400
  echo "gain 400 traces"; zsh $LK run $PY train/ts3_stop_where.py s3AB_140 0 1 2 3 kp=400 from=0 2>&1 | grep -v Warning | cut -c1-330
  for S in 0 1 2 3; do
    echo "gain 400 jumps seed $S"
    zsh $LK run env TS3_SEED=$S $PY train/ts3_jump_where.py s3AB_140 nominal 0.25 --stand-s 0 --kp-rl 400 2>&1 | grep -v Warning | cut -c1-900
  done
} > $(out s140) 2>&1
hb "stage s140 done"

{
  for D in s3AB_120 s3AB_160 s3AB_140; do
    zsh $LK run $PY train/ts3_stop_where.py $D 0 1 kp=200 from=0 2>&1 | grep -v Warning | cut -c1-330
  done
} > $(out mode) 2>&1
hb "DONE"
