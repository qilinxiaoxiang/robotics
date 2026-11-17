"""Which way a + step of a joint moves the robot in the rigid model at a log slice's stance: sole centre sideways
(hip roll), head tilt and heading (head roll and yaw). Sets the sign of trial zero shifts. Run on the Mac mini.
  python3 joint_direction.py SLICE.jsonl
"""
import json
import math
import statistics as st
import sys

import numpy as np

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from leglen_vs_load import G, N, m, d  # noqa: E402

rows = [r for r in (json.loads(l) for l in open(sys.argv[1]) if l.startswith("{")) if r.get("q") and r.get("gb")]
rows = rows[-200:]
q = dict(zip(N, [st.median(r["q"][i] for r in rows) for i in range(14)]))
g = [0.0, 0.0, -1.0]


def snap(qq):
    G.place(qq, g)
    out = {}
    for b in ("ankle_left", "ankle_right"):
        out[b] = d.xpos[m.body(b).id].copy()
    hb = m.body("jaw_soft").id
    R = d.xmat[hb].reshape(3, 3)
    out["head_R"] = R.copy()
    return out


base = snap(q)
for j in ("left_hip_roll", "right_hip_roll", "head_roll", "head_yaw"):
    qq = dict(q)
    qq[j] += math.radians(2)
    s = snap(qq)
    if "hip" in j:
        side = "ankle_left" if j.startswith("left") else "ankle_right"
        dy = (s[side][1] - base[side][1]) * 1000
        outward = dy > 0 if side == "ankle_left" else dy < 0
        print(f"{j} +2 deg: {side} y {dy:+.2f} mm -> {'outward' if outward else 'inward'}")
    else:
        dR = s["head_R"] @ base["head_R"].T  # world-frame rotation of the head
        w = np.array([dR[2, 1] - dR[1, 2], dR[0, 2] - dR[2, 0], dR[1, 0] - dR[0, 1]]) / 2
        print(f"{j} +2 deg: head turns about world x {math.degrees(w[0]):+.2f} (roll, + = right side up, left ear "
              f"down), y {math.degrees(w[1]):+.2f}, z {math.degrees(w[2]):+.2f} (yaw, + = to the robot's left)")
