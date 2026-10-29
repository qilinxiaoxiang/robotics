"""approach_sim.py's 11 suite placements under the robot drift (0.015 N m forward, trim -1.1079), one variant per call,
five in parallel; appends one row per variant to results/bisect_approach.jsonl.

  ~/.venvs/microduck-dyn/bin/python bisect_approach.py LABEL [--root RT] [--neck V]
    --root  repository root of the snapshot to run (default: this one); a copy with older files swapped in bisects
    --neck  open-loop stand neck_pitch through stand_neck_run.py (D-030 0.25, NEUTRAL 0.35)
"""
import argparse
import concurrent.futures as cf
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
SUITE = (((0.6, 0.0), None), ((0.86, -0.31), None), ((0.5, -0.2), None), ((0.55, 0.2), None), ((0.8, 0.35), None),
         ((0.8, 0.0), (3.0, 0.0, -0.2)), ((0.7, -0.15), (3.0, 0.0, 0.3)),
         ((0.35, -0.55), None), ((0.25, 0.45), None), ((0.45, 0.0), (5.0, 0.0, 0.15)), ((-0.2, -0.4), None))
ap = argparse.ArgumentParser()
ap.add_argument("label")
ap.add_argument("--root", default=os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "..")))
ap.add_argument("--neck", type=float, default=None)
a = ap.parse_args()
mac = os.path.join(a.root, "microduck-sim", "guide", "firmware", "mac")


def one(case):
    obj, move = case
    cmd = [os.path.join(mac, "approach_sim.py"), "--obj", str(obj[0]), str(obj[1])] + \
          (["--move"] + [str(v) for v in move] if move else []) + ["--drift", "0.015", "--trim", "-1.1079", "--drift-when", "forward"]
    if a.neck is not None:
        cmd = [os.path.join(HERE, "stand_neck_run.py"), str(a.neck)] + cmd
    # through bvh_run.py (BVH_REFIT=0: report only) for its Mac mini path fix of asbuilt.config.json's MacBook manifest path
    p = subprocess.run([PY, os.path.join(HERE, "bvh_run.py")] + cmd, capture_output=True, text=True, cwd=mac,
                       env=dict(os.environ, BVH_REFIT="0"))
    line = [ln for ln in p.stdout.splitlines() if ln.startswith("{")]
    if not line:
        return dict(obj=obj, error=p.stderr[-400:])
    r = json.loads(line[-1])
    return {k: r.get(k) for k in ("obj", "ok", "why", "true_r", "true_bearing_deg", "fell_at", "max_tilt", "path_m")}


with cf.ThreadPoolExecutor(5) as ex:
    rows = list(ex.map(one, SUITE))
row = dict(label=a.label, root=a.root, neck=a.neck, passed=sum(bool(r.get("ok")) for r in rows), of=len(rows), runs=rows)
with open(os.path.join(HERE, "results", "bisect_approach.jsonl"), "a") as f:
    f.write(json.dumps(row) + "\n")
print(a.label, f"{row['passed']}/{row['of']}", [(r["obj"], r.get("ok"), r.get("error", "")[-80:]) for r in rows if not r.get("ok")])
