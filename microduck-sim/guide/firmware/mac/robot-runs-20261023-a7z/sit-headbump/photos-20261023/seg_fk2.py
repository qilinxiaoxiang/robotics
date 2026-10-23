import json, sys, math, numpy as np, mujoco
exec(open(sys.argv[1]).read().split("def summarize")[0].replace("import json, math, sys, statistics as st", "import json, math, statistics as st"))
from static_gap import setup
for j in range(m.njnt): print("joint", m.joint(j).name, "-> body", m.body(m.jnt_bodyid[j]).name, "axis", np.round(m.jnt_axis[j], 2))
rows = [json.loads(l) for l in open(sys.argv[2]) if l.startswith("{")]
T0 = 1792793490
def mats(q):
    pose = dict(zip(wb.NAMES, q)); R = feet_flat_rot(m, d, names, pose)
    setup(m, d, names, pose); mujoco.mju_mat2Quat(d.qpos[3:7], R.flatten()); mujoco.mj_kinematics(m, d)
    return {m.body(i).name: d.xmat[i].reshape(3, 3).copy() for i in range(1, m.nbody)}
res = {}
for tag, tp in (("closed", 30), ("open", 59)):
    w = [r for r in rows if abs(r["t"] - T0 - tp) < 1.5]
    res[tag] = mats(list(np.median(np.array([r["q"] for r in w]), axis=0)))
for b in res["closed"]:
    dR = res["open"][b] @ res["closed"][b].T
    q = np.zeros(4); mujoco.mju_mat2Quat(q, dR.flatten())
    v = np.zeros(3); mujoco.mju_quat2Vel(v, q, 1.0)
    print(f"{b:20s} world rotation open vs closed (deg) about x {math.degrees(v[0]):+5.2f} y {math.degrees(v[1]):+5.2f} z {math.degrees(v[2]):+5.2f}")
