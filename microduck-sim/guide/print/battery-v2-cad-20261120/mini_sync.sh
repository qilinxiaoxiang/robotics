#!/bin/zsh
# Mirror the inputs of the battery backpack V2 CAD to the Mac mini (heavy-compute rule: the MacBook swaps) and run a
# command there; outputs come back with `pull`. Edits stay on the MacBook; the mirror (~/code/robotics on the mini) is
# disposable.
#   zsh mini_sync.sh push               copy inputs (rsync, only changed files)
#   zsh mini_sync.sh run '<command>'    run in the mirrored battery-v2-cad-20261120 folder; $PY (flight-cad venv),
#                                       $DYN (microduck-dyn venv) and $RUNNER (bounded CAD runner script) are set
#   zsh mini_sync.sh pull               copy build/, checks/ and the sheet back
set -e
LOCAL=/Users/xiangzheng/code/robotics
REMOTE=code/robotics
SIM=microduck-sim
HERE=$SIM/guide/print/battery-v2-cad-20261120
PIPE=$SIM/build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009
RUNNER_DIR=$SIM/build-pack-20260913/redesign-20260913/head-redesign-20261008
case "$1" in
  push)
    ssh mac-mini "mkdir -p $REMOTE/$HERE $REMOTE/$PIPE $REMOTE/$RUNNER_DIR $REMOTE/$SIM/microduck_rl/cmu/hardware/battery-backpack $REMOTE/$SIM/extensions/flight-20261110/cad/build $REMOTE/$SIM/guide/print/battery-v2-concept-20261119"
    rsync -a --delete $LOCAL/cad-practice/ mac-mini:$REMOTE/cad-practice/
    rsync -a $LOCAL/$PIPE/wall_check.py mac-mini:$REMOTE/$PIPE/
    rsync -a $LOCAL/$RUNNER_DIR/run_bounded_cad.py mac-mini:$REMOTE/$RUNNER_DIR/
    rsync -a $LOCAL/$SIM/guide/print/design_contract.py mac-mini:$REMOTE/$SIM/guide/print/
    rsync -a $LOCAL/$SIM/CURRENT-STATE.json mac-mini:$REMOTE/$SIM/
    rsync -a --delete $LOCAL/$SIM/microduck_rl/cmu/hardware/battery-backpack/ mac-mini:$REMOTE/$SIM/microduck_rl/cmu/hardware/battery-backpack/
    rsync -a --delete $LOCAL/$SIM/microduck_rl/cmu/model/ mac-mini:$REMOTE/$SIM/microduck_rl/cmu/model/
    rsync -a --delete $LOCAL/$SIM/extensions/flight-20261110/cad/build/ mac-mini:$REMOTE/$SIM/extensions/flight-20261110/cad/build/
    rsync -a $LOCAL/$SIM/extensions/flight-20261110/duck_poses.json mac-mini:$REMOTE/$SIM/extensions/flight-20261110/
    rsync -a $LOCAL/$SIM/guide/print/battery-v2-concept-20261119/ mac-mini:$REMOTE/$SIM/guide/print/battery-v2-concept-20261119/
    rsync -a --exclude='build/' --exclude='checks/' --exclude='*.png' $LOCAL/$HERE/ mac-mini:$REMOTE/$HERE/
    ;;
  run)
    ssh mac-mini "cd $REMOTE/$HERE && PY=\$HOME/.venvs/flight-cad/bin/python && DYN=\$HOME/.venvs/microduck-dyn/bin/python && RUNNER=\$HOME/$REMOTE/$RUNNER_DIR/run_bounded_cad.py && export PY DYN RUNNER && $2"
    ;;
  pull)
    mkdir -p $LOCAL/$HERE/build $LOCAL/$HERE/checks
    rsync -a --delete mac-mini:$REMOTE/$HERE/build/ $LOCAL/$HERE/build/
    rsync -a --delete mac-mini:$REMOTE/$HERE/checks/ $LOCAL/$HERE/checks/
    rsync -a mac-mini:$REMOTE/$HERE/'*.png' $LOCAL/$HERE/ 2>/dev/null || true
    rsync -a mac-mini:$REMOTE/$HERE/FITS.json mac-mini:$REMOTE/$HERE/SCREWS.json $LOCAL/$HERE/ 2>/dev/null || true
    ;;
esac
