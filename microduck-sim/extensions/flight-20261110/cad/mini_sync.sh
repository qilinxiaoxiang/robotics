#!/bin/zsh
# Mirror the inputs of the flight-pack CAD checks to the Mac mini (heavy-compute rule: the MacBook swaps) and run a
# command there; outputs come back with mini_sync.sh pull. Edits stay on the MacBook; the mirror is disposable.
#   zsh cad/mini_sync.sh push                 copy inputs (rsync, only changed files)
#   zsh cad/mini_sync.sh run '<command>'      run in the mirrored flight-20261110 folder with the mini venv as $PY
#   zsh cad/mini_sync.sh pull                 copy cad/build and the check outputs back
set -e
LOCAL=/Users/xiangzheng/code/robotics
REMOTE=code/flight-cad-mirror/robotics
SIM=microduck-sim
FL=$SIM/extensions/flight-20261110
case "$1" in
  push)
    ssh mac-mini "mkdir -p $REMOTE/$SIM/microduck_rl/cmu $REMOTE/$SIM/microduck_rl/src/mjlab_microduck/robot/microduck $REMOTE/$SIM/guide/print/back-plate $REMOTE/$SIM/guide/firmware/mac/camera-calib-20261030 $REMOTE/$SIM/extensions"
    rsync -a --delete $LOCAL/cad-practice/ mac-mini:$REMOTE/cad-practice/
    rsync -a --delete $LOCAL/$SIM/microduck_rl/cmu/model/ mac-mini:$REMOTE/$SIM/microduck_rl/cmu/model/
    rsync -a --delete $LOCAL/$SIM/microduck_rl/src/mjlab_microduck/robot/microduck/assets/ mac-mini:$REMOTE/$SIM/microduck_rl/src/mjlab_microduck/robot/microduck/assets/
    rsync -a --prune-empty-dirs --include='*/' --include='rows_matched.json' --include='bend_ticks.json' --exclude='*' \
      $LOCAL/$SIM/guide/firmware/mac/camera-calib-20261030/bend-20261030/ mac-mini:$REMOTE/$SIM/guide/firmware/mac/camera-calib-20261030/bend-20261030/
    rsync -a --delete $LOCAL/$SIM/guide/print/world/ mac-mini:$REMOTE/$SIM/guide/print/world/
    rsync -a $LOCAL/$SIM/guide/print/design_contract.py mac-mini:$REMOTE/$SIM/guide/print/
    rsync -a --exclude='*.html' --exclude='duck_mesh.json' --exclude='duck_poses.json' --exclude='cad/build/' --exclude='cad/slices/' \
      $LOCAL/$FL/ mac-mini:$REMOTE/$FL/
    ;;
  run)
    ssh mac-mini "cd $REMOTE/$FL && PY=\$HOME/.venvs/flight-cad/bin/python && export PY && $2"
    ;;
  pull)
    rsync -a --delete mac-mini:$REMOTE/$FL/cad/build/ $LOCAL/$FL/cad/build/
    rsync -a mac-mini:$REMOTE/$FL/cad/FITS.json $LOCAL/$FL/cad/FITS.json
    rsync -a --include='*.txt' --include='*.json' --exclude='*' mac-mini:$REMOTE/$FL/cad/checks/ $LOCAL/$FL/cad/checks/ 2>/dev/null || true
    ;;
esac
