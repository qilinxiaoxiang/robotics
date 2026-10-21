#!/bin/zsh
# serial, one sim process at a time, each clamped to 600 s
cd /private/tmp/claude-501/-Users-xiangzheng-code-robotics/74602e44-fa79-4564-a436-c7a3c8ce2ecd/scratchpad
PY=~/.venvs/microduck-dyn/bin/python
for spec in "ol -4.84 4.89 30 roll_ol_inner_up.json" "ol 4.84 -4.89 30 roll_ol_outer_up.json" "s61 -4.84 4.89 33 roll_s61_inner_up.json" "s61 4.84 -4.89 33 roll_s61_outer_up.json" "s61 1.20 -1.18 33 roll_s61_asfitted.json"; do
  set -- ${=spec}
  echo "=== $5 ($1 L $2 R $3 T $4) start $(date +%T)"
  /usr/bin/time -p timeout 600 $PY sole_roll_sim.py $2 $3 $1 $4 $5 2>&1 | grep -v "^mode ->"
  echo "=== $5 exit $? end $(date +%T)"
done
echo ALL DONE
