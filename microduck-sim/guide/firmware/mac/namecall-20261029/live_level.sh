#!/bin/bash
# Live microphone level bar (live_level.py); the raw 4-channel stream is also kept in ~/duck-logs/live_<HHMMSS>.raw
# (S32_LE, 48 kHz, 4 channels, headerless). Run on the A7Z:
#   ~/rt/microduck-sim/guide/firmware/mac/namecall-20261029/live_level.sh [seconds]
secs=${1:-120}
pkill -f "^/home/radxa/.venvs/duck-policy/bin/python namecall.py" && sleep 1
dev=$(arecord -l | awk -F'[ :]' '/sndi2s0/ {print "hw:" $2 ",0"; exit}')
[ -n "$dev" ] || { echo "no sndi2s0 capture card"; exit 1; }
raw="$HOME/duck-logs/live_$(date +%H%M%S).raw"
echo "live level for $secs s; quiet first 3 s to learn the floor; raw copy $raw"
arecord -q -D "$dev" -c 4 -r 48000 -f S32_LE -t raw -d "$secs" | tee "$raw" | /home/radxa/.venvs/duck-policy/bin/python "$(dirname "$0")/live_level.py"
