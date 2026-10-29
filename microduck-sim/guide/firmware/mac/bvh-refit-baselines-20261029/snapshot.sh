#!/bin/zsh
# snapshot.sh: copy the sim code this study runs to the Mac mini under ~/sims/bvh-refit-20261029/rt (repository layout),
# starting from the 2026-10-27 seeing-pick snapshot there (its model files and meshes) and updating the code from this
# MacBook. Prints the md5 of the harnesses it shipped.
set -eu
REPO=/Users/xiangzheng/code/robotics
DST=mac-mini:sims/bvh-refit-20261029/rt
ssh mac-mini 'test -d ~/sims/bvh-refit-20261029/rt || { mkdir -p ~/sims/bvh-refit-20261029 && cp -a ~/sims/seepick-gap-20261027/rt ~/sims/bvh-refit-20261029/rt; }'
EX=(--exclude __pycache__ --exclude .pytest_cache --exclude .ruff_cache --exclude '.profile' --exclude 'robot-runs-*'
    --exclude 'seepick-*' --exclude '*.mp4' --exclude 'shots')
cd $REPO
rsync -a $EX microduck-sim/CURRENT-STATE.json $DST/microduck-sim/
rsync -a --relative $EX microduck-sim/guide/firmware/mac/ microduck-sim/guide/firmware/pi/ \
    microduck-sim/guide/print/a7z-saddle/balance/ microduck-sim/microduck_rl/cmu/model/ \
    microduck-sim/microduck_rl/src/mjlab_microduck/robot/ \
    microduck-sim/hardware-design-20260912/whole-robot-20260912/runtime-overlay/ \
    microduck-sim/hardware-design-20260912/whole-robot-20260912/dynamics/asbuilt-20261015/ \
    pet/__init__.py pet/express/ pet/body/ $DST/
# delay-repair and realgap: their code files, and refresh whatever data files the old snapshot already holds
rsync -a --relative microduck-sim/hardware-design-20260912/whole-robot-20260912/delay-repair-20260912/*.py \
    microduck-sim/hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014/*.py $DST/
rsync -a --existing $EX microduck-sim/hardware-design-20260912/ $DST/microduck-sim/hardware-design-20260912/
ssh mac-mini 'cd ~/sims/bvh-refit-20261029/rt/microduck-sim/guide/firmware/mac && md5 -q brain_sim_check.py walk_brain.py approach_sim.py getup-20261026/getup_sim.py namecall-20261029/namecall_sim.py ../../../hardware-design-20260912/whole-robot-20260912/delay-repair-20260912/evaluate_delay.py; du -sh ~/sims/bvh-refit-20261029'
md5 -q microduck-sim/guide/firmware/mac/brain_sim_check.py microduck-sim/guide/firmware/mac/walk_brain.py \
    microduck-sim/guide/firmware/mac/approach_sim.py microduck-sim/guide/firmware/mac/getup-20261026/getup_sim.py \
    microduck-sim/guide/firmware/mac/namecall-20261029/namecall_sim.py \
    microduck-sim/hardware-design-20260912/whole-robot-20260912/delay-repair-20260912/evaluate_delay.py
