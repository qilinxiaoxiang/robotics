"""Head sweep against the final saddle outline (D-022; copy of a7z-slice-20261022/head_sweep.py taking the box as 6 args): our V1.17 head meshes (guide world, HOME) attached to jaw_soft in the as-built
MJCF; the saddle as a box on the trunk; mj_geomDistance over the neck/head joint ranges. Convex hulls (MuJoCo mesh
collision), so distances are conservative for the lower head shell. Prints the minimum distance per joint band and the
poses that come closest; writes head_sweep.json."""
import sys, json, itertools, numpy as np, mujoco
from pathlib import Path
HERE = Path(__file__).resolve().parent; MS = HERE.parents[2]
REAL = MS / 'hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014'; WORLD = MS / 'guide/print/world'
sys.path.insert(0, str(REAL))
from static_gap import NAMES, HOME, feet_flat_rot, setup, sole_points
import evaluate_delay as ev
mm = 0.001
SADDLE = dict(lo=tuple(map(float, sys.argv[1:4])), hi=tuple(map(float, sys.argv[4:7])))  # final saddle outline from build.json
spec = mujoco.MjSpec.from_file(str(ev.MODEL_DIR / 'scene.xml'))
# pose at HOME first (to get jaw_soft relative to trunk), with the unmodified model
m0 = spec.compile(); d0 = mujoco.MjData(m0)
Rt = feet_flat_rot(m0, d0, NAMES, HOME); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel()); setup(m0, d0, NAMES, HOME, q); mujoco.mj_forward(m0, d0)
tb, jb = m0.body('trunk_base').id, m0.body('jaw_soft').id
Rtr, ptr = d0.xmat[tb].reshape(3, 3), d0.xpos[tb]; Rj, pj = d0.xmat[jb].reshape(3, 3), d0.xpos[jb]
# a guide-world point x (trunk frame, mm) maps to jaw_soft frame: x_j = Rj^T (Rtr x + ptr - pj)
R_jt = Rj.T @ Rtr; p_jt = Rj.T @ (ptr - pj)
qj = np.zeros(4); mujoco.mju_mat2Quat(qj, R_jt.ravel())
head_joints_home = {n: float(HOME[n]) if isinstance(HOME, dict) else 0.0 for n in ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll')}
spec = mujoco.MjSpec.from_file(str(ev.MODEL_DIR / 'scene.xml'))
trunk = spec.body('trunk_base'); jaw = spec.body('jaw_soft')
for g in list(spec.geoms):
    if g.name in ('power_support', 'np_f970'):
        spec.delete(g)
HEAD = ('head_bottom', 'head_cap', 'jaw_frame', 'face_panel', 'eye_trim')
for n in HEAD:
    a = spec.add_mesh(name=f'm_{n}', file=str(WORLD / f'{n}.stl'), scale=[mm] * 3)
    jaw.add_geom(name=f'our_{n}', type=mujoco.mjtGeom.mjGEOM_MESH, meshname=a.name, pos=p_jt, quat=qj, contype=0, conaffinity=0, mass=0, group=3)
for n in ('shell_left', 'shell_right', 'rear_pack'):
    a = spec.add_mesh(name=f'm_{n}', file=str(WORLD / f'{n}.stl'), scale=[mm] * 3)
    trunk.add_geom(name=f'ex_{n}', type=mujoco.mjtGeom.mjGEOM_MESH, meshname=a.name, contype=0, conaffinity=0, mass=0, group=3)
BP = MS / 'guide/print/back-plate'
for n in ('rear_frame', 'rear_lid'):
    a = spec.add_mesh(name=f'm_{n}', file=str(BP / f'{n}-world.stl'), scale=[mm] * 3)
    trunk.add_geom(name=f'ex_{n}', type=mujoco.mjtGeom.mjGEOM_MESH, meshname=a.name, contype=0, conaffinity=0, mass=0, group=3)
EXIST = ('shell_left', 'shell_right', 'rear_pack', 'rear_frame', 'rear_lid')
lo, hi = np.array(SADDLE['lo']), np.array(SADDLE['hi'])
trunk.add_geom(name='saddle', type=mujoco.mjtGeom.mjGEOM_BOX, pos=(lo + hi) / 2 * mm, size=(hi - lo) / 2 * mm, contype=0, conaffinity=0, mass=0, group=3)
m = spec.compile(); d = mujoco.MjData(m)
Rt = feet_flat_rot(m, d, NAMES, HOME); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel()); setup(m, d, NAMES, HOME, q); mujoco.mj_forward(m, d)
# check: at HOME our head meshes should coincide with the guide world (head_bottom min z 98.7 in trunk frame)
gid = {n: m.geom(f'our_{n}').id for n in HEAD}; sid = m.geom('saddle').id; eid = [m.geom(f'ex_{n}').id for n in EXIST]
def dist(g, other=None):
    ft = np.zeros(6); return mujoco.mj_geomDistance(m, d, g, sid if other is None else other, 0.2, ft)
def dist_exist(g):
    return min(dist(g, e) for e in eid)
jid = {n: m.joint(n).qposadr[0] for n in ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll')}
rng = {n: np.degrees(m.jnt_range[m.joint(n).id]) for n in jid}
q0 = d.qpos.copy()
print('ranges', {k: v.round(0).tolist() for k, v in rng.items()}, 'HOME head joints', head_joints_home)
print('HOME distances mm', {n: round(dist(gid[n]) * 1000, 1) for n in HEAD})
grid = dict(neck_pitch=np.arange(rng['neck_pitch'][0], rng['neck_pitch'][1] + 1, 5.0), head_pitch=np.arange(rng['head_pitch'][0], rng['head_pitch'][1] + 1, 10.0),
            head_yaw=np.array([-170, -135, -90, -45, 0, 45, 90, 135, 170.0]), head_roll=np.array([-25, 0, 25.0]))
rows = []
for np_, hp, hy, hr in itertools.product(grid['neck_pitch'], grid['head_pitch'], grid['head_yaw'], grid['head_roll']):
    d.qpos[:] = q0
    d.qpos[jid['neck_pitch']] = np.radians(np_); d.qpos[jid['head_pitch']] = np.radians(hp); d.qpos[jid['head_yaw']] = np.radians(hy); d.qpos[jid['head_roll']] = np.radians(hr)
    mujoco.mj_forward(m, d)
    dm = min((dist(gid[n]), n) for n in HEAD)
    de = min(dist_exist(gid[n]) for n in HEAD)
    rows.append((float(np_), float(hp), float(hy), float(hr), round(dm[0] * 1000, 1), dm[1], round(de * 1000, 1)))
rows.sort(key=lambda r: r[4])
print('closest 8 poses (neck_pitch, head_pitch, head_yaw, head_roll, saddle mm, part, existing-parts mm):'); [print(r) for r in rows[:8]]
def band(name, f):
    sel = [r for r in rows if f(r)]
    if not sel: print(name, 'no poses'); return
    mn = min(sel, key=lambda r: r[4]); free = [r for r in sel if r[6] > 0]
    worst_free = min(free, key=lambda r: r[4]) if free else None
    new_hits = [r for r in free if r[4] < 0]
    print(f'{name}: {len(sel)} poses, saddle min {mn[4]} mm at {mn[:4]} (existing {mn[6]}); poses clear of existing parts: {len(free)}, '
          f'of which hit the saddle: {len(new_hits)}; closest clear pose to the saddle {worst_free[4] if worst_free else None} mm at {worst_free[:4] if worst_free else None}')
    return new_hits
band('full joint range', lambda r: True)
# trained command range: deltas up to +-1.10, +-1.10, +-1.40, +-0.31 rad from the default 20/20/0/0 deg (walk_brain HEAD_RANGE)
tr = band('trained head range', lambda r: -43 <= r[0] <= 83 and -43 <= r[1] <= 83 and abs(r[2]) <= 80 and abs(r[3]) <= 18)
if tr:
    print(' new hits inside the trained range (first 10):'); [print(' ', r) for r in sorted(tr, key=lambda r: r[4])[:10]]
band('yaw within +-45, roll 0', lambda r: abs(r[2]) <= 45 and r[3] == 0)
json.dump(dict(saddle=SADDLE, rows=rows), open(HERE / 'head_sweep.json', 'w'))
