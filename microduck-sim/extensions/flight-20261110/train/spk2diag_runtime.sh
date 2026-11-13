#!/bin/zsh
# spk2 lateral-miss diagnosis, runtime side: the pickup test of pickup_ckpt.sh (12 mm ball, 20 dev seeds, no pack, Mac mini)
# with ONE runtime-sim setting changed per run, to find the one that moves the spk2 trunk 2 cm right.
#   zsh train/spk2diag_runtime.sh MODELS TAG "EXTRA FLAGS" [TAG "EXTRA FLAGS" ...]
# -> train/eval/pkd_<MODELS>_<TAG>_ball.json (read with train/spk2diag_eval_table.py)
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
R=$1; shift
SP="--stand-s 0 --walk-at 1 --walk-s 0 --wired-guards --sp-at 4 --sp-cone elliptic --sp-impratio 10 --sp-shape ball --sp-size 0.012"
zsh $T/mini.sh push > /dev/null
while [ $# -ge 2 ]; do
  TG=$1; EX=$2; shift 2
  X="$SP $EX"
  [ "$EX" = "noguards" ] && X="${SP/--wired-guards /}"
  echo "== $R $TG: $X $(date +%H:%M:%S)"
  timeout 540 zsh $T/mini.sh run "\$PY train/style_eval.py --name pkd_${R}_${TG}_ball --models train/ckpt/$R --manifest train/manifests/flightpack-none.json --case stand --episodes 20 --workers 8 --extra='$X' --out train/eval/pkd_${R}_${TG}_ball.json" > /dev/null 2>&1
  zsh $T/mini.sh pull > /dev/null
  python3 $T/spk2diag_eval_table.py $T/eval/pkd_${R}_${TG}_ball.json 2>&1 | head -1 | cut -c1-400
done
echo "ALL DONE $(date +%H:%M:%S)"
