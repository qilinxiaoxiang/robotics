#!/bin/zsh
# Take-off forward drift: one knob per test, 3 seeds each.
#  base       current take-off (servo-held legs, spool to 40 % with attitude loop, ramp to 1.3 x weight)
#  rigid      legs locked at the held pose (no servo compliance), otherwise base
#  air        start hovering at 0.3 m, zero velocity, no ground phase, hold 10 s
#  air_rigid  air with locked legs
#  slow       attitude loop on from zero throttle, slow ramp to 95 % of weight over 3 s, then 1.15 x over 0.5 s
#  level      attitude target level (0) while on the ground
cd "$(dirname $0)/.."
mkdir -p sim/out/drift
run() { local n=$1; shift; $PY sim/flight.py --scenario hover "$@" --out sim/out/drift/$n.json --log sim/out/drift/$n.npz > /dev/null 2>&1; }
for s in 0 1 2; do
  run base_s$s --seed $s &
  run rigid_s$s --seed $s --rigid-legs &
  run air_s$s --seed $s --start-air 0.3 --hover-s 10 &
  run air_rigid_s$s --seed $s --start-air 0.3 --hover-s 10 --rigid-legs &
  run slow_s$s --seed $s --spool-s 3.0 --spool-frac 0.95 --takeoff-twr 1.15 --takeoff-ramp 0.5 &
  run level_s$s --seed $s --ground-pitch level &
  run slow_rigid_s$s --seed $s --spool-s 3.0 --spool-frac 0.95 --takeoff-twr 1.15 --takeoff-ramp 0.5 --rigid-legs &
done
wait
$PY sim/authority.py > /dev/null
$PY - <<'EOF' | tee sim/out/drift/summary.txt
import glob, json
for f in sorted(glob.glob("sim/out/drift/*.json")):
    r = json.load(open(f))
    print(f.split("/")[-1][:-5], "ok", r["success"], "fell", r["fell_at"], "takeoff_drift", r["takeoff_drift_m"], "takeoff_pitch",
          r["takeoff_pitch_excursion_deg"], "hover_drift", r["hover_drift_m"], "hover_pitch", r["hover_pitch_max_deg"], "tilt", r["max_tilt_deg"])
EOF
