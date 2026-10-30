"""Can the legs tell the floor from the air while the hold keeps them soft (s 0, kp 80)? Per leg joint, the deflection
(present - goal, servo ticks, 0.088 deg each) and the summed leg current, in windows marked by hand from lift_check.py
output: in the air, and set down with the hand still on the head. Also the body gyro magnitude.

  python3 air_vs_floor.py <log.jsonl> air:<t0>-<t1> floor:<t0>-<t1> ...
"""
import json
import math
import statistics
import sys

sys.path.insert(0, __file__.rsplit("/", 2)[0])
from walk_brain import IDS, NAMES  # noqa: E402

LEGS = [k for k, n in enumerate(NAMES) if n.split("_", 1)[-1] in ("hip_yaw", "hip_roll", "hip_pitch", "knee", "ankle")]

path, wins = sys.argv[1], []
for a in sys.argv[2:]:
    name, rng = a.split(":")
    t0, t1 = rng.split("-")
    wins.append((name, float(t0), float(t1)))
rows = {w: [] for w in wins}
for line in open(path):
    try:
        r = json.loads(line)
    except ValueError:
        continue
    t = r.get("t", 0)
    for w in wins:
        if w[1] <= t <= w[2] and r.get("pos_tick") and r.get("goal_tick"):
            rows[w].append(r)
for w, rs in rows.items():
    if not rs:
        print(w[0], "no rows")
        continue
    print(f"== {w[0]} {w[1]:.1f}-{w[2]:.1f} ({len(rs)} ticks), kp_leg {sorted({(r.get('hold') or {}).get('kp_leg') for r in rs})}")
    for k in LEGS:
        d = [r["pos_tick"][k] - r["goal_tick"][str(IDS[k])] for r in rs]
        print(f"  {NAMES[k]:16s} deflection mean {statistics.mean(d):+7.1f} sd {statistics.pstdev(d):5.1f} ticks")
    ma = [r["legs_ma"] for r in rs if r.get("legs_ma") is not None]
    gy = [math.sqrt(sum(v * v for v in r["gyro_body"])) for r in rs if r.get("gyro_body")]
    print(f"  legs_ma mean {statistics.mean(ma):.0f} range {min(ma):.0f}-{max(ma):.0f}; gyro |w| mean {statistics.mean(gy):.2f}")
