"""Length the head-to-saddle camera cable span needs (D-023 enlarged exit, no neck bundler): the cable is tied inside the head
at the exit and spliced to the right-angle USB-C pigtail at the saddle plug, and is free between. Same as-built MJCF and HOME
mapping as print/a7z-saddle/head_sweep.py. Over the neck/head joint grid it reports
  straight: exit (head) to splice (trunk), a lower bound the span must exceed;
  routed:   exit -> two points on the neck link beside it -> the trunk point under the neck -> splice, the HOME route of
            routes.json bundle_neck / cam_usb with each point carried by the body it sits beside (the cable is not fixed
            there, so this is the long way round, an upper bound for a cable that hugs the neck).
Writes cable_sweep.json.   ~/.venvs/microduck-dyn/bin/python cable_sweep.py"""
import sys, json, itertools, numpy as np, mujoco
from pathlib import Path
HERE = Path(__file__).resolve().parent; MS = HERE.parents[2]
REAL = MS / 'hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014'
sys.path.insert(0, str(REAL))
from static_gap import NAMES, HOME, feet_flat_rot, setup
import evaluate_delay as ev
EXIT = np.array([10.0, 18.5, 98.7])           # bottom of the head floor at the exit centre (guide world, HOME, mm)
SPLICE = np.array([3.0, 30.0, 52.0])          # the splice beside the +y end of the saddle's right-angle plug (plug y 3.5..25.3, z 47.85..55.85)
# MJCF chain trunk_base -> neck (neck_pitch joint, guide z 32.4) -> neck_pitch (head_pitch joint, z 79.4) -> yaw_roll_motion (head_yaw,
# z 98.1) -> jaw_soft (head_roll, z 112.6); each route point rides the link it sits beside
VIA = [((12.0, 15.5, 85.0), 'neck_pitch'), ((10.8, 16.0, 71.2), 'neck'), ((10.8, 16.5, 60.0), 'neck')]
m = mujoco.MjModel.from_xml_path(str(ev.MODEL_DIR / 'scene.xml')); d = mujoco.MjData(m)
Rt = feet_flat_rot(m, d, NAMES, HOME); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel()); setup(m, d, NAMES, HOME, q); mujoco.mj_forward(m, d)
tb = m.body('trunk_base').id; jb = m.body('jaw_soft').id
chain = []; b = jb
while b != tb and b > 0: chain.append(m.body(b).name); b = m.body_parentid[b]
print('jaw_soft chain up to the trunk:', chain)
jid = {n: m.joint(n).qposadr[0] for n in ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll')}
body_of_joint = {n: m.body(m.jnt_bodyid[m.joint(n).id]).name for n in jid}
print('joint bodies', body_of_joint)
def to_world(x):                            # guide trunk-frame mm -> MuJoCo world m, at the current pose of the trunk
    return d.xmat[tb].reshape(3, 3) @ (np.asarray(x) * 1e-3) + d.xpos[tb]
def local(body, x):                          # HOME: body-local coordinates of guide point x
    bid = m.body(body).id; return d.xmat[bid].reshape(3, 3).T @ (to_world(x) - d.xpos[bid])
anchors = [('jaw_soft', local('jaw_soft', EXIT))] + [(bn, local(bn, p)) for p, bn in VIA] + [('trunk_base', local('trunk_base', SPLICE))]
def pts():
    return [d.xpos[m.body(bn).id] + d.xmat[m.body(bn).id].reshape(3, 3) @ v for bn, v in anchors]
q0 = d.qpos.copy()
def lengths():
    P = pts(); return float(np.linalg.norm(P[-1] - P[0]) * 1e3), float(sum(np.linalg.norm(P[i + 1] - P[i]) for i in range(len(P) - 1)) * 1e3)
home = lengths(); print('HOME straight %.1f mm, routed %.1f mm' % home)
rng = {n: np.degrees(m.jnt_range[m.joint(n).id]) for n in jid}
grid = dict(neck_pitch=np.arange(rng['neck_pitch'][0], rng['neck_pitch'][1] + 1, 5.0), head_pitch=np.arange(rng['head_pitch'][0], rng['head_pitch'][1] + 1, 10.0),
            head_yaw=np.array([-170, -135, -90, -80, -45, 0, 45, 80, 90, 135, 170.0]), head_roll=np.array([-25, -18, 0, 18, 25.0]))
rows = []
for np_, hp, hy, hr in itertools.product(*grid.values()):
    d.qpos[:] = q0
    for n, v in zip(jid, (np_, hp, hy, hr)): d.qpos[jid[n]] = np.radians(v)
    mujoco.mj_kinematics(m, d)
    s, r = lengths(); rows.append((float(np_), float(hp), float(hy), float(hr), round(s, 1), round(r, 1)))
trained = lambda r: -43 <= r[0] <= 83 and -43 <= r[1] <= 83 and abs(r[2]) <= 80 and abs(r[3]) <= 18   # walk_brain HEAD_RANGE (head_sweep.py)
out = dict(exit=EXIT.tolist(), splice=SPLICE.tolist(), via=[dict(pt=list(p), body=bn) for p, bn in VIA], rangesDeg={k: v.round(1).tolist() for k, v in rng.items()},
           home=dict(straightMm=round(home[0], 1), routedMm=round(home[1], 1)))
for name, f in (('full', lambda r: True), ('trained', trained)):
    sel = [r for r in rows if f(r)]
    ms, mr = max(sel, key=lambda r: r[4]), max(sel, key=lambda r: r[5])
    out[name] = dict(poses=len(sel), maxStraightMm=ms[4], maxStraightPose=ms[:4], maxRoutedMm=mr[5], maxRoutedPose=mr[:4])
    print(name, out[name])
(HERE / 'cable_sweep.json').write_text(json.dumps(out, indent=1) + '\n')
