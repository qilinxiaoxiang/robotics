#!/bin/zsh
# Round 3: ts3_after_teach.sh for any paired teacher kernel. Wait for the kernel, fetch it, stage every checkpoint
# and score the chatter gates on them (ts3_gates.py, episodes on Modal). Polling and file conversion only here.
#   python3 train/detach.py train/logs/<name>.out zsh train/ts3_after_kaggle.sh <kernel run> <run B> <tag A> <tag B> <name>
# Heartbeat: train/logs/<name>_heartbeat.txt, one line per event, "GATE PASS|FAIL <folder>" per save, last line DONE
# or FAILED. Gives up 2 h 30 min after its start.
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
RL=/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl
MODAL=/Users/xiangzheng/code/robotics/omx-local/.venv/bin/modal
GPY=/Users/xiangzheng/.venvs/microduck-walk/bin/python
KA=$1; KB=$2; TA=$3; TB=$4; NAME=$5
H=$T/logs/${NAME}_heartbeat.txt
hb() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*" >> $H }
echo "$(date +%Y-%m-%dT%H:%M:%S) watch START pid $$ kernel microduck-$KA" > $H
cd $RL
ST=""
for i in $(seq 1 75); do
  ST=$(python3 cmu/finetune/flight/kaggle_flight.py status $KA 2>&1 | grep -v outdated | tail -1 | cut -c1-160)
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
python3 cmu/finetune/flight/kaggle_flight.py fetch $KA > $T/logs/fetch_$KA.log 2>&1
hb "fetch EXIT $?"
DA=($(zsh $T/ts2_stage.sh $KA $KA $TA 2>> $T/logs/$NAME.err))
DB=($(zsh $T/ts2_stage.sh $KA $KB $TB 2>> $T/logs/$NAME.err))
hb "staged ${#DA} + ${#DB} checkpoints: $DA $DB"
if [ $((${#DA} + ${#DB})) -eq 0 ]; then hb "FAILED no checkpoint staged (see logs/fetch_$KA.log)"; exit 1; fi
cd $T/..
python3 train/ts3_gates.py spec $NAME $DA $DB > $T/logs/gates_${NAME}_spec.log 2>&1
hb "modal metered before: $($MODAL billing summary 2>&1 | grep -i metered | tr -s ' ')"
$MODAL run train/flight_eval_modal.py --spec train/eval/spec_gate_$NAME.json > $T/logs/gates_${NAME}_run.log 2>&1
hb "modal run EXIT $?"
hb "modal metered after: $($MODAL billing summary 2>&1 | grep -i metered | tr -s ' ')"
for D in $DA $DB; do
  if $GPY train/ts3_gates.py score $D --teacher > $T/logs/gates_${D}_score.log 2>&1; then hb "GATE PASS $D"; else hb "GATE FAIL $D ($(grep -c '^FAIL' $T/logs/gates_${D}_score.log) lines, logs/gates_${D}_score.log)"; fi
done
hb "DONE"
