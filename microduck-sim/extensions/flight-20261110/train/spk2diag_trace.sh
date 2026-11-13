#!/bin/zsh
# spk2 diagnosis: per-tick runtime traces (--sp-trace) of the pickup test (12 mm ball, no pack, Mac mini), one episode
# per seed, for several policies on the same seeds, to compare head, neck and jaw actions in the close window.
#   zsh train/spk2diag_trace.sh "MODEL1 MODEL2" "0 2 3 5 7"
# -> train/eval/pkt_trace_<MODEL>_s<SEED>.jsonl (read with train/spk2diag_trace_cmp.py)
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
SP="--stand-s 0 --walk-at 1 --walk-s 0 --wired-guards --sp-at 4 --sp-cone elliptic --sp-impratio 10 --sp-shape ball --sp-size 0.012"
zsh $T/mini.sh push > /dev/null
for R in ${=1}; do
  for K in ${=2}; do
    echo "== $R seed $K $(date +%H:%M:%S)"
    timeout 300 zsh $T/mini.sh run "\$PY train/style_eval.py --name pkt_${R}_s${K} --models train/ckpt/$R --manifest train/manifests/flightpack-none.json --case stand --episodes 1 --workers 1 --seed0 $K --extra='$SP --sp-trace train/eval/pkt_trace_${R}_s${K}.jsonl' --out train/eval/pkt_${R}_s${K}_ball.json" > /dev/null 2>&1
  done
done
zsh $T/mini.sh pull > /dev/null
ls -la $T/eval/ | grep pkt_trace_
echo "ALL DONE $(date +%H:%M:%S)"
