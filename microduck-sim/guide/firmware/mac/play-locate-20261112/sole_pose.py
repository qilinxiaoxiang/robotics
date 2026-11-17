"""Per-foot sole pose the rigid model gives from the encoder angles and body gravity of a log slice: sole roll (outer
edge down positive), sole yaw (toe out positive) and toe position, so a photo of the feet can be compared foot by foot.
Run on the Mac mini.

  python3 sole_pose.py SLICE.jsonl [--seconds 6] [--mode walk]
"""
import argparse
import json
import math
import os
import statistics as st
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from leglen_vs_load import G, N, SOLE, encoder_roll, m, d  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("slice")
ap.add_argument("--seconds", type=float, default=6.0)
ap.add_argument("--mode", default="walk")
a = ap.parse_args()
rows = [r for r in (json.loads(l) for l in open(a.slice) if l.startswith("{"))
        if r.get("gb") and r.get("q") and r.get("torque") and r.get("mode") == a.mode]
rows = [r for r in rows if r["t"] >= rows[-1]["t"] - a.seconds]
q = dict(zip(N, [st.median(r["q"][i] for r in rows) for i in range(14)]))
gb = [st.median(r["gb"][i] for r in rows) for i in range(3)]
roll = encoder_roll(q, gb)  # pelvis roll that puts both soles on the floor
n = math.hypot(gb[1], gb[2])
g = list(gb)
g[1], g[2] = n * math.sin(math.radians(roll)), -n * math.cos(math.radians(roll))
G.place(q, g)
out = {"pelvis_roll_model": round(roll, 2)}
for b, side in (("ankle_left", 1), ("ankle_right", -1)):
    sid = SOLE[b]
    R = d.geom_xmat[sid].reshape(3, 3)
    mid = m.geom_dataid[sid]
    v = (R @ m.mesh_vert[m.mesh_vertadr[mid]:m.mesh_vertadr[mid] + m.mesh_vertnum[mid]].T).T + d.geom_xpos[sid]
    bottom = v[v[:, 2] < v[:, 2].min() + 0.002]
    # sole plane normal from the lowest vertices
    c = bottom - bottom.mean(0)
    nrm = np.linalg.svd(c)[2][2]
    nrm = nrm if nrm[2] > 0 else -nrm
    sole_roll = math.degrees(math.atan2(nrm[1], nrm[2])) * side  # outer edge down positive
    pa = np.linalg.svd(c)[2][0]  # long axis of the sole
    pa = pa if pa[0] > 0 else -pa
    yaw = math.degrees(math.atan2(pa[1], pa[0])) * side  # toe out positive
    out[b] = dict(sole_roll=round(sole_roll, 2), sole_yaw=round(yaw, 2), toe_x_mm=round(v[:, 0].max() * 1000, 1),
                  centre_y_mm=round(v[:, 1].mean() * 1000, 1))
out["toe_left_minus_right_mm"] = round(out["ankle_left"]["toe_x_mm"] - out["ankle_right"]["toe_x_mm"], 1)
print(json.dumps(out))
