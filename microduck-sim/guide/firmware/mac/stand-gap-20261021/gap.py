"""Open-loop stand: sim vs robot, 2026-10-21. Sim only; never touches the robot.

1. The open-loop stand (walk_brain stand mode, NEUTRAL, KP 400) in the 10/20 as-built model, 60 s.
2. Kinematics at the robot's own measured joint angles (real_pose_compare_1021.json, means over tonight's A7Z logs
   app1021-035737 / app1021-040436): model trunk pitch with both soles flat, and the model COM against the sole
   contact patch. If the robot's IMU pitch exceeds the flat-foot model pitch, the robot is rocked onto its toes;
   if the model COM sits inside the patch at the robot's pose while the robot falls, the model's mass is wrong.
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "stand-pose-study-20261020"))
import stand_sim as S  # re-execs under the sim venv
import mujoco, numpy as np
bsc, wb = S.bsc, S.wb

REAL = json.load(open(os.path.join(HERE, "real_pose_compare_1021.json")))
REAL_PITCH = {"ol": 12.1, "s61": 4.3}  # mean IMU pitch over the same rows (cmp.py), + = forward

def kin(q):
    m, d, c, names, bam = S._load(400, S.REAL_VOLT, None, 0.0, False)
    Rt = bsc.feet_flat_rot(m, d, names, q)
    qq = np.zeros(4); mujoco.mju_mat2Quat(qq, Rt.ravel())
    bsc.setup(m, d, names, q, qq)
    pts = np.vstack(bsc.sole_points(m, d))
    d.qpos[2] -= pts[:, 2].min() - 0.0005
    mujoco.mj_forward(m, d)
    pts = np.vstack(bsc.sole_points(m, d))
    R = d.xmat[m.body("trunk_base").id].reshape(3, 3)
    pitch = math.degrees(math.atan2(-R[2, 0], R[2, 2]))
    com = d.subtree_com[0]
    low = pts[pts[:, 2] < pts[:, 2].min() + 0.002]
    # x along the robot's facing direction: trunk x axis projected on the floor
    fx = R[:, 0].copy(); fx[2] = 0; fx /= np.linalg.norm(fx)
    s = low[:, :2] @ fx[:2]; cx = com[:2] @ fx[:2]
    return dict(pitch=round(pitch, 2), com_minus_heel_mm=round((cx - s.min()) * 1000, 1),
                toe_minus_com_mm=round((s.max() - cx) * 1000, 1), patch_mm=round((s.max() - s.min()) * 1000, 1),
                mass=round(float(m.body_subtreemass[0]), 4))

out = {}
for k in ("ol", "s61"):
    q = REAL[k]
    out[k] = dict(kin(q), real_imu_pitch=REAL_PITCH[k])
out["neutral"] = kin(dict(S.NEUTRAL))
r = S.run_case(dict(S.NEUTRAL), T=60.0)
out["sim_open_loop_neutral_kp400"] = {k: r[k] for k in ("fell_at", "max_tilt", "end_pitch", "max_tilt_after_5s", "foot_slip_mm", "total_mass_kg")}
out["sim_open_loop_neutral_kp400"]["trace_pitch"] = [(t, p) for t, _, p, _ in r["trace"][::10]]
print(json.dumps(out, indent=1))
json.dump(out, open(os.path.join(HERE, "gap.json"), "w"), indent=1)
