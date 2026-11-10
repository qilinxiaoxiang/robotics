"""Geometric clearance of jetpack layouts against the duck's moving parts (forward kinematics only, no simulation).
Pose sets: the stand pose, random leg/head poses over half and full joint ranges, the logged real ground-pick bend
poses (camera-calib-20261030/bend-20261030) and the head scan poses pickup.py commands. The trunk is fixed; pack
volumes are trunk-fixed boxes in the stand-keyframe world frame (mm). For bend poses the lowest pack point above
the sole plane is also reported, using the logged gravity vector.
  microduck_rl/.venv/bin/python sweep_check.py [N]
"""
import glob, json, sys
from pathlib import Path
import mujoco, numpy as np

H = Path(__file__).resolve().parent
SCENE = H.parents[1] / "microduck_rl/cmu/model/scenes/scene_battery-20261104.xml"
BEND = H.parents[1] / "guide/firmware/mac/camera-calib-20261030/bend-20261030"
LAYOUTS = json.loads((H / "pack_geometry.json").read_text())["layouts"]
m = mujoco.MjModel.from_xml_path(str(SCENE)); d = mujoco.MjData(m)
mujoco.mj_resetDataKeyframe(m, d, 1); mujoco.mj_forward(m, d)
q0 = d.qpos.copy(); rng = np.random.default_rng(0)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 600
jn = [m.joint(j).name for j in range(m.njnt)]
hinge = {jn[j]: j for j in range(m.njnt) if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE}
trunk = m.body("trunk_base").id
Rt0 = d.xmat[trunk].reshape(3, 3).copy()

local = {}
for g in range(m.ngeom):
    if m.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH or m.geom_group[g] != 2: continue
    mid = m.geom_dataid[g]; a, n = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
    v = m.mesh_vert[a:a + n][:: max(1, n // 1500)]
    R = np.zeros(9); mujoco.mju_quat2Mat(R, m.geom_quat[g]); R = R.reshape(3, 3)
    local.setdefault(m.geom_bodyid[g], []).append(v @ R.T + m.geom_pos[g])
local = {b: np.vstack(v) for b, v in local.items()}
local = {b: v[rng.choice(len(v), min(len(v), 2500), replace=False)] for b, v in local.items()}   # keep the job in seconds
names = {b: m.body(b).name for b in local}
LEG = [b for b in local if any(k in names[b] for k in ("leg", "ankle", "hip", "roll")) and b != trunk and "yaw_roll" not in names[b]]
HEAD = [b for b in local if names[b] in ("neck", "neck_pitch", "yaw_roll_motion", "jaw_soft")]

def pts(bodies):
    return np.vstack([(local[b] @ d.xmat[b].reshape(3, 3).T + d.xpos[b]) * 1000.0 for b in bodies])

def setq(q):
    d.qpos[:] = q0
    for k, v in q.items():
        if k in hinge: d.qpos[m.jnt_qposadr[hinge[k]]] = v
    mujoco.mj_kinematics(m, d)

def gap(P, lo, hi):
    return float(np.linalg.norm(np.maximum(np.maximum(lo - P, P - hi), 0), axis=1).min())

def rand_pose(prefixes, scale):
    q = {}
    for k, j in hinge.items():
        if k.startswith(prefixes):
            lo, hi = m.jnt_range[j]; c = q0[m.jnt_qposadr[j]]
            q[k] = rng.uniform(c + (lo - c) * scale, c + (hi - c) * scale)
    return q

# pose sets -> list of (label, point cloud of the moving group, extra)
sets = {}
setq({}); sets["stand: legs"] = [pts(LEG)]; sets["stand: head"] = [pts(HEAD)]
for sc in (0.5, 1.0):
    P = []
    for _ in range(N): setq(rand_pose(("left_", "right_"), sc)); P.append(pts(LEG))
    sets[f"legs random, {int(sc * 100)} % of joint range"] = P
    P = []
    for _ in range(N): setq(rand_pose(("neck", "head"), sc)); P.append(pts(HEAD))
    sets[f"head random, {int(sc * 100)} % of joint range"] = P
# head scan poses of pickup.py (LOOK/MID/NEAR x SCAN_YAWS), read both as absolute and as offset from the stand pose
st = {k: float(q0[m.jnt_qposadr[j]]) for k, j in hinge.items()}
P = []
for pose in ({"head_pitch": 0.8}, {"head_pitch": 1.0}, {"neck_pitch": -0.8, "head_pitch": 1.1}):
    for yaw in np.linspace(-1.2, 1.2, 13):
        for rel in (False, True):
            q = {k: (st[k] + v if rel else v) for k, v in pose.items()}; q["head_yaw"] = yaw
            setq(q); P.append(pts(HEAD))
sets["head scan poses of pickup.py (yaw to +-1.2 rad, looking down)"] = P
# head yaw alone at the stand head pitch
P = []
for yaw in np.linspace(-2.97, 2.97, 61): setq({"head_yaw": yaw}); P.append(pts(HEAD))
sets["head yaw alone, full +-170 deg, stand pitch"] = P
# logged bend poses
rows = []
for f in sorted(glob.glob(str(BEND / "sweep*/rows_matched.json"))): rows += json.load(open(f))
rows += json.load(open(BEND / "bend_ticks.json"))["obs"]
rows = [r for r in rows if r.get("q") and r.get("gb")]
Pl, Ph, bend_info = [], [], []
for r in rows:
    setq(r["q"]); Pl.append(pts(LEG)); Ph.append(pts(HEAD))
    g = np.array(r["gb"], float); g /= np.linalg.norm(g)        # gravity direction in the trunk frame (points down)
    feet = pts([b for b in LEG if "ankle" in names[b]])
    bend_info.append((Rt0 @ g, float((feet @ (Rt0 @ g)).max()), r.get("phase")))
sets[f"logged real bend poses ({len(rows)} rows): legs"] = Pl
sets[f"logged real bend poses ({len(rows)} rows): head"] = Ph

for lname, lay in LAYOUTS.items():
    vols = {k: (np.array(v["lo"], float), np.array(v["hi"], float)) for k, v in lay["volumes"].items()}
    print(f"\n===== layout {lname}: {lay.get('note', '')}")
    for sname, P in sets.items():
        res = {}
        for k, (lo, hi) in vols.items():
            gs = np.array([gap(p, lo, hi) for p in P])
            res[k] = f"{gs.min():.0f}" + (f" ({(gs < 0.5).mean() * 100:.0f}% hit)" if gs.min() < 0.5 else "")
        print(f"  {sname:62s} min gap mm: " + ", ".join(f"{k} {v}" for k, v in res.items()))
    # ground clearance of the pack in the bend: lowest pack corner above the sole plane, along logged gravity
    lowest = 1e9
    for gw, sole, ph in bend_info:
        for k, (lo, hi) in vols.items():
            corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
            lowest = min(lowest, float(sole - (corners @ gw).max()))
    print(f"  bend: lowest pack corner is {lowest:.0f} mm above the sole plane (worst logged bend row)")
