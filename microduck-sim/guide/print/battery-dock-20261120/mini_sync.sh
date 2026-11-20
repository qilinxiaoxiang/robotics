#!/bin/zsh
# Mirror the dock CAD inputs to the Mac mini (heavy-compute rule: the MacBook swaps), run there, pull build/ back.
#   zsh mini_sync.sh push | zsh mini_sync.sh run '$PY build_dock.py' | zsh mini_sync.sh pull
set -e
LOCAL=/Users/xiangzheng/code/robotics
REMOTE=code/robotics
SIM=microduck-sim
HERE=$SIM/guide/print/battery-dock-20261120
BV2=$SIM/guide/print/battery-v2-cad-20261120
PIPE=$SIM/build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009
case "$1" in
  push)
    ssh mac-mini "mkdir -p $REMOTE/$HERE $REMOTE/$BV2/build/parts $REMOTE/$PIPE $REMOTE/cad-practice"
    rsync -a $LOCAL/cad-practice/ mac-mini:$REMOTE/cad-practice/
    rsync -a $LOCAL/$PIPE/wall_check.py mac-mini:$REMOTE/$PIPE/
    rsync -a $LOCAL/$BV2/build/battery_v2_frame-world.stl $LOCAL/$BV2/build/battery_v2_cap-world.stl mac-mini:$REMOTE/$BV2/build/
    rsync -a $LOCAL/$BV2/build/parts/contact_pad_plus-world.stl $LOCAL/$BV2/build/parts/contact_pad_minus-world.stl mac-mini:$REMOTE/$BV2/build/parts/
    rsync -a --exclude='build/' --exclude='slices/' $LOCAL/$HERE/ mac-mini:$REMOTE/$HERE/
    ;;
  run)
    ssh mac-mini "cd $REMOTE/$HERE && PY=\$HOME/.venvs/flight-cad/bin/python && export PY && $2"
    ;;
  pull)
    mkdir -p $LOCAL/$HERE/build
    rsync -a --delete mac-mini:$REMOTE/$HERE/build/ $LOCAL/$HERE/build/
    rsync -a mac-mini:$REMOTE/$HERE/FITS.json $LOCAL/$HERE/
    ;;
esac
