"""Print tick-log rows of one brain_sim_check run in a time window: mode, sit phase, knees, tilt, pitch rate, the
largest |action|. Mac mini.

  python show_ticks.py TICKS.jsonl T0 T1 [EVERY]
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
from walk_brain import NAMES  # noqa: E402

LK, RK = NAMES.index("left_knee"), NAMES.index("right_knee")
t0, t1 = float(sys.argv[2]), float(sys.argv[3])
every = int(sys.argv[4]) if len(sys.argv) > 4 else 1
rows = [json.loads(l) for l in open(sys.argv[1])]
rows = [r for r in rows if t0 <= r["t"] <= t1][::every]
for r in rows:
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, -r["gb"][2]))))
    act = max(abs(a) for a in r["action"]) if r.get("action") else None
    print(f"{r['t']:6.2f} {r['mode']:5s} {str(r.get('sit_phase', '-')):6s} {r.get('policy', '-'):9s} "
          f"knees {r['q'][LK]:+.2f}/{r['q'][RK]:+.2f} tilt {tilt:5.1f} gb {r['gb'][0]:+.2f} gy {r['gyro_body'][1]:+5.2f} "
          f"amax {act if act is None else round(act, 2)}")
