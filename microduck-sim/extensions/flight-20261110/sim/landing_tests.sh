#!/bin/zsh
# Ground phase after landing, held legs (servos at KP 400), take-off fix flags of sim/batch.py.
#  (c) fans keep a fraction of the weight with the attitude loop on for settle_s after the land detector, then ramp down
#  (d) crouch poses: which mirrored hip/knee/ankle trims stand with the pack, fans off (hold probe), then land in them
cd "$(dirname $0)/.."
mkdir -p sim/out/landing sim/out/crouch
FIX=(--com-est true --ground-pitch level --takeoff-twr 1.6 --takeoff-ramp 0.1)
run() { local d=$1 n=$2; shift 2; $PY sim/flight.py "$@" --out sim/out/$d/$n.json > /dev/null 2>&1; }
# (d) crouch hold probe, fans never armed
for kn in -30 -15 15 30; do
  for hp in -10 0 10; do
    for an in -12 -8 -4 0 4 8; do run crouch k${kn}_h${hp}_a${an} --scenario hover --arm-at 50 --trim-knee $kn --trim-hip $hp --trim-ankle $an & done
    wait
  done
done
# (c) settle with partial thrust, 2 seeds, hover and table_down
for sc in hover table_down; do
  for fr in 0.3 0.5; do
    for st in 2 4; do
      for sd in 1 3; do
        for s in 0 1; do run landing ${sc}_f${fr}_st${st}_sd${sd}_s$s --scenario $sc $FIX --spool-down-frac $fr --settle-s $st --spool-down $sd --flare-h 0 --seed $s & done
      done
    done
    wait
  done
done
$PY - <<'EOF' | tee sim/out/landing/summary.txt
import glob, json
for d in ("crouch", "landing"):
    for f in sorted(glob.glob(f"sim/out/{d}/*.json")):
        r = json.load(open(f))
        if d == "crouch" and r["fell_at"] is not None:
            continue
        print(d, f.split("/")[-1][:-5], "ok", r["success"], "air", r.get("airborne_success"), "fell", r["fell_at"], "tilt_end", r["tilt_end_deg"],
              "support", r["support_end"], "mAh", r["mah_used"])
EOF
