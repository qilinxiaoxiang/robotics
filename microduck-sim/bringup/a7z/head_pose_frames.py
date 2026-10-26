"""Body poses of the neck and head links in the guide trunk frame (mm) for a few head poses, for render_head_poses.py.
Same model and HOME as head_sweep_v2.py. Each pose gives, per body, the 4x4 transform that carries a guide-world HOME point to
that pose, plus the exit point and the straight exit-to-front-wall distance. Writes head-pose-frames.json.
~/.venvs/microduck-dyn/bin/python head_pose_frames.py"""
import sys, json, numpy as np, mujoco
from pathlib import Path
HERE = Path(__file__).resolve().parent; MS = HERE.parents[1]
sys.path.insert(0, str(MS / 'hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014'))
from static_gap import NAMES, HOME, feet_flat_rot, setup
import evaluate_delay as ev
SW = json.loads((HERE / 'head-sweep-v2.json').read_text())
EXIT, WALL = np.array(SW['exit']), np.array(SW['splice'])
BODIES = ('neck', 'neck_pitch', 'yaw_roll_motion', 'jaw_soft')
POSES = {  # (neck_pitch, head_pitch, head_yaw, head_roll) deg; HOME is 20, 20, 0, 0; trained range is HOME +-63, +-63, +-80, +-18
    'home': (20, 20, 0, 0), 'neck_fwd': (-43, 20, 0, 0), 'yaw80': (20, 20, -80, 0), 'pitch_dn': (20, -43, 0, 0),
    'worst': tuple(SW['trained']['maxStraightPose']),
}
m = mujoco.MjModel.from_xml_path(str(ev.MODEL_DIR / 'scene.xml')); d = mujoco.MjData(m)
Rt = feet_flat_rot(m, d, NAMES, HOME); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel()); setup(m, d, NAMES, HOME, q); mujoco.mj_forward(m, d)
tb = m.body('trunk_base').id; q0 = d.qpos.copy()
jid = {n: m.joint(n).qposadr[0] for n in ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll')}


def frames():  # body -> 4x4 in the guide trunk frame, mm
    Rtb, ptb = d.xmat[tb].reshape(3, 3), d.xpos[tb]
    out = {}
    for bn in BODIES:
        b = m.body(bn).id
        T = np.eye(4); T[:3, :3] = Rtb.T @ d.xmat[b].reshape(3, 3); T[:3, 3] = Rtb.T @ (d.xpos[b] - ptb) * 1e3
        out[bn] = T
    return out


def pose(p):
    d.qpos[:] = q0
    for n, v in zip(jid, p): d.qpos[jid[n]] = np.radians(v)
    mujoco.mj_kinematics(m, d)
    return frames()


F0 = pose(POSES['home'])
res = {}
for k, p in POSES.items():
    F = pose(p)
    carry = {bn: (F[bn] @ np.linalg.inv(F0[bn])).round(5).tolist() for bn in BODIES}
    ex = (np.array(carry['jaw_soft']) @ np.append(EXIT, 1))[:3]
    res[k] = dict(jointsDeg=list(p), carry=carry, exit=ex.round(1).tolist(), straightMm=round(float(np.linalg.norm(ex - WALL)), 1))
    print(k, p, res[k]['exit'], res[k]['straightMm'])
(HERE / 'head-pose-frames.json').write_text(json.dumps(dict(exit=EXIT.tolist(), wall=WALL.tolist(), poses=res), indent=1) + '\n')
