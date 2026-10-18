#!/bin/zsh
cd /Users/xiangzheng/code/robotics/microduck-sim/guide/print/head-wires-20261014/scratch
until grep -q ALLDONE5 run_evals5.status 2>/dev/null; do sleep 10; done
R=/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py
for attempt in 1 2 3 4 5 6; do
  /tmp/microduck-cad-venv/bin/python $R --max-mib 2500 --seconds 240 --wait-lock-seconds 60 --report runs/part_dist_q0.json -- /tmp/microduck-cad-venv/bin/python -u part_dist_q0.py > part_dist_q0.log 2>&1
  rc=$?; echo "partdist rc=$rc attempt=$attempt" >> run_evals6.status; if [ $rc -ne 75 ]; then break; fi; sleep 30; done
for attempt in 1 2 3 4 5 6; do
  /tmp/microduck-cad-venv/bin/python $R --max-mib 2500 --seconds 290 --wait-lock-seconds 60 --report runs/eval_leftrear-C2.json -- /tmp/microduck-cad-venv/bin/python -u eval_routes.py leftrear 230 walkBox -C2 > eval_leftrear-C2.log 2>&1
  rc=$?; echo "leftrear -C2 rc=$rc attempt=$attempt" >> run_evals6.status; if [ $rc -ne 75 ]; then break; fi; sleep 30; done
echo ALLDONE6 >> run_evals6.status
