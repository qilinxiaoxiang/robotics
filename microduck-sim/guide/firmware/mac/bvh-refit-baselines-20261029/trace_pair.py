"""Trace one get-up run without and with the refit and merge the harness trace (trunk gravity z, height, phase, action)
with bvh_hook's 20 ms samples (lowest point of each moved body relative to the floor, bodies touching the floor).

  ~/.venvs/microduck-dyn/bin/python trace_pair.py side 7 [extra getup_sim args]   # results/traces/side_7.json
"""
import json
import math
import os
import pathlib
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
pose, seed = sys.argv[1], int(sys.argv[2])
cmd = [os.path.join(MAC, "getup-20261026", "getup_sim.py"), "--start", pose, "--getup", "recover", "--seed", str(seed),
       "--hard-max-action", "99", "--trace"] + sys.argv[3:]
if pose == "sitting":
    cmd += ["--settle-kp", "200"]
if pose == "push":
    cmd += ["--push-dir", f"{2 * math.pi * seed / 10:.4f}", "--run-s", "10"]
out_dir = pathlib.Path(HERE) / "results" / "traces"
out_dir.mkdir(parents=True, exist_ok=True)
merged = {}
for refit in (0, 1):
    tr = out_dir / f"tmp_{pose}_{seed}_{refit}.jsonl"
    env = dict(os.environ, BVH_REFIT=str(refit), BVH_TRACE=str(tr))
    p = subprocess.run([PY, os.path.join(HERE, "bvh_run.py")] + cmd, capture_output=True, text=True, cwd=os.path.dirname(cmd[0]), env=env)
    res = json.loads(p.stdout.strip().splitlines()[-1])
    hook = {s["t"]: s for s in (json.loads(ln) for ln in tr.read_text().splitlines())}
    tr.unlink()
    rows = []
    for r in res.pop("trace"):
        h = hook.get(round(r["t"] - 0.0, 3)) or hook.get(round(r["t"] + 0.0025, 3)) or {}
        low = h.get("low_mm", {})
        rows.append(dict(r, head_low_mm=low.get("jaw_soft"), trunk_low_mm=low.get("trunk_base"),
                         hip_low_mm=[low.get("hip_l"), low.get("hip_l_2")], touch=h.get("touch")))
    merged[refit] = dict(result={k: res[k] for k in ("success", "up_after_s", "fell_after_up", "max_action", "phases", "sat_s")},
                         trace=rows)
json.dump(dict(cmd=" ".join(os.path.relpath(c, MAC) if c.startswith("/") else c for c in cmd), runs=merged),
          open(out_dir / f"{pose}_{seed}.json", "w"))
print(json.dumps({k: v["result"] for k, v in merged.items()}))
