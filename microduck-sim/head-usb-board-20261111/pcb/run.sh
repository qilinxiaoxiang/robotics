#!/bin/sh
# Build the head USB board on the Mac mini (KiCad and Freerouting live there) and bring the results back.
# Usage: sh run.sh place | route [passes] | drc | all
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
REMOTE=code/robotics/microduck-sim/head-usb-board-20261111
STAGE=${1:-place}
PASSES=${2:-30}
rsync -a --exclude build "$HERE/" "mac-mini:$REMOTE/pcb/"
rsync -a --exclude build "$HERE/../sch/" "mac-mini:$REMOTE/sch/"
ssh mac-mini "sh -s" <<EOF
set -e
K=\$HOME/Applications/KiCad/KiCad.app/Contents
PY=\$K/Frameworks/Python.framework/Versions/3.9/bin/python3.9
CLI=\$K/MacOS/kicad-cli
cd \$HOME/$REMOTE/pcb
mkdir -p build
case "$STAGE" in
  place|all) \$PY gen_pcb.py place ;;
esac
case "$STAGE" in
  route|all)
    rm -f build/board.ses
    # the jar on a current Java: the native freerouting-cli 2.5.0 dies on boards with component outlines
    # (UnsupportedFeatureError ComponentOutline) and then hangs; the Perl alarm bounds a hung run to 8 minutes
    perl -e 'alarm 480; exec @ARGV' /opt/homebrew/opt/openjdk/bin/java -Djava.awt.headless=true -jar \$HOME/code/robotics/pcb-tools/freerouting-2.5.0.jar -de build/board.dsn -do build/board.ses -mp $PASSES > build/route.log 2>&1 || true
    grep -v "^[[:space:]]*at " build/route.log | tail -4
    test -s build/board.ses || { echo "router wrote no session file"; exit 1; }
    \$PY gen_pcb.py finish ;;
esac
\$CLI pcb drc --severity-error --format json -o build/drc.json build/board.kicad_pcb > build/drc.log 2>&1 || true
tail -2 build/drc.log
\$CLI pcb export svg --layers F.Cu,B.Cu,Edge.Cuts,F.Courtyard,F.SilkS --mode-single --page-size-mode 2 --exclude-drawing-sheet -o build/board.svg build/board.kicad_pcb > /dev/null 2>&1 || echo "svg export failed"
EOF
mkdir -p "$HERE/build"
rsync -a "mac-mini:$REMOTE/pcb/build/" "$HERE/build/"
