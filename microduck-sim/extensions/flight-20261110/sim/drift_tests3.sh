#!/bin/zsh
# Take-off drift, third round. Finding of round 2: the mixer assumes the COM of mass_report.json (x -11.9 mm) while the
# loaded model's COM is at x -10.6 mm (sim/diag_com.py); with a 36 mm pitch arm the 1.3 mm error is a nose-down hover
# moment the attitude integrator must find, and it is frozen on the ground. One knob: the mixer's COM = the true COM.
cd "$(dirname $0)/.."
mkdir -p sim/out/drift
run() { local n=$1; shift; $PY sim/flight.py --scenario hover "$@" --out sim/out/drift/$n.json --log sim/out/drift/$n.npz > /dev/null 2>&1; }
for s in 0 1 2; do
  run air_level_true_s$s --seed $s --start-air 0.3 --hover-s 10 --air-level --com-est true &
  run air_true_s$s --seed $s --start-air 0.3 --hover-s 10 --com-est true &
  run base_true_s$s --seed $s --com-est true &
  run level_true_s$s --seed $s --com-est true --ground-pitch level &
  run rigid_level_true_s$s --seed $s --com-est true --ground-pitch level --rigid-legs &
  run level_true_twr16_s$s --seed $s --com-est true --ground-pitch level --takeoff-twr 1.6 --takeoff-ramp 0.1 &
done
wait
$PY - <<'EOF' | tee sim/out/drift/summary3.txt
import glob, json
for f in sorted(glob.glob("sim/out/drift/*true*.json")):
    r = json.load(open(f))
    print(f.split("/")[-1][:-5], "ok", r["success"], "fell", r["fell_at"], "takeoff_drift", r["takeoff_drift_m"], "takeoff_pitch",
          r["takeoff_pitch_excursion_deg"], "hover_drift", r["hover_drift_m"], "hover_pitch", r["hover_pitch_max_deg"], "tilt", r["max_tilt_deg"])
EOF
