#!/bin/zsh
# Funnel concept sims on the Mac mini (the MacBook swaps). Edits stay here; the mini mirror is disposable.
#   zsh mini_sync.sh push | zsh mini_sync.sh run '<cmd>' | zsh mini_sync.sh bg <name> '<cmd>' | zsh mini_sync.sh pull
set -e
LOCAL=/Users/xiangzheng/code/robotics/microduck-sim
REMOTE=code/robotics/microduck-sim
HERE=guide/print/battery-dock-20261120/funnel-concept
BV2=guide/print/battery-v2-cad-20261120/build
case "$1" in
  push)
    ssh mac-mini "mkdir -p $REMOTE/$HERE/checks $REMOTE/$BV2/parts"
    rsync -a $LOCAL/$BV2/battery_v2_frame-world.stl $LOCAL/$BV2/battery_v2_cap-world.stl mac-mini:$REMOTE/$BV2/
    rsync -a $LOCAL/$BV2/parts/contact_pad_plus-world.stl $LOCAL/$BV2/parts/contact_pad_minus-world.stl mac-mini:$REMOTE/$BV2/parts/
    rsync -a --exclude='checks/' --exclude='*.png' $LOCAL/$HERE/ mac-mini:$REMOTE/$HERE/
    ;;
  run)
    ssh mac-mini "cd $REMOTE/$HERE && DYN=\$HOME/.venvs/microduck-dyn/bin/python && export DYN && $2"
    ;;
  bg)
    ssh mac-mini "cd $REMOTE/$HERE && DYN=\$HOME/.venvs/microduck-dyn/bin/python && export DYN && nohup zsh -c '$3' > checks/$2.log 2>&1 < /dev/null & echo started"
    ;;
  pull)
    rsync -a mac-mini:$REMOTE/$HERE/checks/ $LOCAL/$HERE/checks/
    ;;
esac
