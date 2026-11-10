"""Export the as-built MicroDuck visual meshes per body (stand-keyframe world frame, mm) plus per-pose body
transforms, so a page can show the real robot in several poses with trunk-fixed attachments.
Poses: stand keyframe; the deepest logged real ground-pick bend (camera-calib-20261030/bend-20261030, tilted by
its logged gravity vector, feet on the floor); head scan (pickup.py: yaw 1.2 rad, head_pitch 0.8).
  microduck_rl/.venv/bin/python export_duck_poses.py   -> duck_poses.json
"""
import base64, glob, json
from pathlib import Path
import mujoco, numpy as np

H = Path(__file__).resolve().parent
SCENE = H.parents[1] / "microduck_rl/cmu/model/scenes/scene_battery-20261104.xml"
BEND = H.parents[1] / "guide/firmware/mac/camera-calib-20261030/bend-20261030"
m = mujoco.MjModel.from_xml_path(str(SCENE)); d = mujoco.MjData(m)
mujoco.mj_resetDataKeyframe(m, d, 1); mujoco.mj_forward(m, d)
q0 = d.qpos.copy()
hinge = {m.joint(j).name: j for j in range(m.njnt) if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE}
trunk = m.body("trunk_base").id

def T(b):
    M = np.eye(4); M[:3, :3] = d.xmat[b].reshape(3, 3); M[:3, 3] = d.xpos[b] * 1000.0; return M

stand_T = {b: T(b) for b in range(m.nbody)}
parts = {}
for g in range(m.ngeom):
    if m.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH or m.geom_group[g] != 2: continue
    mid = m.geom_dataid[g]
    v = m.mesh_vert[m.mesh_vertadr[mid]:m.mesh_vertadr[mid] + m.mesh_vertnum[mid]].astype(np.float64)
    f = m.mesh_face[m.mesh_faceadr[mid]:m.mesh_faceadr[mid] + m.mesh_facenum[mid]].astype(np.int64)
    w = (v @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g]) * 1000.0
    key = (int(m.geom_bodyid[g]), tuple(round(float(c), 3) for c in m.geom_rgba[g][:3]))
    p = parts.setdefault(key, {"v": [], "f": [], "n": 0})
    p["v"].append(w); p["f"].append(f + p["n"]); p["n"] += len(w)

def setq(q):
    d.qpos[:] = q0
    for k, v in q.items():
        if k in hinge: d.qpos[m.jnt_qposadr[hinge[k]]] = v
    mujoco.mj_kinematics(m, d)

def pose(q, gb=None):
    """per-body matrix that moves stand-world vertices to this pose; optional tilt so logged gravity points down."""
    setq(q)
    W = np.eye(4)
    if gb is not None:
        g = np.array(gb, float); g /= np.linalg.norm(g)
        gw = stand_T[trunk][:3, :3] @ g                    # gravity in the stand world frame for this trunk
        ang = np.arctan2(gw[0], -gw[2])                    # rotate about y so gw -> -z
        c, s = np.cos(ang), np.sin(ang)
        W[:3, :3] = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    out = {}
    for b in range(m.nbody): out[b] = W @ T(b) @ np.linalg.inv(stand_T[b])
    # feet on the floor, mid-foot kept at its stand x
    feet = [k for k in parts if "ankle" in m.body(k[0]).name]
    P = np.vstack([np.c_[np.vstack(parts[k]["v"]), np.ones(parts[k]["n"])] @ out[k[0]].T for k in feet])[:, :3]
    S = np.vstack([np.vstack(parts[k]["v"]) for k in feet])
    shift = np.array([S[:, 0].mean() - P[:, 0].mean(), 0.0, -P[:, 2].min() + S[:, 2].min()])
    for b in out: out[b][:3, 3] += shift
    return out

rows = []
for f in sorted(glob.glob(str(BEND / "sweep*/rows_matched.json"))): rows += json.load(open(f))
rows = [r for r in rows if r.get("q") and r.get("gb")]
deep = max(rows, key=lambda r: r["gb"][0])
print("deepest bend row:", deep["name"], "phase", deep.get("phase"), "gb", deep["gb"], deep["q"])
poses = {
    "stand": pose({}),
    "bend": pose(deep["q"], deep["gb"]),
    "scan": pose({"head_yaw": 1.2, "head_pitch": 0.8}),
}
out = {"parts": [], "poses": {}, "bodies": {b: m.body(b).name for b in range(m.nbody)}, "trunk": int(trunk),
       "bend_row": {"name": deep["name"], "phase": deep.get("phase"), "gb": deep["gb"], "q": deep["q"]}}
for (b, col), p in parts.items():
    v = np.concatenate(p["v"]).astype(np.float32); f = np.concatenate(p["f"]).astype(np.uint32)
    out["parts"].append({"body": b, "color": col, "pos": base64.b64encode(v.tobytes()).decode(), "idx": base64.b64encode(f.tobytes()).decode()})
for name, mats in poses.items():
    out["poses"][name] = {str(b): [round(float(x), 5) for x in M[:3].reshape(-1)] for b, M in mats.items()}
root = m.body("trunk_base").id
setq({}); mujoco.mj_forward(m, d)
out["com_mm"] = [round(float(x) * 1000, 1) for x in d.subtree_com[root]]
out["mass_g"] = round(float(sum(m.body_mass)) * 1000, 1)
(H / "duck_poses.json").write_text(json.dumps(out))
print("bytes", (H / "duck_poses.json").stat().st_size, "com", out["com_mm"], "mass", out["mass_g"])
