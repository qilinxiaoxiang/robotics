#!/bin/bash
# Does a right spin stall at the same absolute heading wherever it starts? Left, then right twice, then right again.
cd ~/rt/microduck-sim/guide/firmware/mac
P=~/.venvs/duck-policy/bin/python
run() { date +%s.%N; echo "== $*"; timeout -s INT 15 $P -u turn_test.py --vx 0 "$@" | tail -n 1 | cut -c1-130; sleep 3; }
run --vtheta 0.5 --secs 6
run --vtheta -0.5 --secs 6
run --vtheta -0.5 --secs 6
run --vtheta -0.5 --secs 6
