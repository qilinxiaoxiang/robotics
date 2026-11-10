"""Mass, centre of mass and static leg-joint torque of the MicroDuck with the flight pack. Pure statics from the
model's stand keyframe (no simulation). The pack is a list of point masses from mass_budget.json (trunk-fixed,
stand-keyframe world frame, mm). Single support = one leg carries everything (the hardest instant of walking).
  microduck_rl/.venv/bin/python leg_load.py   -> prints and writes leg_load.json
"""
import json
from pathlib import Path
import mujoco, numpy as np

H = Path(__file__).resolve().parent
SCENE = H.parents[1] / "microduck_rl/cmu/model/scenes/scene_battery-20261104.xml"
BUD = json.loads((H / "mass_budget.json").read_text())
m = mujoco.MjModel.from_xml_path(str(SCENE)); d = mujoco.MjData(m)
mujoco.mj_resetDataKeyframe(m, d, 1); mujoco.mj_forward(m, d)
G = np.array([0, 0, -9.81])

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
duck_m = float(sum(m.body_mass)); duck_com = (d.xipos[1:] * m.body_mass[1:, None]).sum(0) / duck_m
feet = [g for g in range(m.ngeom) if "ankle" in m.body(m.geom_bodyid[g]).name and m.geom_group[g] == 2 and m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH]
fx = []
for g in feet:
    mid = m.geom_dataid[g]; v = m.mesh_vert[m.mesh_vertadr[mid]:m.mesh_vertadr[mid] + m.mesh_vertnum[mid]]
    w = v @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g]; w = w[w[:, 2] < w[:, 2].min() + 0.004]
    fx.append(w)
sole = np.vstack(fx) * 1000
out = {"duck": {"mass_g": round(duck_m * 1000, 1), "com_mm": [round(float(x) * 1000, 1) for x in duck_com]},
       "sole_mm": {"x": [round(float(sole[:, 0].min()), 1), round(float(sole[:, 0].max()), 1)], "y": [round(float(sole[:, 1].min()), 1), round(float(sole[:, 1].max()), 1)]},
       "limit_nm": limit["left_hip_pitch"], "cases": {}}
print("sole contact patch mm:", out["sole_mm"])

def case(name, items):
    pm = sum(i["g"] for i in items) / 1000.0
    pc = sum(np.array(i["pos"], float) * i["g"] for i in items) / max(1e-9, sum(i["g"] for i in items)) if items else np.zeros(3)
    tot = duck_m + pm; com = (duck_com * 1000 * duck_m + pc * pm) / tot
    Ixx = sum(i["g"] / 1000 * ((i["pos"][1] - com[1]) ** 2 + (i["pos"][2] - com[2]) ** 2) for i in items) * 1e-6
    Ixx_d = float(sum(m.body_mass[i] * ((d.xipos[i][1] * 1000 - com[1]) ** 2 + (d.xipos[i][2] * 1000 - com[2]) ** 2) for i in range(1, m.nbody)) * 1e-6)
    res = {"pack_g": round(pm * 1000), "total_g": round(tot * 1000), "pack_com_mm": [round(float(x), 1) for x in pc],
           "com_mm": [round(float(x), 1) for x in com], "roll_inertia_point_masses_kgm2": {"duck": round(Ixx_d, 5), "pack": round(Ixx, 5)}, "joints": {}}
    print(f"\n== {name}: pack {pm * 1000:.0f} g, total {tot * 1000:.0f} g, pack COM {res['pack_com_mm']}, combined COM {res['com_mm']}")
    for j in left:
        b = m.jnt_bodyid[j]; p = d.xanchor[j]; a = d.xaxis[j]; distal = set(desc(b))
        t = np.zeros(3)
        for i in range(1, m.nbody):
            if i not in distal: t += np.cross(d.xipos[i] - p, m.body_mass[i] * G)
        for it in items: t += np.cross(np.array(it["pos"], float) / 1000 - p, it["g"] / 1000 * G)
        tq = abs(float(a @ t)); nm = m.joint(j).name; lim = limit[nm]
        res["joints"][nm] = {"nm": round(tq, 3), "pct": round(tq / lim * 100)}
        print(f"  {nm:16s} single-support {tq:.3f} N.m  = {tq / lim * 100:3.0f} % of {lim:.2f}")
    out["cases"][name] = res

case("none", [])
for name, items in BUD["cases"].items(): case(name, items)
(H / "leg_load.json").write_text(json.dumps(out, indent=1))
