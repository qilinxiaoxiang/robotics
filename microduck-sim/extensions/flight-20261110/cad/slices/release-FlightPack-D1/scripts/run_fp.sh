#!/bin/zsh
# FlightPack-D1 print release (geometry c31e5e2d): Orange (wing plate, trays L/R, FC bracket, 100 % infill) and Black (four
# nacelle clamp halves); X1C (Textured PEI), Elegoo Centauri Carbon and H2S. From guide/print/release-V1.41/scripts/run_v141.sh.
# Every job runs under the bounded runner (10 minute cap); logs in logs/. The slicers (Bambu Studio, the pinned OrcaSlicer 2.4.2
# image) exist only on the MacBook, so this runs here with per-job memory caps.
#   zsh scripts/run_fp.sh            (after cad/build_pack.py)
set -e
REL=${0:A:h:h}; CAD=${REL:h:h}; SIM=${CAD:h:h:h}; PRINT=$SIM/guide/print
PIPE=$SIM/build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009
RUNNER=$SIM/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py
PY=/tmp/microduck-cad-venv/bin/python
VER=FlightPack-D1
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
# release gate first: STATUS.json (scripts/gate_status.py) must say RELEASED or RELEASED_WITH_EXCEPTION (Shawn's
# A-GATE-BPHATCH, cad/checks/accepted.json) for exactly the printed STLs that will be sliced (cad/build = guide/print/world)
$PY $REL/scripts/check_gate_for_slicing.py || { echo "slicing refused: gate status does not cover the current geometry"; exit 1; }
[ -x /Volumes/OrcaSlicer/OrcaSlicer.app/Contents/MacOS/OrcaSlicer ] || \
  hdiutil attach -readonly -nobrowse -mountpoint /Volumes/OrcaSlicer ~/Library/Caches/microduck/OrcaSlicer-2.4.2.dmg
mkdir -p $REL/logs
$PY -c "import shutil,sys,pathlib; [shutil.rmtree(pathlib.Path(sys.argv[1])/d, ignore_errors=True) for d in ('run','review','run-h2s','delivery-h2s')]" $REL
(cd $CAD && $PY make_slice_manifest.py) > $REL/logs/manifest.log 2>&1; echo "manifest exit $?"
job orientation 1600 $PRINT/orientation-study $PY orientation_check.py $REL/manifest-$VER.json --out $REL/review/orientation.json
job prepare 1600 $REL $PY $PIPE/release_pipeline_v2.py prepare $REL/manifest-$VER.json $REL/run
for C in Orange Black; do for M in Bambu Elegoo; do
  # 2400 MiB: Orca reached 1721 MiB on the thick-collar Black nacelle plate (2026-11-10, stopped at 1600)
  job slice-$C-$M 2400 $REL $PY $PIPE/release_pipeline_v2.py slice $REL/run/preparation.json $C $M
  job review-$C-$M 600 $REL $PY scripts/review_fp.py $REL/run $C $M
  job brim-$C-$M 600 $PIPE $PY review_brim.py $REL/run $C $M --output $REL/review/${C}_${M}-brim.json
done; done
for C in Orange Black; do job h2s-$C 1600 $PRINT $PY make_h2s.py $REL $C; done
job native-review 600 $REL $PY scripts/make_native_review.py
job package 1600 $REL $PY $PIPE/release_pipeline_v2.py package $REL/run/preparation.json --native-review $REL/run/native-review.json
job verify 1600 $PIPE $PY verify_release_v2.py $REL/run --output $REL/run/final-binding-check.json
job delivery-folder 1200 $PRINT $PY make_delivery_folder.py $REL --out-root $REL/run/delivery-folder
job delivery-downloads 1200 $PRINT $PY make_delivery_folder.py $REL    # ~/Downloads/zhengxia_MicroDuck_FlightPack-D1
(cd $CAD && $PY collect_grams.py) > $REL/logs/grams.log 2>&1; echo "grams exit $?"; tail -3 $REL/logs/grams.log
find ~/Downloads/zhengxia_MicroDuck_$VER -type f | sort
