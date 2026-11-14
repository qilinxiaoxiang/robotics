#!/bin/zsh
# spk3diag training-env probes in small Modal calls (2-3 probes, about 70-90 s each), so each call has ended before the
# two-minute modal_watch check; modal_watch runs before and after every call, and the loop stops on a non-clean watch.
#   zsh train/spk3diag_modal_batches.sh "LABEL1,LABEL2" "LABEL3,LABEL4" ...
G=/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl-grasp
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
M=/Users/xiangzheng/code/robotics/omx-local/.venv/bin/modal
i=0
for B in "$@"; do
  i=$((i + 1))
  python3 ~/code/claude-config/scripts/modal_watch.py > /dev/null || { echo "watch not clean before batch $i"; python3 ~/code/claude-config/scripts/modal_watch.py; exit 1; }
  echo "== batch $i: $B $(date +%H:%M:%S)"
  (cd $G && SPK3_DIAG=${SPK3_DIAG_PREFIX:-f}$i SPK3_DIAG_ONLY=$B timeout 600 $M run cmu/grasp/spk3diag_modal.py::probe < /dev/null > $T/logs/spk3diag_${SPK3_DIAG_PREFIX:-f}${i}_local.log 2>&1)
  grep -E "^\[diag\]|^spk3diag: probe|^exit|Error" $T/logs/spk3diag_${SPK3_DIAG_PREFIX:-f}${i}_local.log | cut -c1-260
  python3 ~/code/claude-config/scripts/modal_watch.py | tail -1
done
echo "BATCHES DONE $(date +%H:%M:%S)"
