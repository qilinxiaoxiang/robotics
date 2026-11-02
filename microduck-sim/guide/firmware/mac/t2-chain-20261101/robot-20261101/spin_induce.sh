#!/bin/bash
# In-place spins on the robot: short ones as approach sends them, long ones right and left, and one with the head lowered.
cd ~/rt/microduck-sim/guide/firmware/mac
P=~/.venvs/duck-policy/bin/python
run() { date +%s.%N; echo "== $*"; timeout -s INT 15 $P -u turn_test.py --vx 0 "$@" | tail -n 6 | cut -c1-200; date +%s.%N; sleep 4; }
run --vtheta -0.5 --secs 1.6
run --vtheta -0.5 --secs 1.6
run --vtheta -0.5 --secs 6
run --vtheta 0.5 --secs 6
run --vtheta -0.5 --secs 6 --head-pitch 1.0 --head-after 1
