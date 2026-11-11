#!/bin/zsh
# Walk-slot comparison: for each STAND_RUN:ITER+WALK_RUN:ITER pair, build the models dir (probe_ckpt.py, 2 episodes),
# write the suite's moving cases (walk, turnL, turnR, mass, COM, shove, landing, no pack), run them on Modal CPU and
# print falls / speed / p99 / saturation.   zsh train/walk_suite.sh <label> fs1:2950+fw1:3000 fs1:2950+fw2:3000
set -e
cd /Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110
label=$1; shift
python3 ~/code/claude-config/scripts/modal_watch.py > /dev/null || echo "modal_watch: attention (see its output)"
python3 train/probe_ckpt.py "$@" --cases stand --episodes 2 | grep probe_
python3 - "$label" "$@" <<'EOF'
import json, subprocess, sys
label, pairs = sys.argv[1], sys.argv[2:]
ev = []
for p in pairs:
    tag = p.replace(":", "_").replace("+", "__")
    pre = f"{label}_{tag}"
    subprocess.run(["python3", "train/make_suite.py", pre, f"ckpt/{tag}"], check=True, capture_output=True)
    ev += [e for e in json.load(open(f"train/specs/suite_{pre}.json"))["evals"] if e["case"] != "stand"]
open(f"train/specs/walk_{label}.json", "w").write(json.dumps(dict(evals=ev)))
print(len(ev), "evals")
EOF
/Users/xiangzheng/code/robotics/omx-local/.venv/bin/modal run train/flight_eval_modal.py --spec train/specs/walk_$label.json > train/logs/eval_walk_$label.log 2>&1
grep '^{' train/logs/eval_walk_$label.log | python3 -c "
import sys, json
for l in sys.stdin:
    s = json.loads(l)
    print(s['name'], s['falls'], '/', s['episodes'], s['fall_times'][:3], s['speed_median_upright'], s['leg_force_p99_nm_upright_median'], s['leg_force_sat_frac_upright_max'])"
