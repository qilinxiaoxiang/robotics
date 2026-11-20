"""Leg clearance to candidate backpack envelopes over hip pitch +-30, roll +-10 (trunk frame = guide frame, mm)."""
import json, sys
import mujoco, numpy as np

SCENE = "/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl/cmu/model/scenes/scene_battery-20261104.xml"
BOXES = json.loads(sys.argv[1])
m = mujoco.MjModel.from_xml_path(SCENE); d = mujoco.MjData(m)
mujoco.mj_resetDataKeyframe(m, d, 1); mujoco.mj_forward(m, d)
q0 = d.qpos.copy()
trunk = m.body("trunk_base").id
LEG = {"left": ["yaw2roll", "hip_l", "upper_leg_left", "leg", "ankle_left"],
       "right": ["bearing_roll", "hip_l_2", "upper_leg_right", "leg_2", "ankle_right"]}
geoms = {s: [g for g in range(m.ngeom) if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH and m.body(m.geom_bodyid[g]).name in names]
         for s, names in LEG.items()}
def verts(g):
    mid = m.geom_dataid[g]; a = m.mesh_vertadr[mid]
    return m.mesh_vert[a:a + m.mesh_vertnum[mid]].astype(float)
V = {g: verts(g) for s in geoms for g in geoms[s]}
def qadr(n): return m.jnt_qposadr[m.joint(n).id]
def box_dist(P, lo, hi):
    q = np.maximum(np.maximum(np.array(lo) - P, P - np.array(hi)), 0.0)
    return np.sqrt((q * q).sum(1))
out = {}
for name, (lo, hi) in BOXES.items():
    best = (1e9, None)
    for side in ("left", "right"):
        for dp in range(-30, 31, 5):
            for dr in range(-10, 11, 5):
                d.qpos[:] = q0
                d.qpos[qadr(f"{side}_hip_pitch")] += np.radians(dp)
                d.qpos[qadr(f"{side}_hip_roll")] += np.radians(dr)
                mujoco.mj_kinematics(m, d)
                Rt = d.xmat[trunk].reshape(3, 3); pt = d.xpos[trunk]
                for g in geoms[side]:
                    R = d.geom_xmat[g].reshape(3, 3); p = d.geom_xpos[g]
                    W = V[g] @ R.T + p
                    T = (W - pt) @ Rt * 1000.0          # trunk frame, mm
                    dist = box_dist(T, lo, hi).min()
                    if dist < best[0]:
                        best = (float(dist), dict(side=side, pitch=dp, roll=dr, body=m.body(m.geom_bodyid[g]).name))
    out[name] = dict(min_mm=round(best[0], 2), at=best[1])
print(json.dumps(out, indent=1))
