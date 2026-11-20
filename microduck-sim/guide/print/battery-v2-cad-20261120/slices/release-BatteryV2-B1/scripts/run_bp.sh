#!/bin/zsh
# BatteryV2-B1 slices: battery backpack V2 rev B frame and cap on one Orange plate; X1C (Textured PEI, plus a Cool Plate file),
# Elegoo Centauri Carbon and H2S. From extensions/flight-20261110/cad/slices/release-FlightPack-D1/scripts/run_fp.sh and
# guide/print/release-V1.41/scripts/run_v141.sh. Every job runs under the bounded runner (10 minute cap); logs in logs/. The
# slicers (Bambu Studio, the pinned OrcaSlicer 2.4.2 image) exist only on the MacBook, so this runs here with per-job memory
# caps. Not a print-gate release: the assembly guide chapter 12 is not rebuilt for this design yet.
#   zsh scripts/run_bp.sh            (after build_v2.py and checks.py, with build/ and checks/ pulled from the Mac mini)
set -e
REL=${0:A:h:h}; CAD=${REL:h:h}; PRINT=${CAD:h}; SIM=${PRINT:h:h}
PIPE=$SIM/build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009
RUNNER=$SIM/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py
PY=$HOME/.venvs/microduck-cad/bin/python
VER=BatteryV2-B1
export MICRODUCK_CAD_RESERVE_MIB=1024
job() {  # name max-mib cwd command...
  local name=$1 mib=$2 dir=$3; shift 3
  local rc=75 tries=0   # exit 75 = another bounded job holds the lock: wait and retry, up to 20 minutes
  while [ $rc -eq 75 ] && [ $tries -lt 20 ]; do
    (cd $dir && /opt/homebrew/bin/python3 $RUNNER --max-mib $mib --seconds 600 --wait-lock-seconds 60 --report $REL/logs/$name-resource.json -- "$@") > $REL/logs/$name.log 2>&1 && rc=0 || rc=$?; tries=$((tries+1))
  done
  echo "$name exit $rc"; grep -v 'lock holder' $REL/logs/$name.log | tail -3 | cut -c1-300
  [ $rc -eq 0 ]
}
[ -x /Volumes/OrcaSlicer/OrcaSlicer.app/Contents/MacOS/OrcaSlicer ] || \
  hdiutil attach -readonly -nobrowse -mountpoint /Volumes/OrcaSlicer ~/Library/Caches/microduck/OrcaSlicer-2.4.2.dmg
mkdir -p $REL/logs
$PY -c "import shutil,sys,pathlib; [shutil.rmtree(pathlib.Path(sys.argv[1])/d, ignore_errors=True) for d in ('run','review','run-h2s','delivery-h2s','run-x1c-cool','delivery-x1c-cool')]" $REL
$PY $REL/scripts/make_slice_manifest.py > $REL/logs/manifest.log 2>&1; echo "manifest exit $?"; tail -2 $REL/logs/manifest.log
job orientation 1600 $PRINT/orientation-study $PY orientation_check.py $REL/manifest-$VER.json --out $REL/review/orientation.json
job prepare 1600 $REL $PY $PIPE/release_pipeline_v2.py prepare $REL/manifest-$VER.json $REL/run
for M in Bambu Elegoo; do
  job slice-Orange-$M 1600 $REL $PY $PIPE/release_pipeline_v2.py slice $REL/run/preparation.json Orange $M
  job review-Orange-$M 600 $REL $PY scripts/review_bp.py $REL/run Orange $M
  job brim-Orange-$M 600 $PIPE $PY review_brim.py $REL/run Orange $M --output $REL/review/Orange_${M}-brim.json
done
job h2s-Orange 1600 $PRINT $PY make_h2s.py $REL Orange
job x1c-cool-Orange 1600 $REL $PY scripts/make_x1c_coolplate.py $REL Orange
job native-review 600 $REL $PY scripts/make_native_review.py
job package 1600 $REL $PY $PIPE/release_pipeline_v2.py package $REL/run/preparation.json --native-review $REL/run/native-review.json
job verify 1600 $PIPE $PY verify_release_v2.py $REL/run --output $REL/run/final-binding-check.json
job delivery-folder 1200 $PRINT $PY make_delivery_folder.py $REL --out-root $REL/run/delivery-folder
find $REL/run/delivery-folder $REL/delivery-x1c-cool -type f | sort
