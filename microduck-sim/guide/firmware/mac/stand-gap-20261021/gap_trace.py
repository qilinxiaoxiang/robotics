"""Per-row gap between the robot's IMU pitch and the as-built model's flat-foot trunk pitch at the same measured joint
angles (tonight's A7Z logs). Constant gap while stand61 balances = IMU offset; a gap that grows in open-loop stand
while the joints hold = the robot rotating onto its toes. Sim kinematics only."""
import json, math, os, sys, gzip
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "stand-pose-study-20261020"))
import stand_sim as S
import mujoco, numpy as np
bsc, wb = S.bsc, S.wb
m, d, c, names, bam = S._load(400, S.REAL_VOLT, None, 0.0, False)
trunk = m.body("trunk_base").id
def kin_pitch(q):
    Rt = bsc.feet_flat_rot(m, d, names, q)
    R = Rt  # trunk orientation that puts both soles flat
    return math.degrees(math.atan2(-R[2, 0], R[2, 2]))
def rpitch(g): return math.degrees(math.atan2(g[0], -g[2]))
OUT, STEP, LOGS = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
res = []
for fn in LOGS:
    rows = [json.loads(l) for l in (gzip.open(fn, "rt") if fn.endswith(".gz") else open(fn))]
    t00 = rows[0]["t"]
    for i, r in enumerate(rows[::STEP]):
        if not r["torque"] or r["q"][0] is None or abs(r["gb"][1]) > 0.15 or abs(rpitch(r["gb"])) > 40:
            continue
        q = dict(zip(wb.NAMES, r["q"]))
        kp = kin_pitch(q)
        c_ = r.get("cmd") or {}
        mode = r["mode"] + ("0" if r["mode"] == "walk" and not any(float(c_.get(k, 0) or 0) for k in ("vx", "vy", "vtheta")) else "")
        res.append((os.path.basename(fn).replace("duck_wired_log_", "").split(".")[0], round(r["t"] - t00, 2), mode, round(rpitch(r["gb"]), 2), round(kp, 2)))
json.dump(res, open(os.path.join(HERE, OUT), "w"))
import statistics as st
for mode in ("walk0", "stand", "walk", "sit"):
    g = [a - b for _, _, mo, a, b in res if mo == mode]
    if g: print(mode, len(g), "rows gap mean %.2f median %.2f sd %.2f p10 %.2f p90 %.2f" % (st.mean(g), st.median(g), st.pstdev(g), sorted(g)[len(g)//10], sorted(g)[9*len(g)//10]))
