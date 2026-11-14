#!/bin/zsh
# spk3 heavy-load fall diagnosis, runtime side: the pickup test of pickup_ckpt.sh (12 mm ball, 20 dev seeds, Mac mini)
# for one checkpoint and load, with ONE runtime-sim setting changed per run.
#   zsh train/spk3diag_runtime.sh CKPT LOAD TAG "EXTRA FLAGS" [TAG "EXTRA FLAGS" ...]
# EXTRA "noguards" drops --wired-guards; an EXTRA starting with "JR=" sets SPK3DIAG_JOINT_RANGE (flight_eval.py: the
# joint range the runtime Brain clamps policy goals to) to the JSON after "JR=" and adds no flag.
# -> train/eval/pkd3_<CKPT>_<LOAD>_<TAG>_ball.json (summary: train/spk3diag_clamps.py, train/spk3diag_table.py)
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
R=$1; LD=$2; shift 2
SP="--stand-s 0 --walk-at 1 --walk-s 0 --wired-guards --sp-at 4 --sp-cone elliptic --sp-impratio 10 --sp-shape ball --sp-size 0.012"
zsh $T/mini.sh push > /dev/null
while [ $# -ge 2 ]; do
  TG=$1; EX=$2; shift 2
  X="$SP $EX"; ENVP=""
  [ "$EX" = "noguards" ] && X="${SP/--wired-guards /}"
  if [[ "$EX" == JR=* ]]; then X="$SP"; ENVP="SPK3DIAG_JOINT_RANGE='${EX#JR=}'"; fi
  echo "== $R $LD $TG: $ENVP $X $(date +%H:%M:%S)"
  timeout 540 zsh $T/mini.sh run "$ENVP \$PY train/style_eval.py --name pkd3_${R}_${LD}_${TG}_ball --models train/ckpt/$R --manifest train/manifests/flightpack-$LD.json --case stand --episodes 20 --workers 8 --extra='$X' --out train/eval/pkd3_${R}_${LD}_${TG}_ball.json" < /dev/null > /dev/null 2>&1
  zsh $T/mini.sh pull > /dev/null
  python3 $T/spk3diag_table.py $T/eval/pkd3_${R}_${LD}_${TG}_ball.json 2>&1 | head -3
done
echo "ALL DONE $(date +%H:%M:%S)"
