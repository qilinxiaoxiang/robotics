#!/bin/zsh
# First look at the ground behaviours with the pack as dead weight (fans off): brain_sim_check (walk61/stand61) on the
# as-built model, real-condition flags from robot_state_check.py --print-sim-args (--volt 7.6 --drop 0.036).
# --stand-s: seconds of the open-loop stand pose before walk mode (closed loop, stand61 at zero command) takes over.
cd "$(dirname $0)/.."
RL=../../microduck_rl/cmu/mac
mkdir -p sim/out/walkprobe
run() {  # name, manifest variant, flags...
  local n=$1 mv=$2; shift 2
  $PY $RL/brain_sim_check.py --model asbuilt --manifest $PWD/sim/out/manifest_pack_$mv.json --volt 7.6 --drop 0.036 "$@" \
    > sim/out/walkprobe/$n.txt 2>&1
}
for mv in none nominal comx+5 comx+10; do
  for ss in 0 0.3 1.0; do
    run ${mv}_ss${ss}_vx0 $mv --stand-s $ss --walk-at 3 --walk-s 10 --vx 0 &
    run ${mv}_ss${ss}_vx025 $mv --stand-s $ss --walk-at 3 --walk-s 10 --vx 0.25 &
  done
done
wait
$PY - <<'EOF' | tee sim/out/walkprobe/summary.txt
import glob, json
for f in sorted(glob.glob("sim/out/walkprobe/*_ss*.txt")):
    t = open(f).read(); i = t.rfind('{"model"')
    if i < 0:
        print(f, "NO RESULT", t[-300:]); continue
    r = json.loads(t[i:].strip().splitlines()[0])
    print(f.split("/")[-1][:-4], "fell", r["fell_at"], r["fall_dir"], "max_tilt", r["max_tilt"], "first_policy", r["first_policy_tick_s"],
          "dist_x", r["dist_x"], "yaw", r["yaw_walk_deg"])
EOF
