"""Static COM against the sole edges at HOME and at the robot's measured open-loop stand pose, for each balance manifest.
Sim kinematics only (same method as stand-gap-20261021/head_mass.py). Prints heel and toe margins in mm."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.join(HERE, '..', '..', '..', 'firmware', 'mac')
sys.path.insert(0, os.path.join(MAC, 'stand-pose-study-20261020'))
import stand_sim as S
from static_gap import HOME
import mujoco, numpy as np
bsc = S.bsc
REAL = json.load(open(os.path.join(MAC, 'stand-gap-20261021', 'real_pose_compare_1021.json')))
def margins(manifest, q):
    S.MANIFEST = manifest
    m, d, c, names, bam = S._load(400, S.REAL_VOLT, None, 0.0, False)
    Rt = bsc.feet_flat_rot(m, d, names, q)
    qq = np.zeros(4); mujoco.mju_mat2Quat(qq, Rt.ravel()); bsc.setup(m, d, names, q, qq)
    pts = np.vstack(bsc.sole_points(m, d)); d.qpos[2] -= pts[:, 2].min() - 0.0005; mujoco.mj_forward(m, d)
    pts = np.vstack(bsc.sole_points(m, d)); low = pts[pts[:, 2] < pts[:, 2].min() + 0.002]
    R = d.xmat[m.body('trunk_base').id].reshape(3, 3); fx = R[:, 0].copy(); fx[2] = 0; fx /= np.linalg.norm(fx)
    s = low[:, :2] @ fx[:2]; cx = d.subtree_com[0][:2] @ fx[:2]
    total = float(d.subtree_mass[0] if hasattr(d, 'subtree_mass') else m.body_subtreemass[0])
    return dict(toe_minus_com_mm=round((s.max() - cx) * 1000, 1), com_minus_heel_mm=round((cx - s.min()) * 1000, 1), total_kg=round(total, 3))
for v in ('today', 'saddle'):
    man = os.path.join(HERE, f'manifest-{v}.json')
    print(v, 'HOME', margins(man, HOME), '| measured OL pose', margins(man, REAL['ol']))
