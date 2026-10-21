"""Static foot-roll geometry in the as-built MuJoCo model (sim kinematics only, no dynamics, no robot).
1. Pollen's sole normals (left_foot_collision / right_foot_collision) in the trunk frame at qpos0 and at NEUTRAL (the trained
   stance, hip_roll +-0.0873): is the stock sole flat at the stance?
2. The printed community feet: their sole normal in the robot(guide, qpos0) frame from foot-slipfit-20261019/slipfit-check.json
   footPrintToRobot (column 3 = foot-print +z = sole normal). Compare with Pollen's at qpos0: same, or rolled +-4.8 deg?
3. At NEUTRAL with the trunk placed by feet_flat_rot: height of the inner and outer sole edges for Pollen's feet and for feet
   whose sole is rolled +-4.84 deg about the robot's forward axis (both signs), i.e. which edge touches the floor.
Imports stand_sim from the 10/20 study (re-execs under the sim venv)."""
import json, math, os, sys
sys.path.insert(0, "/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware/mac/stand-pose-study-20261020")
import stand_sim as S  # noqa: E402  (re-execs under ~/.venvs/microduck-dyn)
import mujoco, numpy as np  # noqa: E402
bsc, wb = S.bsc, S.wb
sg = sys.modules[bsc.feet_flat_rot.__module__]
HERE = os.path.dirname(os.path.abspath(__file__))
CHK = json.load(open("/Users/xiangzheng/code/robotics/microduck-sim/guide/print/foot-slipfit-20261019/slipfit-check.json"))
m, d, c, names, bam = S._load(400, S.REAL_VOLT, None, 0.0, False)
trunk = m.body("trunk_base").id
ZERO = {n: 0.0 for n in wb.NAMES}
out = {}

def normals(pose, R=np.eye(3)):
    q = np.zeros(4); mujoco.mju_mat2Quat(q, R.ravel()); sg.setup(m, d, names, pose, q)
    Rt = d.xmat[trunk].reshape(3, 3)
    res = {}
    for g in ("left_foot_collision", "right_foot_collision"):
        n_world = sg.sole_normal(m, d, g)          # points down out of the foot
        n_trunk = Rt.T @ n_world
        gid = m.geom(g).id
        res[g] = dict(down_normal_trunk=np.round(n_trunk, 4).tolist(), geom_center_trunk=np.round(Rt.T @ (d.geom_xpos[gid] - d.xpos[trunk]), 4).tolist(),
                      roll_about_x_deg=round(math.degrees(math.atan2(n_trunk[1], -n_trunk[2])), 2),   # + = normal tilts to +y (left)
                      pitch_about_y_deg=round(math.degrees(math.atan2(n_trunk[0], -n_trunk[2])), 2))
    return res

out["pollen_qpos0"] = normals(ZERO)
out["pollen_neutral"] = normals(dict(S.NEUTRAL))
# community feet: up-normal in the robot (guide, qpos0) frame; convert to a down normal for comparison with Pollen's at qpos0
comm = {}
for side in CHK:
    Rr = np.array(side["footPrintToRobot"])[:3, :3]
    up = Rr[:, 2]; down = -up
    comm[side["side"]] = dict(down_normal_robot=np.round(down, 4).tolist(), roll_about_x_deg=round(math.degrees(math.atan2(down[1], -down[2])), 2),
                              pitch_about_y_deg=round(math.degrees(math.atan2(down[0], -down[2])), 2), seat_rpy_deg=side["seat"]["rollPitchYawDeg"])
out["community_qpos0_from_slipfit_check"] = comm
# relative roll community - pollen at qpos0 (same frame: guide frame == trunk_base at qpos0, build_manifest_copy.py line 45)
for side, g in (("left", "left_foot_collision"), ("right", "right_foot_collision")):
    out["community_minus_pollen_roll_deg_" + side] = round(comm[side]["roll_about_x_deg"] - out["pollen_qpos0"][g]["roll_about_x_deg"], 2)

def edge_heights(pose, roll_deg_left, roll_deg_right, label):
    """Rotate the two sole collision geoms about the robot's forward axis (trunk x at qpos0 == foot body frames' x up to the joint
    angles; we rotate about the geom's own axis that maps to world x at qpos0), then place the trunk with feet_flat_rot, drop to
    the floor and report inner/outer edge heights of each sole's lowest-point band."""
    saved = m.geom_quat.copy()
    sg.setup(m, d, names, ZERO)
    for g, deg in (("left_foot_collision", roll_deg_left), ("right_foot_collision", roll_deg_right)):
        gid = m.geom(g).id
        Rg = d.geom_xmat[gid].reshape(3, 3)
        ax_local = Rg.T @ np.array([1.0, 0, 0])    # world x (forward) in the geom frame at qpos0
        qrot = np.zeros(4); mujoco.mju_axisAngle2Quat(qrot, ax_local, math.radians(deg))
        qn = np.zeros(4); mujoco.mju_mulQuat(qn, m.geom_quat[gid], qrot)
        m.geom_quat[gid] = qn
    Rt = sg.feet_flat_rot(m, d, names, pose)
    q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel()); sg.setup(m, d, names, pose, q)
    pts = sg.sole_points(m, d); allp = np.vstack(pts); d.qpos[2] -= allp[:, 2].min(); mujoco.mj_forward(m, d)
    pts = sg.sole_points(m, d)
    R = d.xmat[trunk].reshape(3, 3)
    res = dict(label=label, trunk_pitch_deg=round(math.degrees(math.atan2(-R[2, 0], R[2, 2])), 2),
               trunk_roll_deg=round(math.degrees(math.atan2(R[2, 1], R[2, 2])), 2))
    for name, p in zip(("left", "right"), pts):
        low = p[p[:, 2] < p[:, 2].min() + 0.006]   # the bottom 6 mm band of the hull
        yin = low[:, 1].min() if name == "left" else low[:, 1].max()   # inner edge: toward y=0
        yout = low[:, 1].max() if name == "left" else low[:, 1].min()
        inner = low[np.abs(low[:, 1] - yin) < 0.003]; outer = low[np.abs(low[:, 1] - yout) < 0.003]
        res[name] = dict(z_min_mm=round(float(p[:, 2].min()) * 1000, 2), inner_edge_min_z_mm=round(float(inner[:, 2].min()) * 1000, 2),
                         outer_edge_min_z_mm=round(float(outer[:, 2].min()) * 1000, 2), width_mm=round(float(low[:, 1].max() - low[:, 1].min()) * 1000, 1),
                         sole_roll_vs_floor_deg=round(math.degrees(math.atan2(float(outer[:, 2].min() - inner[:, 2].min()), float(abs(yout - yin)))), 2))
    m.geom_quat[:] = saved
    return res

cases = [("pollen", 0, 0)]
rl, rr = out["community_minus_pollen_roll_deg_left"], out["community_minus_pollen_roll_deg_right"]
cases += [("community as fitted (roll %+.2f / %+.2f)" % (rl, rr), rl, rr), ("mirror of that (roll %+.2f / %+.2f)" % (-rl, -rr), -rl, -rr),
          ("soles rolled inward-normal 4.84 (L -4.84, R +4.89)", -4.84, 4.89), ("soles rolled outward-normal 4.84 (L +4.84, R -4.89)", 4.84, -4.89)]
out["edge_heights_at_neutral"] = [edge_heights(dict(S.NEUTRAL), a, b, lbl) for lbl, a, b in cases]
out["edge_heights_at_qpos0"] = [edge_heights(ZERO, a, b, lbl) for lbl, a, b in cases[:2]]
json.dump(out, open(os.path.join(HERE, "foot_roll_static.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
