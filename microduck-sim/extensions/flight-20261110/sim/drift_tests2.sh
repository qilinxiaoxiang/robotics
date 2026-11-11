#!/bin/zsh
# Take-off drift, second round (hypothesis: the standing trunk pitch tilts the thrust forward and foot friction turns the
# horizontal thrust into a nose-down moment the low-collective differential cannot hold). One knob per test, 3 seeds.
#  mu005        base with floor/foot friction 0.05 (friction moment removed)
#  level_mu005  level ground target with friction 0.05
#  air_level    start hovering at 0.3 m with the trunk level (initial-attitude effect removed)
#  trim0_arm0   stand pose without the -4 deg ankle trim (trunk ~level on the ground), fans armed at t=0
#  trim0_level  as trim0_arm0 with the level ground target
cd "$(dirname $0)/.."
mkdir -p sim/out/drift
run() { local n=$1; shift; $PY sim/flight.py --scenario hover "$@" --out sim/out/drift/$n.json --log sim/out/drift/$n.npz > /dev/null 2>&1; }
for s in 0 1 2; do
  run mu005_s$s --seed $s --floor-mu 0.05 &
  run level_mu005_s$s --seed $s --floor-mu 0.05 --ground-pitch level &
  run air_level_s$s --seed $s --start-air 0.3 --hover-s 10 --air-level &
  run trim0_arm0_s$s --seed $s --trim-ankle 0 --arm-at 0.0 &
  run trim0_level_s$s --seed $s --trim-ankle 0 --arm-at 0.0 --ground-pitch level &
done
wait
$PY - <<'EOF' | tee sim/out/drift/summary2.txt
import glob, json
for f in sorted(glob.glob("sim/out/drift/*.json")):
    r = json.load(open(f))
    print(f.split("/")[-1][:-5], "ok", r["success"], "fell", r["fell_at"], "takeoff_drift", r["takeoff_drift_m"], "takeoff_pitch",
          r["takeoff_pitch_excursion_deg"], "hover_drift", r["hover_drift_m"], "hover_pitch", r["hover_pitch_max_deg"], "tilt", r["max_tilt_deg"],
          "end", r["support_end"]["trunk_pitch_deg"])
EOF
