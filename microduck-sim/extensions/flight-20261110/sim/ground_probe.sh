#!/bin/zsh
# Ground transitions (lift-off and touchdown) over ground attitude mode, fan lag, gain, takeoff collective, landing flare and spool-down.
# Each line: case, success, fell_at, nacelle hit, max tilt, takeoff drift and pitch excursion, vz at touchdown, end pitch.
cd "$(dirname $0)/.."
mkdir -p sim/out/ground
run() {  # name, flags...
  local n=$1; shift
  $PY sim/flight.py --scenario "$@" --out sim/out/ground/$n.json --log sim/out/ground/$n.npz > /dev/null 2>&1
}
for sc in hover table_up; do
  for gp in rest level track; do
    run ${sc}_${gp} $sc --ground-pitch $gp &
    run ${sc}_${gp}_twr16 $sc --ground-pitch $gp --takeoff-twr 1.6 --takeoff-ramp 0.1 &
    run ${sc}_${gp}_tau05 $sc --ground-pitch $gp --tau 0.05 --wn 14 &
    run ${sc}_${gp}_tau05_twr16 $sc --ground-pitch $gp --tau 0.05 --wn 14 --takeoff-twr 1.6 --takeoff-ramp 0.1 &
    wait
  done
done
for sc in hover table_down; do
  for fl in 0 0.05 0.10; do
    for sd in 0.15 0.3 0.6; do run ${sc}_land_f${fl}_sd${sd} $sc --flare-h $fl --spool-down $sd & done
  done
  wait
done
$PY - <<'EOF' | tee sim/out/ground/summary.txt
import glob, json
for f in sorted(glob.glob("sim/out/ground/*.json")):
    r = json.load(open(f))
    print(f.split("/")[-1][:-5], "ok", r["success"], "fell", r.get("fell_at"), "nac", r.get("nacelle_hit_at"), "tilt", r.get("max_tilt_deg"),
          "drift", r.get("takeoff_drift_m"), "tpitch", r.get("takeoff_pitch_excursion_deg"), "vz", r.get("landing_vz_mps"),
          "end", r.get("support_end", {}).get("trunk_pitch_deg"), "ph", r.get("phase_end"))
EOF
