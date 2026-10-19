#!/bin/zsh
# V1.22 release run, every job under the bounded runner (10 minute cap), logs in logs/.
#   zsh scripts/run_v122.sh            from guide/print/release-V1.22
set -e
REL=${0:A:h:h}; PRINT=$REL:h; SIM=$PRINT:h:h
PIPE=$SIM/build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009
RUNNER=$SIM/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py
PY=/tmp/microduck-cad-venv/bin/python
# The runner gates on max-mib plus its reserve against the kernel's available memory, which on 2026-10-19 evening sat at
# 2.1-2.9 GiB, so each job gets a budget near its measured peak (V1.21 and V1.22 resource reports: slice 180-830 MiB,
# prepare 755, review and brim review under 180, package 450, verify 480, parts sheet and delivery 650-740) with a
# 1024 MiB reserve instead of the 3000 + 2048 default.
export MICRODUCK_CAD_RESERVE_MIB=1024
job() {  # name max-mib cwd command...
  local name=$1 mib=$2 dir=$3; shift 3
  (cd $dir && /opt/homebrew/bin/python3 $RUNNER --max-mib $mib --seconds 600 --report $REL/logs/$name-resource.json -- "$@") > $REL/logs/$name.log 2>&1
  echo "$name exit $?"; grep -v 'lock holder' $REL/logs/$name.log | tail -3 | cut -c1-300
}
mkdir -p $REL/logs; rm -rf $REL/run $REL/review
$PY $REL/scripts/make_manifest.py > $REL/logs/manifest.log 2>&1; echo "manifest exit $?"
job step1 1000 $REL $PY $PIPE/release_pipeline_v2.py prepare $REL/manifest-V1.22.json $REL/run
$PY - $REL/run/preparation.json <<'EOF'
import json, sys
p = json.load(open(sys.argv[1]))
print('plate centre offsets', [(r['color'], r['machine'], r.get('plateCentreOffsetMm')) for r in p['rows']])
EOF
for C in Orange Black Yellow; do for M in Bambu Elegoo; do
  job slice-$C-$M 1000 $REL $PY $PIPE/release_pipeline_v2.py slice $REL/run/preparation.json $C $M
  job review-$C-$M 400 $REL $PY scripts/review_v122.py $REL/run $C $M
  job brim-$C-$M 400 $PIPE $PY review_brim.py $REL/run $C $M --output $REL/review/${C}_${M}-brim.json
done; done
job native-review 600 $REL $PY scripts/make_native_review.py
job package 700 $REL $PY $PIPE/release_pipeline_v2.py package $REL/run/preparation.json --native-review $REL/run/native-review.json
job verify 700 $PIPE $PY verify_release_v2.py $REL/run --output $REL/run/final-binding-check.json
job parts-sheet 900 $PRINT $PY make_parts_sheet.py --incremental $REL/manifest-V1.22.json --out $REL/PARTS-SHEET-V1.22.html
job delivery-folder 900 $PRINT $PY make_delivery_folder.py $REL --out-root $REL/run/delivery-folder
find $REL/run/delivery-folder -type f | sort
