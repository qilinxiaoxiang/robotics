"""Does the left lean grow with walking time? Per brain log, every zero-command balance (walk mode) and stand episode
in time order: median IMU roll, hip roll readings and left/right knee current, against cumulative walk+turn seconds
before it. Run in ~/duck-walks on the Mac mini. Read-only."""
import gzip
import json
import math
import statistics as st
import sys
from collections import defaultdict

eps = [json.loads(l) for l in open("episodes.jsonl")]
by_log = defaultdict(list)
for e in eps:
    by_log[e["log"]].append(e)

R_HROLL, L_HROLL, R_KNEE, L_KNEE = 3, 8, 1, 6
out = []
for log, es in sorted(by_log.items()):
    es.sort(key=lambda e: e["t_start"])
    walked = 0.0
    for e in es:
        if e["kind"] in ("walk", "turn"):
            walked += e["dur_s"]
            continue
        if e["kind"] not in ("balance", "stand") or e["dur_s"] < 3 or e["outcome"] not in ("ok", None):
            continue
        rows = []
        try:
            with gzip.open(e["trajectory"], "rt") as f:
                for line in f:
                    r = json.loads(line)
                    if r.get("gb") and r.get("q") and r.get("torque"):
                        rows.append(r)
        except OSError:
            continue
        if len(rows) < 50:
            continue
        rows = rows[len(rows) // 3:]  # settled part
        roll = st.median(math.degrees(math.atan2(-r["gb"][1], -r["gb"][2])) for r in rows)
        hr = st.median(math.degrees(r["q"][R_HROLL]) for r in rows)
        hl = st.median(math.degrees(r["q"][L_HROLL]) for r in rows)
        cur = [r.get("cur_ma") for r in rows if r.get("cur_ma")]
        kr = st.median(abs(c[R_KNEE]) for c in cur) if cur else None
        kl = st.median(abs(c[L_KNEE]) for c in cur) if cur else None
        out.append(dict(log=log, day=e["day"], when=e["when"], kind=e["kind"], kp=e["kp"], walked_s=round(walked, 1),
                        roll=round(roll, 2), hip_roll_r=round(hr, 2), hip_roll_l=round(hl, 2), knee_ma_r=kr, knee_ma_l=kl))

json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "/tmp/lean_drift.json", "w"), indent=0)
for o in out:
    print(o["when"], o["log"][15:35], o["kind"][:4], "walked", o["walked_s"], "roll", o["roll"], "hipR", o["hip_roll_r"],
          "hipL", o["hip_roll_l"], "kneeR", o["knee_ma_r"], "kneeL", o["knee_ma_l"])
