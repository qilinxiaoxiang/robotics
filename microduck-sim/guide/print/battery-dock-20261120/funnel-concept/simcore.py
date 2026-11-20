"""Shared sim core for the dock funnel concept: the real Brain sit (brain_sim_check.py --model asbuilt --manifest current)
with optional static dock geometry and a backpack collision hull added to the as-built spec, run on the Mac mini.

Frames. Robot STLs of battery-v2-cad-20261120 are in the guide frame = trunk_base frame, mm (legsit.py uses them this
way). Dock frame D: the seated robot's trunk frame flattened to the floor (x forward, y left, z up from the floor, yaw
only), the frame build_dock.py draws in. The nominal dock pose in the world is the baseline seated trunk pose (no dock),
so a robot with zero offset lands exactly where build_dock.py assumed. A start offset (dx, dy, dyaw) is the robot's pose
in D before the sit; yaw turns about the pad centre (x -69.5, y 0) so it does not add a pad shift of its own.
"""
import contextlib, io, json, math, os, runpy, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
MD = HERE.parents[3]                                    # microduck-sim
BV2 = MD / "guide/print/battery-v2-cad-20261120/build"
MAC = MD / "guide/firmware/mac"
PAD_C = np.array([-69.5, 0.0])                          # pad centre, yaw pivot (mm, D)

sys.path.insert(0, str(MD / "microduck_rl/cmu/model"))
import mujoco  # noqa: E402
import trimesh  # noqa: E402
import visual  # noqa: E402  (the module evaluate_delay.load takes apply_visual_to_spec from)

LEG_BODIES = ["yaw2roll", "hip_l", "upper_leg_left", "leg", "ankle_left",
              "bearing_roll", "hip_l_2", "upper_leg_right", "leg_2", "ankle_right"]


def backpack_verts_mm():
    v = [trimesh.load(BV2 / f, force="mesh").vertices for f in ("battery_v2_frame-world.stl", "battery_v2_cap-world.stl")]
    return np.vstack(v)


def pad_verts_mm():
    return {k: trimesh.load(BV2 / f"parts/contact_pad_{k}-world.stl", force="mesh").vertices for k in ("plus", "minus")}


def yaw_T(x, y, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([[c, -s, x], [s, c, y], [0, 0, 1.0]])


def offset_T(dx, dy, dyaw_deg):
    """robot pose in D (2D homogeneous, mm): rotate about the pad centre, then translate."""
    a = math.radians(dyaw_deg)
    R = yaw_T(0, 0, a)
    P = np.eye(3); P[:2, 2] = PAD_C
    Pi = np.eye(3); Pi[:2, 2] = -PAD_C
    T = np.eye(3); T[:2, 2] = [dx, dy]
    return T @ P @ R @ Pi


def run(dock_boxes=None, seat_pose=None, offset=(0, 0, 0), mu_rail=0.35, floor_mu=1.0, sit_at=4.0, unsit_at=None,
        end_after=None, every=10, extra_args=(), hull=True, seed=0):
    """dock_boxes: list of dict(name, size=(hx,hy,hz) mm half sizes, pos=(x,y,z) mm in D, R=3x3 rotation in D).
    seat_pose: (x_m, y_m, yaw_rad) of the baseline seated trunk in the world (D origin). Returns the recorded run."""
    bp = backpack_verts_mm() / 1000.0
    orig = visual.apply_visual_to_spec
    DW = None
    if dock_boxes is not None:
        sx, sy, syaw = seat_pose
        S = yaw_T(sx * 1000, sy * 1000, syaw)                 # D -> world, mm
        DW = S @ np.linalg.inv(offset_T(*offset))             # dock frame pose in the world for this offset
    dyaw_w = math.atan2(DW[1, 0], DW[0, 0]) if DW is not None else 0.0

    def hooked(spec, *a, **kw):
        n = orig(spec, *a, **kw)
        if not hull:
            return n
        # backpack collision: two convex hulls (lower tier below seated z 47, wide upper tier above), so the hull of the
        # whole backpack does not invent a slope between the tiers where a rail would touch it
        for k, sel in (("lo", bp[:, 2] < -0.0099), ("hi", bp[:, 2] >= -0.0101)):
            hm = trimesh.convex.convex_hull(bp[sel])
            spec.add_mesh(name=f"bp_hull_{k}", uservert=hm.vertices.ravel().tolist(), userface=hm.faces.ravel().tolist())
            spec.body("trunk_base").add_geom(name=f"bp_hull_{k}_geom", type=mujoco.mjtGeom.mjGEOM_MESH,
                                             meshname=f"bp_hull_{k}", contype=1, conaffinity=1, density=0, mass=0,
                                             condim=3, friction=[mu_rail, 0.005, 0.0001], rgba=[1, .5, 0, .3], group=3)
        if dock_boxes is not None:
            Rz = np.array([[math.cos(dyaw_w), -math.sin(dyaw_w), 0], [math.sin(dyaw_w), math.cos(dyaw_w), 0], [0, 0, 1]])
            for b in dock_boxes:
                p = DW @ np.array([b["pos"][0], b["pos"][1], 1.0])
                R = Rz @ np.asarray(b.get("R", np.eye(3)), float)
                q = np.zeros(4); mujoco.mju_mat2Quat(q, R.ravel())
                spec.worldbody.add_geom(name="dock_" + b["name"], type=mujoco.mjtGeom.mjGEOM_BOX,
                                        size=[s_ / 1000 for s_ in b["size"]],
                                        pos=[p[0] / 1000, p[1] / 1000, b["pos"][2] / 1000], quat=q.tolist(),
                                        contype=1, conaffinity=1, condim=3, friction=[mu_rail, 0.005, 0.0001],
                                        rgba=[.9, .5, .1, 1])
        return n

    visual.apply_visual_to_spec = hooked
    rec = dict(t=[], qpos=[], contacts=[])
    st = dict(n=0, m=None)
    _step = mujoco.mj_step

    def step(m, d, *a):
        _step(m, d, *a)
        st["n"] += 1
        if st["m"] is None:
            st["m"] = m
            st["dock_ids"] = {i for i in range(m.ngeom) if m.geom(i).name.startswith("dock_")}
            st["floor"] = m.geom("floor").id
        if st["n"] % every:
            return
        rec["t"].append(float(d.time)); rec["qpos"].append(d.qpos.copy())
        cs = []
        for i in range(d.ncon):
            c = d.contact[i]
            g1, g2 = int(c.geom1), int(c.geom2)
            if g1 in st["dock_ids"] or g2 in st["dock_ids"]:
                other = g2 if g1 in st["dock_ids"] else g1
                cs.append((m.geom(other).name, m.body(m.geom_bodyid[other]).name, round(float(c.dist) * 1000, 2)))
        rec["contacts"].append(cs)
        fl = sorted({(m.geom(int(c.geom2 if c.geom1 == st["floor"] else c.geom1)).name or m.body(m.geom_bodyid[int(c.geom2 if c.geom1 == st["floor"] else c.geom1)]).name)
                     for c in d.contact[:d.ncon] if st["floor"] in (int(c.geom1), int(c.geom2))})
        rec.setdefault("floor", []).append(fl)

    # teleop_sim_batch.py's sit_stand_from_stand61 case with the real-condition flags of robot_state_check.py
    # --print-sim-args (2026-11-20: --volt 7.6 --drop 0.036); the seed draws the dropped servo reads
    args = ["brain_sim_check.py", "--model", "asbuilt", "--manifest", "current", "--volt", "7.6", "--drop", "0.036",
            "--seed", str(seed), "--walk-s", "0", "--sit-at", str(sit_at), "--floor-mu", str(floor_mu)]
    if unsit_at is not None:
        args += ["--unsit-at", str(unsit_at)]
    args += list(extra_args)
    sys.argv = args
    sys.path.insert(0, str(MAC)); cwd = os.getcwd(); os.chdir(MAC)
    mujoco.mj_step = step
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            try:
                runpy.run_path(str(MAC / "brain_sim_check.py"), run_name="__main__")
            except SystemExit as e:
                sys.stderr.write(f"SystemExit {e.code}\n")
    finally:
        mujoco.mj_step = _step; os.chdir(cwd); visual.apply_visual_to_spec = orig
    lines = buf.getvalue().strip().splitlines()
    try:
        summary = json.loads(lines[-1])
    except Exception:
        summary = {"raw_tail": lines[-5:]}
    rec["summary"] = summary
    rec["m"] = st["m"]
    rec["DW"] = DW
    return rec


def trunk_pose(m, qpos):
    """trunk_base world pose from a stored qpos (mj_kinematics on a scratch data)."""
    d = mujoco.MjData(m); d.qpos[:] = qpos; mujoco.mj_kinematics(m, d)
    t = m.body("trunk_base").id
    return d.xpos[t].copy(), d.xmat[t].reshape(3, 3).copy(), d


def mesh_geoms(m, bodies):
    ids = {m.body(b).id for b in bodies}
    return [g for g in range(m.ngeom) if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH and m.geom_bodyid[g] in ids]


def geom_verts(m, g):
    mid = m.geom_dataid[g]; a = m.mesh_vertadr[mid]
    return m.mesh_vert[a:a + m.mesh_vertnum[mid]].astype(float)


def world_pts(m, d, geoms):
    out = []
    for g in geoms:
        R = d.geom_xmat[g].reshape(3, 3); p = d.geom_xpos[g]
        out.append(geom_verts(m, g) @ R.T + p)
    return np.vstack(out) if out else np.zeros((0, 3))


def to_D(pts_w_m, DW_mm):
    """world points (m) -> D (mm)"""
    Di = np.linalg.inv(DW_mm)
    P = pts_w_m * 1000.0
    xy = (Di @ np.c_[P[:, 0], P[:, 1], np.ones(len(P))].T).T[:, :2]
    return np.c_[xy, P[:, 2]]
