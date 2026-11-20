#!/bin/zsh
# Round 3: wait for the paired teacher kernel (ts3-teach-a + ts3-teach-b), fetch it, stage every checkpoint and score
# the chatter gates on them (ts3_gates.py, Modal). Polling and file conversion only on the MacBook; the episodes run on
# Modal. Started detached (nohup, parent launchd) so it outlives the session's turn:
#   nohup zsh train/ts3_after_teach.sh > train/logs/ts3_after_teach.out 2>&1 < /dev/null &
# Heartbeat: train/logs/ts3_teach_heartbeat.txt, one line per event, last line DONE or FAILED.
# Gives up 2 h 30 min after its start (the kernel's cap is 1.6 h plus setup and queue).
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
RL=/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl
MODAL=/Users/xiangzheng/code/robotics/omx-local/.venv/bin/modal
GPY=/Users/xiangzheng/.venvs/microduck-walk/bin/python
H=$T/logs/ts3_teach_heartbeat.txt
hb() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*" >> $H }
echo "$(date +%Y-%m-%dT%H:%M:%S) watch START pid $$ kernel microduck-ts3-teach-a" > $H
cd $RL
ST=""
for i in $(seq 1 75); do
  ST=$(python3 cmu/finetune/flight/kaggle_flight.py status ts3-teach-a 2>&1 | grep -v outdated | tail -1 | cut -c1-160)
  hb "kaggle $ST"
  case "$ST" in
    *COMPLETE*|*ERROR*|*CANCEL*) break ;;
  esac
  sleep 120
done
case "$ST" in
  *COMPLETE*|*ERROR*|*CANCEL*) ;;
  *) hb "FAILED kernel not finished after 2 h 30 min"; exit 1 ;;
esac
python3 cmu/finetune/flight/kaggle_flight.py fetch ts3-teach-a > $T/logs/fetch_ts3-teach-a.log 2>&1
hb "fetch EXIT $?"
DA=($(zsh $T/ts2_stage.sh ts3-teach-a ts3-teach-a t3a 2>> $T/logs/ts3_after_teach.err))
DB=($(zsh $T/ts2_stage.sh ts3-teach-a ts3-teach-b t3b 2>> $T/logs/ts3_after_teach.err))
hb "staged ${#DA} + ${#DB} checkpoints: $DA $DB"
if [ $((${#DA} + ${#DB})) -eq 0 ]; then hb "FAILED no checkpoint staged (see logs/fetch_ts3-teach-a.log)"; exit 1; fi
cd $T/..
python3 train/ts3_gates.py spec t3teach $DA $DB > $T/logs/gates_t3teach_spec.log 2>&1
hb "modal metered before: $($MODAL billing summary 2>&1 | grep -i metered | tr -s ' ')"
$MODAL run train/flight_eval_modal.py --spec train/eval/spec_gate_t3teach.json > $T/logs/gates_t3teach_run.log 2>&1
hb "modal run EXIT $?"
hb "modal metered after: $($MODAL billing summary 2>&1 | grep -i metered | tr -s ' ')"
$GPY train/ts3_gates.py score $DA $DB --teacher > $T/logs/gates_t3teach_score.log 2>&1
hb "gates scored: $(grep -c 'verdict PASS' $T/logs/gates_t3teach_score.log) PASS of $(grep -c '^gates ' $T/logs/gates_t3teach_score.log) (logs/gates_t3teach_score.log)"
hb "DONE"
