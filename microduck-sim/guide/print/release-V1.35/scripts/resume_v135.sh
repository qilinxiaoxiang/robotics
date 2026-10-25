#!/bin/zsh
# Resume run_v135.sh after the Elegoo support-map job (the slices, reviews and brim checks are already in run/ and review/).
set -e
REL=${0:A:h:h}; PRINT=$REL:h; SIM=$PRINT:h:h
PIPE=$SIM/build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009
RUNNER=$SIM/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py
PY=/tmp/microduck-cad-venv/bin/python
export MICRODUCK_CAD_RESERVE_MIB=1024
job() {
  local name=$1 mib=$2 dir=$3; shift 3
  local rc=75; local tries=0
  while [ $rc -eq 75 ] && [ $tries -lt 20 ]; do
    (cd $dir && /opt/homebrew/bin/python3 $RUNNER --max-mib $mib --seconds 600 --wait-lock-seconds 60 --report $REL/logs/$name-resource.json -- "$@") > $REL/logs/$name.log 2>&1; rc=$?; tries=$((tries+1))
  done
  echo "$name exit $rc"; grep -v 'lock holder' $REL/logs/$name.log | tail -3 | cut -c1-300
  [ $rc -eq 0 ]
}
C=Orange; M=Elegoo
job support-map-$C-$M 1024 $REL $PY $PRINT/orientation-study/scripts/support_map.py $REL/run $C $M $REL/review/${C}_${M}-support-map.png $REL/review/${C}_${M}-support-map.json
job readback-$C-$M 1024 $REL $PY $PRINT/orientation-study/scripts/slice_readback.py $REL/run $C $M $REL/review/${C}_${M}-readback.json
job native-review 600 $REL $PY scripts/make_native_review.py
job package 1600 $REL $PY $PIPE/release_pipeline_v2.py package $REL/run/preparation.json --native-review $REL/run/native-review.json
job verify 1600 $PIPE $PY verify_release_v2.py $REL/run --output $REL/run/final-binding-check.json
job parts-sheet 900 $PRINT $PY make_parts_sheet.py --incremental $REL/manifest-V1.35.json --out $REL/PARTS-SHEET-V1.35.html
job delivery-folder 1600 $PRINT $PY make_delivery_folder.py $REL --out-root $REL/run/delivery-folder
find $REL/run/delivery-folder -type f | sort
