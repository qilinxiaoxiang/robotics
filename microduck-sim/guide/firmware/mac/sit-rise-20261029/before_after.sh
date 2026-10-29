#!/bin/zsh
# before_after.sh: the in-process sit -> stand-up set "ba" and the teleop batch under the 2 s timer (var-before20261029,
# walk_brain.py from e4a92b4) and under the evidence hand-over (rt, the working tree), then the fake_pi seats of the
# runner path under the evidence hand-over. Mac mini; results in each copy's sit-rise-20261029/results/.
set -u
PY=~/.venvs/microduck-dyn/bin/python
S=~/sims/bvh-refit-20261029
for root in $S/var-before20261029 $S/rt; do
  ( cd $root/microduck-sim/guide/firmware/mac/sit-rise-20261029 && $PY rise_batch.py ba --jobs 5 > results/ba.out 2>&1 ) &
done
wait
for root in $S/var-before20261029 $S/rt; do
  ( cd $root/microduck-sim/guide/firmware/mac && $PY teleop_sim_batch.py > sit-rise-20261029/results/teleop.out 2>&1 ) &
done
wait
cd $S/rt/microduck-sim/guide/firmware/mac/sit-rise-20261029
$PY fakepi_seat.py after_runner --port 9900 &
$PY fakepi_seat.py after_nocomp --port 9910 --no-compensation &
$PY fakepi_seat.py after_runner_b --port 9920 &
$PY fakepi_seat.py after_tostand --port 9930 --to-stand &
wait
