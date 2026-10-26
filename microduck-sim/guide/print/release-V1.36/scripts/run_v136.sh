#!/bin/zsh
# V1.36 release run (the lower head shell with the speaker pocket and holes 4.5 mm forward and no amplifier rails, Yellow), every job under the bounded runner (10 minute cap), logs in logs/
#   zsh scripts/run_v136.sh            from guide/print/release-V1.36
set -e
REL=${0:A:h:h}; PRINT=$REL:h; SIM=$PRINT:h:h
PIPE=$SIM/build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009
RUNNER=$SIM/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py
PY=/tmp/microduck-cad-venv/bin/python
# Budgets as in run_v130.sh (measured peaks: slice 180-830 MiB, prepare 755, reviews under 180, package 450, verify 480, parts sheet and delivery 650-740).
export MICRODUCK_CAD_RESERVE_MIB=1024
job() {  # name max-mib cwd command...
  local name=$1 mib=$2 dir=$3; shift 3
  local rc=75 tries=0   # exit 75 = another bounded job holds the lock (a gate run): wait and retry, up to 20 minutes
  while [ $rc -eq 75 ] && [ $tries -lt 20 ]; do
    (cd $dir && /opt/homebrew/bin/python3 $RUNNER --max-mib $mib --seconds 600 --wait-lock-seconds 60 --report $REL/logs/$name-resource.json -- "$@") > $REL/logs/$name.log 2>&1; rc=$?; tries=$((tries+1))
  done
  echo "$name exit $rc"; grep -v 'lock holder' $REL/logs/$name.log | tail -3 | cut -c1-300
  [ $rc -eq 0 ]
}
mkdir -p $REL/logs; rm -rf $REL/run $REL/review
$PY $REL/scripts/make_manifest.py > $REL/logs/manifest.log 2>&1; echo "manifest exit $?"; tail -3 $REL/logs/manifest.log
job step1 1600 $REL $PY $PIPE/release_pipeline_v2.py prepare $REL/manifest-V1.36.json $REL/run
$PY - $REL/run/preparation.json <<'PYEOF'
import json, sys
p = json.load(open(sys.argv[1]))
print('plate centre offsets', [(r['color'], r['machine'], r.get('plateCentreOffsetMm')) for r in p['rows']])
PYEOF
for C in Yellow; do for M in Bambu Elegoo; do
  job slice-$C-$M 1000 $REL $PY $PIPE/release_pipeline_v2.py slice $REL/run/preparation.json $C $M
  job review-$C-$M 400 $REL $PY scripts/review_v136.py $REL/run $C $M
  job brim-$C-$M 400 $PIPE $PY review_brim.py $REL/run $C $M --output $REL/review/${C}_${M}-brim.json
  job support-map-$C-$M 1024 $REL $PY $PRINT/orientation-study/scripts/support_map.py $REL/run $C $M $REL/review/${C}_${M}-support-map.png $REL/review/${C}_${M}-support-map.json
  job readback-$C-$M 1024 $REL $PY $PRINT/orientation-study/scripts/slice_readback.py $REL/run $C $M $REL/review/${C}_${M}-readback.json
done; done
job native-review 600 $REL $PY scripts/make_native_review.py
job package 1600 $REL $PY $PIPE/release_pipeline_v2.py package $REL/run/preparation.json --native-review $REL/run/native-review.json
job verify 1600 $PIPE $PY verify_release_v2.py $REL/run --output $REL/run/final-binding-check.json
job parts-sheet 900 $PRINT $PY make_parts_sheet.py --incremental $REL/manifest-V1.36.json --out $REL/PARTS-SHEET-V1.36.html
job delivery-folder 900 $PRINT $PY make_delivery_folder.py $REL --out-root $REL/run/delivery-folder
find $REL/run/delivery-folder -type f | sort
