#!/bin/zsh
# fakepi_cause.sh: the runner's fake_pi + walk_brain seat, four plant/brain variants at once (distinct UDP ports),
# 4 seats each, current walk_brain code. Mac mini.
set -u
HERE=${0:A:h}
PY=~/.venvs/microduck-dyn/bin/python
cd $HERE
$PY fakepi_seat.py before_runner --port 9900 &
$PY fakepi_seat.py before_nocomp --port 9910 --no-compensation &
$PY fakepi_seat.py before_refit --port 9920 --refit &
$PY fakepi_seat.py before_nocomp_refit --port 9930 --no-compensation --refit &
wait
