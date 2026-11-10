"""Static leg-joint torque of the standing MicroDuck with a flight pack on the trunk. Pure statics from the model's
stand keyframe (no simulation): torque about each joint axis from the weight of everything on the trunk side of it.
  microduck_rl/.venv/bin/python leg_load.py
"""
from pathlib import Path
import mujoco, numpy as np
SCENE = Path(__file__).resolve().parents[2] / "microduck_rl/cmu/model/scenes/scene_battery-20261104.xml"
m = mujoco.MjModel.from_xml_path(str(SCENE)); d = mujoco.MjData(m)
mujoco.mj_resetDataKeyframe(m, d, 1); mujoco.mj_forward(m, d)
G = np.array([0, 0, -9.81])
def subtree(b):
    return [i for i in range(m.nbody) if i == b or (lambda j: any(k == b for k in iter(lambda s=[i]: s.__setitem__(0, m.body_parentid[s[0]]) or s[0], 0)))(i)]
def desc(b):
    out = []
    for i in range(1, m.nbody):
        j = i
        while j != 0:
            if j == b: out.append(i); break
            j = m.body_parentid[j]
    return out
limit = {m.joint(m.actuator_trnid[a, 0]).name: float(m.actuator_forcerange[a, 1]) for a in range(m.nu)}
left = [j for j in range(m.njnt) if m.joint(j).name.startswith("left_")]
trunk = m.body("trunk_base").id
print("limits N.m:", {k: v for k, v in limit.items() if k.startswith("left_")})
print("stand pose: joint positions (mm) and axes")
PACKS = {"none": (0, None), "A twin boosters 4x50 EDF, batteries in pylons, 705 g": (0.705, [-0.013, 0, 0.175]), "B twin 70 EDF, battery on back, 880 g": (0.880, [-0.035, 0, 0.165])}
for name, (pm, ppos) in PACKS.items():
    print(f"\n== {name}: total {sum(m.body_mass) * 1000 + pm * 1000:.0f} g")
    for j in left:
        b = m.jnt_bodyid[j]; p = d.xanchor[j]; a = d.xaxis[j]
        distal = set(desc(b))
        right_leg = set(desc(m.body("bearing_roll").id)) if "bearing_roll" in [m.body(i).name for i in range(m.nbody)] else set()
        def moment(bodies, extra=True):
            t = np.zeros(3)
            for i in bodies:
                t += np.cross(d.xipos[i] - p, m.body_mass[i] * G)
            if extra and pm: t += np.cross(np.array(ppos) - p, pm * G)
            return float(a @ t)
        prox_all = [i for i in range(1, m.nbody) if i not in distal]
        upper = [i for i in prox_all if i not in right_leg]
        single = abs(moment(prox_all)); double = abs(moment(upper)) / 2
        lim = limit.get(m.joint(j).name, float("nan"))
        print(f"  {m.joint(j).name:16s} double {double:.3f}  single {single:.3f}  limit {lim:.2f}  single/limit {single / lim * 100:4.0f} %")
