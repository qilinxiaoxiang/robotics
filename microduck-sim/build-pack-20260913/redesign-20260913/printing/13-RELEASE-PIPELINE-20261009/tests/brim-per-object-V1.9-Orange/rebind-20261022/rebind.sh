#!/bin/zsh
# Rebind the V1.9 Orange brim acceptance run to release_pipeline_v2.py after the damageReprint field (2026-10-22).
cd ${0:A:h:h:h:h}
RB=tests/brim-per-object-V1.9-Orange/rebind-20261022; T=tests/brim-per-object-V1.9-Orange
RUNNER=../../head-redesign-20261008/run_bounded_cad.py; PY=/tmp/microduck-cad-venv/bin/python
export MICRODUCK_CAD_RESERVE_MIB=1024
job() { local n=$1 mib=$2; shift 2; /opt/homebrew/bin/python3 $RUNNER --max-mib $mib --seconds 600 --report $RB/$n-resource.json -- "$@" > $RB/$n.log 2>&1; echo "$n exit $?"; }
set -e
rm -rf $T/run
job step1 1000 $PY release_pipeline_v2.py prepare $T/manifest.json $T/run
job step2 1000 $PY release_pipeline_v2.py slice $T/run/preparation.json Orange Bambu
job step3 1600 $PY release_pipeline_v2.py slice $T/run/preparation.json Orange Elegoo
job brim-Bambu 400 $PY review_brim.py $T/run Orange Bambu --output $T/brim-review-v2-Orange-Bambu.json
job brim-Elegoo 400 $PY review_brim.py $T/run Orange Elegoo --output $T/brim-review-v2-Orange-Elegoo.json
job step4 700 $PY release_pipeline_v2.py package $T/run/preparation.json
job verify 700 $PY verify_release_v2.py $T/run --output $T/run/final-binding-check-v2.json
$PY -m unittest test_pipeline_v2 2>&1 | tail -3
