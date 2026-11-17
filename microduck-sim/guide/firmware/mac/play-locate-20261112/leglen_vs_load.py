"""Is the missing left-right leg height fixed geometry or load-dependent deformation?

For every zero-command balance and stand episode in the run ledger: the settled median joint angles and body
gravity, the pelvis roll at which the rigid model with those encoder angles puts both soles on the floor (as
~/sims/leglen.py), the residual IMU roll minus that roll, and the left share of knee current as a load proxy.
Fixed geometry (zero, sole or part height) gives a residual independent of load; elastic deformation gives a
residual that grows with the left leg's load. Run on the Mac mini in ~/duck-walks; read-only.

  python3 leglen_vs_load.py OUT.json
"""
import gzip
import json
import math
import os
import statistics as st
import sys

import numpy as np

MAC = os.path.expanduser("~/code/robotics/microduck-sim/guide/firmware/mac")
sys.path.insert(0, MAC)
LEDGER = os.getcwd()
os.chdir(MAC)
import target_ground as tg  # noqa: E402

N = ["right_ankle", "right_knee", "right_hip_pitch", "right_hip_roll", "right_hip_yaw", "left_ankle", "left_knee",
     "left_hip_pitch", "left_hip_roll", "left_hip_yaw", "head_pitch", "neck_pitch", "head_yaw", "head_roll"]
G = tg.DuckGeometry()
m, d = G.m, G.d
SOLE = {}
for b in ("ankle_left", "ankle_right"):
    SOLE[b] = [x for x in range(m.ngeom) if m.geom_bodyid[x] == m.body(b).id and m.geom_group[x] == 3][0]


def soles(q, g):
    G.place(q, g)
    r = []
    for b in ("ankle_left", "ankle_right"):
        sid = SOLE[b]
        mid = m.geom_dataid[sid]
        va, na = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
        r.append(((d.geom_xmat[sid].reshape(3, 3) @ m.mesh_vert[va:va + na].T).T + d.geom_xpos[sid])[:, 2].min() * 1000)
    return r


def encoder_roll(q, gb):
    n = math.hypot(gb[1], gb[2])

    def diff(r):
        g = list(gb)
        g[1], g[2] = n * math.sin(math.radians(r)), -n * math.cos(math.radians(r))
        L, R = soles(q, g)
        return L - R

    lo, hi = -6.0, 8.0
    flo = diff(lo)
    for _ in range(30):
        mid = (lo + hi) / 2
        fm = diff(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2


eps = [json.loads(l) for l in open(os.path.join(LEDGER, "episodes.jsonl"))]
out = []
for e in eps:
    if e["kind"] not in ("balance", "stand") or e["dur_s"] < 3 or e["outcome"] not in ("ok", None):
        continue
    if "145302" in e["log"]:  # roll trim -3 in that log
        continue
    rows = []
    try:
        with gzip.open(os.path.join(LEDGER, e["trajectory"]), "rt") as f:
            for line in f:
                r = json.loads(line)
                if r.get("gb") and r.get("q") and r.get("torque") and r.get("cur_ma"):
                    rows.append(r)
    except OSError:
        continue
    if len(rows) < 50:
        continue
    rows = rows[len(rows) // 3:]
    q = dict(zip(N, [st.median(r["q"][i] for r in rows) for i in range(14)]))
    gb = [st.median(r["gb"][i] for r in rows) for i in range(3)]
    imu = math.degrees(math.atan2(gb[1], -gb[2]))
    enc = encoder_roll(q, gb)
    kl = st.median(abs(r["cur_ma"][6]) for r in rows)
    kr = st.median(abs(r["cur_ma"][1]) for r in rows)
    share = kl / (kl + kr) if kl + kr > 0 else None
    out.append(dict(log=e["log"], when=e["when"], kind=e["kind"], imu_roll=round(imu, 2), encoder_roll=round(enc, 2),
                    residual=round(imu - enc, 2), knee_ma_l=kl, knee_ma_r=kr, left_share=share))
    print(e["when"], e["kind"][:4], "imu %+.2f enc %+.2f resid %+.2f kneeL %s kneeR %s" % (imu, enc, imu - enc, kl, kr),
          flush=True)
json.dump(out, open(sys.argv[1], "w"), indent=0)
