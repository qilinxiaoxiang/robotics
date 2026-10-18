#!/bin/zsh
cd /Users/xiangzheng/code/robotics/microduck-sim/guide/print/head-wires-20261014/scratch
R=/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py
run() { # route sets tag
  for attempt in 1 2 3 4 5 6 7 8; do
    /tmp/microduck-cad-venv/bin/python $R --max-mib 2500 --seconds 290 --wait-lock-seconds 60 --report runs/eval_$1$3.json -- /tmp/microduck-cad-venv/bin/python -u eval_routes.py $1 250 $2 $3 > eval_$1$3.log 2>&1
    rc=$?; echo "$1 $3 rc=$rc attempt=$attempt" >> run_evals.status
    if [ $rc -ne 75 ]; then break; fi; sleep 30
  done
}
run designed jawSweep -B
run leftrear policy,pickup,mjcf -A
run leftrear yawSweep,rollSweep,rollYaw,walkBox,jawSweep -B
run hybrid policy,pickup,mjcf -A
run hybrid yawSweep,rollSweep,rollYaw,walkBox,jawSweep -B
echo ALLDONE >> run_evals.status
