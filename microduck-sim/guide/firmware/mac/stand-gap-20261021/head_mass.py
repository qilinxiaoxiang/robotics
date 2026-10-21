"""How much extra head mass (at the head-board position, stand_sim PI_POS on jaw_soft) moves the model COM to the toe
edge at the robot's measured open-loop pose. Sim kinematics only."""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "stand-pose-study-20261020"))
import stand_sim as S
import mujoco, numpy as np
bsc = S.bsc
REAL = json.load(open(os.path.join(HERE, "real_pose_compare_1021.json")))
def margin(q, head_g):
    m, d, c, names, bam = S._load(400, S.REAL_VOLT, None, head_g, False)
    Rt = bsc.feet_flat_rot(m, d, names, q)
    qq = np.zeros(4); mujoco.mju_mat2Quat(qq, Rt.ravel()); bsc.setup(m, d, names, q, qq)
    pts = np.vstack(bsc.sole_points(m, d)); d.qpos[2] -= pts[:, 2].min() - 0.0005; mujoco.mj_forward(m, d)
    pts = np.vstack(bsc.sole_points(m, d)); low = pts[pts[:, 2] < pts[:, 2].min() + 0.002]
    R = d.xmat[m.body("trunk_base").id].reshape(3, 3); fx = R[:, 0].copy(); fx[2] = 0; fx /= np.linalg.norm(fx)
    s = low[:, :2] @ fx[:2]; cx = d.subtree_com[0][:2] @ fx[:2]
    head = d.xpos[m.body("jaw_soft").id][:2] @ fx[:2]
    return round((s.max() - cx) * 1000, 1), round((head - s.max()) * 1000, 1)
for g in (0, 20, 50, 100, 200):
    print("head +%d g: toe - COM %s mm, head body ahead of toe %s mm" % ((g,) + margin(REAL["ol"], g)))
