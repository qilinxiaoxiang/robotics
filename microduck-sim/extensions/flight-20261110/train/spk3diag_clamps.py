"""spk3 heavy-load diagnosis: per runtime pickup record (train/eval/pk*_ball.json), episodes by fall, with the policy
goals the runtime Brain clamped to walk_brain.JOINT_RANGE (goal_clamped_ticks, goal_clamp_peak_rad) and the lateral
summary. Read-only.
  python3 train/spk3diag_clamps.py train/eval/pk_spk3_600_load050_ball.json ...
"""
import json
import sys
from collections import Counter

for f in sys.argv[1:]:
    d = json.load(open(f))
    eps = d["episodes"]
    n_f = sum(e["fell_at"] is not None for e in eps)
    rows = []
    agg = {True: Counter(), False: Counter()}
    nep = {True: 0, False: 0}
    for e in eps:
        ev = (e["probe"].get("seepick") or {}).get("events") or {}
        gc = ev.get("goal_clamped_ticks") or {}
        pk = ev.get("goal_clamp_peak_rad") or {}
        fell = e["fell_at"] is not None
        nep[fell] += 1
        for k, v in gc.items():
            agg[fell][k] += v
        hr = {k: (gc.get(k, 0), pk.get(k, 0.0)) for k in ("left_hip_roll", "right_hip_roll", "left_ankle", "right_ankle")}
        rows.append((e["seed"], e["fell_at"], e["fall_dir"], hr))
    print(f"== {f}: falls {n_f}/{len(eps)}")
    for fell in (True, False):
        if nep[fell]:
            print(f"  {'fell' if fell else 'stood'} ({nep[fell]} eps) clamped ticks per ep:",
                  {k: round(v / nep[fell], 1) for k, v in sorted(agg[fell].items())})
    for r in rows:
        print("   seed", r[0], "fell", r[1], r[2], {k: v for k, v in r[3].items() if v[0]})
