#!/bin/bash
# Listen-only name-call check on the A7Z: detects and localises calls, writes nothing to the brain, plays nothing.
# The robot does not move. Run on the A7Z:  ~/rt/microduck-sim/guide/firmware/mac/namecall-20261029/listen_only.sh [seconds]
# Log: ~/duck-logs/namecall_listen_<HHMMSS>.jsonl (+ .out); the path is also in /tmp/namecall_listen_path.
secs=${1:-600}
cd "$HOME/rt/microduck-sim/guide/firmware/mac" || exit 1
pkill -f "^/home/radxa/.venvs/duck-policy/bin/python namecall.py" && sleep 1
log="$HOME/duck-logs/namecall_listen_$(date +%H%M%S).jsonl"
echo "$log" > /tmp/namecall_listen_path
setsid nohup timeout "$secs" /home/radxa/.venvs/duck-policy/bin/python namecall.py --no-head --mute --no-sound --no-gate \
  --log "$log" > "${log%.jsonl}.out" 2>&1 < /dev/null &
sleep 3
echo "listening for $secs s until $(date -d "+$secs sec" +%H:%M:%S), log $log"
tail -2 "${log%.jsonl}.out"
