"""Third check, no scan and no camera: servo position error is a load gauge. Predict the neck and head gravity torque from the model at
each logged frame and read which hidden offset and which contact fit the real position error."""
import json, math, os, sys, datetime as dt
import numpy as np
sys.argv = [sys.argv[0]] + sys.argv[1:]
S = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sim_static as ss
import mujoco
from duck_kin import trunk_rotation
m, d, c, names, bam = ss.load()
base = dt.datetime(2026, 11, 1, 20, 0, 0).timestamp()
ID = ss.ID_NAMES
rows = []
for k, l in enumerate(open(S + "/brain_slice.jsonl")):
    if k % 12:
        continue
    try:
        r = json.loads(l)
    except Exception:
        continue
    if not r.get("goal_tick") or r["mode"] == "monitor":
        continue
    rows.append(r)
idx = {n: names.index(n) for n in names}
ji = np.array([m.actuator(n).trnid[0] for n in names]); va = m.jnt_dofadr[ji]
def bias(r, dn=0.0, trunk=0.0):
    q = dict(zip(ID, r["q"])); q["neck_pitch"] += math.radians(dn)
    g = np.array(r["gb"], float); a = math.radians(trunk)
    g = np.array([g[0]*math.cos(a) - g[2]*math.sin(a), g[1], g[0]*math.sin(a) + g[2]*math.cos(a)])
    R = trunk_rotation(g); quat = np.zeros(4); mujoco.mju_mat2Quat(quat, R.ravel())
    ss.setup(m, d, names, q, quat)
    return d.qfrc_bias[va[idx["neck_pitch"]]], d.qfrc_bias[va[idx["head_pitch"]]]
T = np.array([r["t"] for r in rows])
errN = np.array([(r["pos_tick"][11] - r["goal_tick"]["12"]) * ss.TICK for r in rows])
errH = np.array([(r["pos_tick"][10] - r["goal_tick"]["11"]) * ss.TICK for r in rows])
neck = np.array([r["q"][11] for r in rows]); head = np.array([r["q"][10] for r in rows]); dq = np.array([np.abs(r["dq"]).max() for r in rows])
# the servo's own stiffness from the sim's BAM: torque per rad at kp 200 (sim_static settled table: position error against hold torque)
print("frames", len(rows), "still frames", int((dq < 0.1).sum()))
# 3 still groups, plus the descent and the rise frame by frame
def win(a, b):
    return (T >= base + a) & (T < base + b)
GROUPS = dict(stand1=win(38*60, 39*60+40), bend=win(40*60+30, 41*60+50), stand2=win(43*60, 46*60))
for label, kw in (("chain", {}), ("neck -10.4", dict(dn=-10.41)), ("trunk +4", dict(trunk=4.0)), ("trunk +4 neck -5", dict(trunk=4.0, dn=-5.0))):
    print("\ncase", label)
    for g, mask in GROUPS.items():
        i = np.where(mask)[0][::10]
        b = np.array([bias(rows[k], **kw) for k in i])
        print(f"  {g:7s} neck {neck[i].mean():+.3f} head {head[i].mean():+.3f} | neck hold {b[:,0].mean():+.3f} Nm err {errN[i].mean():+.3f} rad -> K {abs(b[:,0].mean()/errN[i].mean()):.2f} | head hold {b[:,1].mean():+.3f} Nm err {errH[i].mean():+.3f} rad -> K {abs(b[:,1].mean()/errH[i].mean()):.2f} Nm/rad")
print("\nservo K in the sim (bam kp 200): probing")
# the descent: does the neck load collapse when the head reaches the floor?
t0 = base + 39*60 + 58
mask = (T > t0) & (T < t0 + 14)
print("descent t  neck head trunk | neck hold Nm err rad K | head hold err K")
for k in np.where(mask)[0][::3]:
    b = bias(rows[k])
    print(f"{T[k]-t0:5.2f} {neck[k]:+.3f} {head[k]:+.3f} {math.degrees(math.asin(rows[k]['gb'][0])):+5.1f} | {b[0]:+.3f} {errN[k]:+.3f} {abs(b[0]/errN[k]) if abs(errN[k])>1e-3 else 0:5.2f} | {b[1]:+.3f} {errH[k]:+.3f} {abs(b[1]/errH[k]) if abs(errH[k])>1e-3 else 0:5.2f}  dqmax {dq[k]:.2f} mode {rows[k]['mode']}")
