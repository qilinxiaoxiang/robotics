#!/bin/zsh
cd /Users/xiangzheng/code/robotics/microduck-sim/guide/print/head-wires-20261014/scratch
until grep -q ALLDONE2 run_evals2.status 2>/dev/null; do sleep 10; done
R=/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py
run() { for attempt in 1 2 3 4 5 6; do
    /tmp/microduck-cad-venv/bin/python $R --max-mib 2500 --seconds 290 --wait-lock-seconds 60 --report runs/eval_$1$3.json -- /tmp/microduck-cad-venv/bin/python -u eval_routes.py $1 220 $2 $3 > eval_$1$3.log 2>&1
    rc=$?; echo "$1 $3 rc=$rc attempt=$attempt" >> run_evals3.status; if [ $rc -ne 75 ]; then break; fi; sleep 30; done; }
run designed walkBox -C
run leftrear mjcf -A2
echo ALLDONE3 >> run_evals3.status
