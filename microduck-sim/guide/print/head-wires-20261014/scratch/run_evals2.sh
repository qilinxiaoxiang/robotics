#!/bin/zsh
cd /Users/xiangzheng/code/robotics/microduck-sim/guide/print/head-wires-20261014/scratch
until grep -q ALLDONE run_evals.status 2>/dev/null; do sleep 10; done
R=/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py
run() { # route sets tag
  for attempt in 1 2 3 4 5 6 7 8; do
    /tmp/microduck-cad-venv/bin/python $R --max-mib 2500 --seconds 290 --wait-lock-seconds 60 --report runs/eval_$1$3.json -- /tmp/microduck-cad-venv/bin/python -u eval_routes.py $1 200 $2 $3 > eval_$1$3.log 2>&1
    rc=$?; echo "$1 $3 rc=$rc attempt=$attempt" >> run_evals2.status
    if [ $rc -ne 75 ]; then break; fi; sleep 30
  done
}
run hybrid pickup -A2
run hybrid mjcf -A3
run leftrear jawSweep -C
# whatever hybrid-B did not finish
missing=$(/tmp/microduck-cad-venv/bin/python -c "
import json,os
want=['yawSweep','rollSweep','rollYaw','walkBox','jawSweep']
have=set()
if os.path.exists('eval-hybrid-B.json'):
    d=json.load(open('eval-hybrid-B.json')); have={k for k,v in d['sets'].items() if v['posesChecked']==v['poses']}
print(','.join([w for w in want if w not in have]))")
if [ -n "$missing" ]; then run hybrid $missing -B2; fi
for attempt in 1 2 3 4 5 6; do
  /tmp/microduck-cad-venv/bin/python $R --max-mib 2500 --seconds 290 --wait-lock-seconds 60 --report runs/render_routes.json -- /tmp/microduck-cad-venv/bin/python -u render_routes.py > render_routes.log 2>&1
  rc=$?; echo "render rc=$rc attempt=$attempt" >> run_evals2.status
  if [ $rc -ne 75 ]; then break; fi; sleep 30
done
echo ALLDONE2 >> run_evals2.status
