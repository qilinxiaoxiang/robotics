"""Read one quiet stand from a slice of brain log rows: IMU roll, the pelvis roll the rigid model with the encoder
angles needs for both soles on the floor, their difference (the left-right leg height gap the encoders do not see),
hip roll readings and knee currents. Run on the Mac mini; the slice is copied off the A7Z with tail, never parsed there.

  python3 stand_read.py SLICE.jsonl [--seconds 5]
"""
import argparse
import json
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from leglen_vs_load import N, encoder_roll  # noqa: E402  (loads the duck geometry once)

ap = argparse.ArgumentParser()
ap.add_argument("slice")
ap.add_argument("--seconds", type=float, default=5.0)
ap.add_argument("--mode", default="stand", help="brain mode of the rows to read (stand, or walk for zero command)")
a = ap.parse_args()
rows = []
for line in open(a.slice):
    try:
        r = json.loads(line)
    except ValueError:
        continue
    if r.get("gb") and r.get("q") and r.get("torque") and r.get("mode") == a.mode:
        rows.append(r)
if not rows:
    sys.exit("no stand rows with torque in the slice")
t_end = rows[-1]["t"]
rows = [r for r in rows if r["t"] >= t_end - a.seconds]
q = dict(zip(N, [st.median(r["q"][i] for r in rows) for i in range(14)]))
gb = [st.median(r["gb"][i] for r in rows) for i in range(3)]
imu = math.degrees(math.atan2(gb[1], -gb[2]))
enc = encoder_roll(q, gb)
spread = max(math.degrees(math.atan2(r["gb"][1], -r["gb"][2])) for r in rows) - \
    min(math.degrees(math.atan2(r["gb"][1], -r["gb"][2])) for r in rows)
cur = [r["cur_ma"] for r in rows if r.get("cur_ma")]
out = dict(rows=len(rows), imu_roll=round(imu, 2), imu_roll_spread=round(spread, 2), encoder_roll=round(enc, 2),
           residual=round(imu - enc, 2), hip_roll_r=round(math.degrees(q["right_hip_roll"]), 2),
           hip_roll_l=round(math.degrees(q["left_hip_roll"]), 2),
           knee_ma_r=st.median(abs(c[1]) for c in cur) if cur else None,
           knee_ma_l=st.median(abs(c[6]) for c in cur) if cur else None)
print(json.dumps(out))
