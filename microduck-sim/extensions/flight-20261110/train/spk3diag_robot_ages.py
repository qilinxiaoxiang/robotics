"""spk3diag: the robot's own sample ages at the policy step, from A7Z wired brain logs (walk_wired.py JSONL rows:
joint_age, imu_age = seconds from the servo read / IMU frame to the brain tick, read_ms = sync read time, loop_ms =
tick time). Policy-mode rows only (stand/walk/seepick with an action). Median, p10, p90 per file and pooled.
  python3 train/spk3diag_robot_ages.py <brain log jsonl>...
"""
import gzip
import json
import sys

import numpy as np

pool = {k: [] for k in ("joint_age", "imu_age", "read_ms", "loop_ms")}
for f in sys.argv[1:]:
    vals = {k: [] for k in pool}
    for ln in (gzip.open(f, "rt") if f.endswith(".gz") else open(f)):
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if r.get("action") is None:
            continue
        for k in pool:
            v = r.get(k)
            if isinstance(v, (int, float)):
                vals[k].append(float(v) * (1000 if k.endswith("age") else 1))
    out = {k: (round(float(np.median(v)), 1), round(float(np.percentile(v, 10)), 1), round(float(np.percentile(v, 90)), 1),
               len(v)) for k, v in vals.items() if v}
    print(f.split("/")[-1], json.dumps(out))
    for k in pool:
        pool[k] += vals[k]
print("POOLED ms (median, p10, p90, n):", json.dumps({k: (round(float(np.median(v)), 1), round(float(np.percentile(v, 10)), 1),
                                                         round(float(np.percentile(v, 90)), 1), len(v)) for k, v in pool.items() if v}))
