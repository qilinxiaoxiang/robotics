#!/bin/bash
# Live microphone level bar (live_level.py). Run on the A7Z:
#   ~/rt/microduck-sim/guide/firmware/mac/namecall-20261029/live_level.sh [seconds]
secs=${1:-120}
pkill -f "^/home/radxa/.venvs/duck-policy/bin/python namecall.py" && sleep 1
dev=$(arecord -l | awk -F'[ :]' '/sndi2s0/ {print "hw:" $2 ",0"; exit}')
[ -n "$dev" ] || { echo "no sndi2s0 capture card"; exit 1; }
echo "live level for $secs s; quiet first 3 s to learn the floor"
arecord -q -D "$dev" -c 4 -r 48000 -f S32_LE -t raw -d "$secs" | /home/radxa/.venvs/duck-policy/bin/python "$(dirname "$0")/live_level.py"
