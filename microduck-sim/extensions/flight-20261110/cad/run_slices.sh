#!/bin/zsh
# Draft slices of the flight pack (Orange + Black; X1C, Elegoo Centauri Carbon, H2S), every job under the bounded runner
# (10 minute cap), logs in slices/release-FlightPack-D1-DRAFT/logs/. Package runs without a native review, so the release
# stays PREPARED_NATIVE_REVIEW_PENDING (draft pending gate); no delivery folder is made.
#   zsh cad/run_slices.sh          (after build_pack.py; slicers are on the MacBook only)
set -e
CAD=${0:A:h}; REL=$CAD/slices/release-FlightPack-D1-DRAFT; SIM=${CAD:h:h:h}; PRINT=$SIM/guide/print
PIPE=$SIM/build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009
RUNNER=$SIM/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py
PY=/tmp/microduck-cad-venv/bin/python
export MICRODUCK_CAD_RESERVE_MIB=512
job() {  # name max-mib cwd command...
  local name=$1 mib=$2 dir=$3; shift 3
  local rc=75 tries=0
  while [ $rc -eq 75 ] && [ $tries -lt 20 ]; do
    (cd $dir && /opt/homebrew/bin/python3 $RUNNER --max-mib $mib --seconds 600 --wait-lock-seconds 60 --report $REL/logs/$name-resource.json -- "$@") > $REL/logs/$name.log 2>&1 && rc=0 || rc=$?; tries=$((tries+1))
  done
  echo "$name exit $rc"; grep -v 'lock holder' $REL/logs/$name.log | tail -3 | cut -c1-300
  [ $rc -eq 0 ]
}
# The Elegoo slices use the pinned OrcaSlicer 2.4.2 image (pipeline README)
[ -x /Volumes/OrcaSlicer/OrcaSlicer.app/Contents/MacOS/OrcaSlicer ] || \
  hdiutil attach -readonly -nobrowse -mountpoint /Volumes/OrcaSlicer ~/Library/Caches/microduck/OrcaSlicer-2.4.2.dmg
(cd $CAD && $PY make_slice_manifest.py)
mkdir -p $REL/logs
$PY -c "import shutil,sys,pathlib; [shutil.rmtree(pathlib.Path(sys.argv[1])/d, ignore_errors=True) for d in ('run','run-h2s','delivery-h2s')]" $REL
job prepare 1600 $REL $PY $PIPE/release_pipeline_v2.py prepare $REL/manifest-FlightPack-D1-DRAFT.json $REL/run
for C in Orange Black; do for M in Bambu Elegoo; do
  # 1600 MiB: Orca peaked over 1000 MiB on the Black nacelle plate (2026-11-10)
  job slice-$C-$M 1600 $REL $PY $PIPE/release_pipeline_v2.py slice $REL/run/preparation.json $C $M
done; done
for C in Orange Black; do job h2s-$C 1600 $PRINT $PY make_h2s.py $REL $C; done
job package 1600 $REL $PY $PIPE/release_pipeline_v2.py package $REL/run/preparation.json
find $REL/run/delivery $REL/delivery-h2s -type f | sort
