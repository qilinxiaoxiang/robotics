"""Frontal-plane (roll) angle of every leg body's axes in the rigid model at a log slice's stance, to compare with
edge angles measured on a front photo: the segment where photo and model part is where the unseen tilt sits.
Run on the Mac mini.  python3 segment_roll.py SLICE.jsonl
"""
import json
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from leglen_vs_load import G, N, encoder_roll, m, d  # noqa: E402

rows = [r for r in (json.loads(l) for l in open(sys.argv[1]) if l.startswith("{"))
        if r.get("gb") and r.get("q") and r.get("torque") and r.get("mode") == "walk"]
rows = [r for r in rows if r["t"] >= rows[-1]["t"] - 6]
q = dict(zip(N, [st.median(r["q"][i] for r in rows) for i in range(14)]))
gb = [st.median(r["gb"][i] for r in rows) for i in range(3)]
roll = encoder_roll(q, gb)
n = math.hypot(gb[1], gb[2])
g = list(gb)
g[1], g[2] = n * math.sin(math.radians(roll)), -n * math.cos(math.radians(roll))
G.place(q, g)
for b in range(m.nbody):
    name = m.body(b).name
    if not name or "head" in name or "neck" in name:
        continue
    R = d.xmat[b].reshape(3, 3)
    # angle of each body axis projected on the world y-z plane, measured from world vertical (deg)
    ang = [round(math.degrees(math.atan2(R[1, k], R[2, k])), 1) for k in range(3)]
    print(f"{name:28s} pos_y {d.xpos[b][1]*1000:+6.1f} z {d.xpos[b][2]*1000:6.1f}  axis-from-vertical x,y,z {ang}")
