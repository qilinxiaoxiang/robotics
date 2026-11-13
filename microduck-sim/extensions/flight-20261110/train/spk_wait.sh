#!/bin/zsh
# Wait on a seeing-pick pack run on Modal: exit when progress.json reports iteration >= <target>, the app has stopped,
# or Modal sent an alert mail. Checks every 5 minutes, alert mail every 10. Prints the reason and the last record.
# Usage: zsh spk_wait.sh <run> <app-id> <target-iteration>     (Volume microduck-seepick-<run>)
M=/Users/xiangzheng/code/robotics/omx-local/.venv/bin/modal
RUN=$1; APP=$2; WANT=${3:-100}
P=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train/modal/out/$RUN
mkdir -p $P
n=0
while true; do
  $M volume get --force microduck-seepick-$RUN runs/$RUN/progress.json $P/progress.json > /dev/null 2>&1
  it=$(python3 -c "import json;print(json.load(open('$P/progress.json')).get('iteration',-1))" 2>/dev/null)
  if [ -n "$it" ] && [ "$it" -ge "$WANT" ]; then echo "ITERATION $it $(date +%H:%M)"; cat $P/progress.json; exit 0; fi
  st=$($M app list --json 2>/dev/null | python3 -c "
import json,sys
for a in json.load(sys.stdin):
    if a['app_id']=='$APP': print(a['state'], a['tasks'])")
  case "$st" in stopped*) echo "APP STOPPED it=${it:-none} $(date +%H:%M)"; cat $P/progress.json 2>/dev/null; exit 0;; esac
  if [ $((n % 2)) -eq 1 ]; then
    w=$(python3 ~/code/claude-config/scripts/modal_watch.py --hours 1 2>&1)
    if print -r -- "$w" | grep -q "alert emails: [1-9]"; then echo "ALERT MAIL $(date +%H:%M)"; print -r -- "$w" | tail -8; exit 0; fi
  fi
  n=$((n+1))
  echo "$(date +%H:%M) state=$st it=${it:-none}"
  sleep 300
done
