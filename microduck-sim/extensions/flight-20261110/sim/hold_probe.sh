#!/bin/zsh
# Held leg pose (servos at KP 400, fans off), with and without the pack, over hip-pitch and ankle trims (mirrored, deg):
# does it stay up 12 s, which way does it fall (pitch + = nose down / forward), and the COM margin to heel and toe.
cd "$(dirname $0)/.."
mkdir -p sim/out/hold
run() {  # name, flags...
  local n=$1; shift
  $PY sim/flight.py --scenario hover --arm-at 50 "$@" --log sim/out/hold/$n.npz --out sim/out/hold/$n.json > /dev/null 2>&1
}
for mv in none nominal; do
  for th in -8 -4 0 4 8 12; do
    for ta in -12 -8 -6 -4 -2 0 4 8; do run ${mv}_h${th}_a${ta} --mass-variant $mv --trim-hip $th --trim-ankle $ta & done
    wait
  done
done
$PY - <<'EOF' > sim/out/hold/summary.txt
import glob, json, numpy as np
for f in sorted(glob.glob("sim/out/hold/*_h*_a*.json")):
    r = json.load(open(f)); L = np.load(f[:-5] + ".npz")["log"]
    print(f.split("/")[-1][:-5], "fell_at", r["fell_at"], "final pitch", round(float(np.degrees(L[-1, 5])), 1), "support", r["support_end"])
EOF
grep "fell_at None" sim/out/hold/summary.txt
