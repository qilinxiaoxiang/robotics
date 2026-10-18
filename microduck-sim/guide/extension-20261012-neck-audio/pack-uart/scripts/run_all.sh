#!/bin/zsh
# Rerun the whole pack-UART study under the bounded CAD runner (one exclusive job at a time, retried while another CAD job
# holds the lock). Order: sockets -> options (study solids + exact checks) -> renders -> walking sweep of the added material.
cd "${0:A:h}"
PY=/tmp/microduck-cad-venv/bin/python
RUN=/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py
job() {  # job <name> <max-mib> <seconds> <script> [args...]
  local name=$1 mib=$2 sec=$3; shift 3
  for i in $(seq 1 120); do
    $PY $RUN --max-mib $mib --seconds $sec --wait-lock-seconds 60 --report ../run-report-$name.json -- $PY "$@" > ../$name.log 2>&1
    rc=$?; [ $rc -ne 75 ] && break; sleep 30
  done
  echo "$name exit $rc"; [ $rc -eq 0 ] || exit $rc
}
[ -n "$SKIP_SOCKETS" ] || job sockets 1024 600 measure_sockets.py
[ -n "$SKIP_OPTIONS" ] || job options 1400 1200 options.py
job render 1024 600 render.py
job sweep-left 1400 900 sweep_added.py uart left
job sweep-right 1400 900 sweep_added.py uart right
job summary 512 120 summarize.py
