#!/bin/zsh
# Pickup test of one staged checkpoint dir (train/ckpt/<name>: seepick61.onnx, stand61.onnx, walk61.onnx) in the
# runtime sim: 12 mm ball, 20 dev seeds, one job per load on the Mac mini. Prints held / still held 3 s later / falls.
# Usage: zsh pickup_ckpt.sh <name> <load>...     loads: none load025 load050 load075 nobatt load100
#        PK_SD0=1 zsh pickup_ckpt.sh ...   same test at the short loop delay (--sensor-delay 0, about 24 ms instead of
#        44 ms from sample to applied goal); results go to eval/pk_<name>sd0_<load>_ball.json
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
M=$1; shift
R=$M
SP="--stand-s 0 --walk-at 1 --walk-s 0 --wired-guards --sp-at 4 --sp-cone elliptic --sp-impratio 10 --sp-shape ball --sp-size 0.012"
if [ -n "$PK_SD0" ]; then SP="$SP --sensor-delay 0"; R=${M}sd0; fi
zsh $T/mini.sh push > /dev/null
for ld in "$@"; do
  echo "== $R $ld $(date +%H:%M:%S)"
  timeout 540 zsh $T/mini.sh run "\$PY train/style_eval.py --name pk_${R}_${ld}_ball --models train/ckpt/$M --manifest train/manifests/flightpack-$ld.json --case stand --episodes 20 --workers 8 --extra='$SP' --out train/eval/pk_${R}_${ld}_ball.json" > /dev/null 2>&1
done
zsh $T/mini.sh pull > /dev/null
cd $T && python3 - "$R" "$@" <<'EOF'
import json, collections, sys
R = sys.argv[1]
for ld in sys.argv[2:]:
    try:
        d = json.load(open(f"eval/pk_{R}_{ld}_ball.json"))
    except Exception as e:
        print(R, ld, "missing", e); continue
    eps = [v for v in d.values() if isinstance(v, list) and v and isinstance(v[0], dict)][0]
    sp = [e["probe"].get("seepick") or {} for e in eps]
    ev = [s.get("events") or {} for s in sp]
    print(R, ld, "held", sum(bool((s.get("at_handback") or {}).get("held")) for s in sp), "at_end",
          sum(bool((s.get("at_end") or {}).get("held")) for s in sp), "of", len(eps),
          "pinched", sum(e.get("first_pinched_t") is not None for e in ev),
          "falls", sum(e["fell_at"] is not None for e in eps), dict(collections.Counter(e["fall_dir"] for e in eps)))
EOF
echo "ALL DONE"
