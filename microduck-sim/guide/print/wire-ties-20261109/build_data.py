"""Tie points and wire lengths for the head-to-saddle cables, plus the 3D data of wire-ties.html.
Same as-built MJCF and HOME mapping as neck-exit-20261023/cable_sweep.py. Writes data.json and sweep.json.
~/.venvs/microduck-dyn/bin/python build_data.py"""
import sys, json, base64, itertools
from pathlib import Path
import numpy as np, mujoco

HERE = Path(__file__).resolve().parent
MS = HERE.parents[2]
WORLD = HERE.parent / 'world'
sys.path.insert(0, str(MS / 'hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014'))
from static_gap import NAMES, HOME, feet_flat_rot, setup
import evaluate_delay as ev

# Tie points, guide trunk frame at HOME, mm. +y is the robot's left.
TIES = {
    'T1': ('jaw_soft', (10.0, 18.5, 98.7)),    # inside-head tie at the left-rear exit (D-029), bottom of the head floor
    'T2': ('neck', (11.0, 16.8, 57.0)),        # left face of the neck link, the two-servo waist
    'T3': ('trunk_base', (-4.2, 16.0, 56.0)),  # saddle front wall, outer face (wall x -5, Dupont bundle)
    'T4': ('trunk_base', (-9.0, 37.2, 54.0)),  # saddle left wall outer face, front end (bulge y 36.4, USB cable)
    'T5': ('trunk_base', (-40.0, 35.2, 54.0)), # saddle left wall outer face, rear end (wall y 34.4, USB cable)
}
SPANS = [('T1', 'T2'), ('T2', 'T3'), ('T2', 'T4')]
# Wire length to leave in each moving span: the longest straight distance over the joint limits, about +10 % for the bends, rounded up
WIRE = {('T1', 'T2'): 75.0, ('T2', 'T3'): 70.0, ('T2', 'T4'): 75.0}

PARTS = [  # file, body, colour, opacity
    ('shell_left', 'trunk_base', 0xE9E7DF, 1), ('shell_right', 'trunk_base', 0xE9E7DF, 1),
    ('saddle_body', 'trunk_base', 0xE8782B, 1), ('sd_a7z_pcb', 'trunk_base', 0x2F4F3E, 1),
    ('sd_heatsink_6530b', 'trunk_base', 0x8C9196, 1), ('sd_dupont_housings', 'trunk_base', 0x26282B, 1),
    ('duallock_plate', 'trunk_base', 0xE8782B, 1),
    ('battery_backpack_frame', 'trunk_base', 0xE8782B, 0.28), ('battery_backpack_cap', 'trunk_base', 0xE8782B, 0.28),
    ('rear_pack', 'trunk_base', 0xF2C230, 0.28),
    ('head_bottom', 'jaw_soft', 0xF2C230, 1), ('jaw_support', 'jaw_soft', 0x3A3C40, 1), ('head_cap', 'jaw_soft', 0xE9E7DF, 0.32),
    ('face_panel', 'jaw_soft', 0xE9E7DF, 0.32),
]
BODIES = ['trunk_base', 'neck', 'neck_pitch', 'yaw_roll_motion', 'jaw_soft']
GRID = 0.9  # vertex-clustering cell, mm

m = mujoco.MjModel.from_xml_path(str(ev.MODEL_DIR / 'scene.xml')); d = mujoco.MjData(m)
Rt = feet_flat_rot(m, d, NAMES, HOME); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel()); setup(m, d, NAMES, HOME, q); mujoco.mj_forward(m, d)
tb = m.body('trunk_base').id
Rb0, pb0 = d.xmat[tb].reshape(3, 3).copy(), d.xpos[tb].copy()
q0 = d.qpos.copy()
J = {n: m.joint(n).qposadr[0] for n in ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll')}
rng = {n: np.degrees(m.jnt_range[m.joint(n).id]) for n in J}
to_w = lambda x: Rb0 @ (np.asarray(x, float) * 1e-3) + pb0

def body_T(name):
    """4x4 of a body in the guide frame (mm) at the current pose; the trunk stays put."""
    Rb, pb = d.xmat[tb].reshape(3, 3), d.xpos[tb]
    i = m.body(name).id
    T = np.eye(4); T[:3, :3] = Rb.T @ d.xmat[i].reshape(3, 3); T[:3, 3] = (Rb.T @ (d.xpos[i] - pb)) * 1e3
    return T

T0 = {b: body_T(b) for b in BODIES}
LOC = {k: np.linalg.inv(T0[b]) @ np.r_[x, 1.0] for k, (b, x) in TIES.items()}
axis_loc = np.linalg.inv(T0['neck']) @ np.r_[18.0, 0.0, 70.0, 1.0]

def tie(k):
    return (body_T(TIES[k][0]) @ LOC[k])[:3]

def set_pose(np_=None, hp=None, hy=None, hr=None):
    d.qpos[:] = q0
    for n, v in zip(J, (np_, hp, hy, hr)):
        if v is not None: d.qpos[J[n]] = np.radians(v)
    mujoco.mj_kinematics(m, d)

# 1. sweep every span over the joint limits (same grid as cable_sweep.py)
set_pose()
home = {s: float(np.linalg.norm(tie(s[0]) - tie(s[1]))) for s in SPANS}
print('HOME joints deg', {n: round(float(np.degrees(q0[a])), 1) for n, a in J.items()})
grid = (np.arange(rng['neck_pitch'][0], rng['neck_pitch'][1] + 1, 5.0), np.arange(rng['head_pitch'][0], rng['head_pitch'][1] + 1, 10.0),
        np.array([-170, -135, -90, -80, -45, 0, 45, 80, 90, 135, 170.0]), np.array([-25, -18, 0, 18, 25.0]))
poses, rows = [], {s: [] for s in SPANS}
for t in itertools.product(*grid):
    set_pose(*t); poses.append(t)
    P = {k: tie(k) for k in TIES}
    for s in SPANS: rows[s].append(float(np.linalg.norm(P[s[0]] - P[s[1]])))
poses = np.array(poses)
used = (np.abs(poses[:, 2]) <= 80) & (np.abs(poses[:, 3]) <= 18)
sweep = {}
for s in SPANS:
    a = np.array(rows[s])
    i = int(a.argmax())
    sweep['-'.join(s)] = dict(homeMm=round(home[s], 1), minMm=round(float(a.min()), 1), maxLimitsMm=round(float(a.max()), 1),
                              maxYaw80Roll18Mm=round(float(a[used].max()), 1), maxPoseDeg=poses[i].round().tolist(), wireMm=WIRE[s])
    print(s, sweep['-'.join(s)])
    assert WIRE[s] >= a.max() * 1.05, f'wire {s} too short for the joint limits'
(HERE / 'sweep.json').write_text(json.dumps(sweep, indent=1) + '\n')

# 2. the poses the page can show
POSES = [('stand', '站立', None, None, None, None), ('bow', '低头到底', -90.0, 0.0, 0.0, 0.0), ('pick', '捡球弯腰', -72.5, -14.7, 0.0, 0.0),
         ('back', '后仰', 32.0, 0.0, 0.0, 0.0), ('left', '头左转 80°', None, None, 80.0, None), ('right', '头右转 80°', None, None, -80.0, None),
         ('worst', '低头加右转', -90.0, 0.0, -80.0, -18.0)]

def bez(a, b, dirv, h, n=28):
    c1, c2 = a + (b - a) * .2 + dirv * h, a + (b - a) * .8 + dirv * h
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t ** 2 * c2 + t ** 3 * b

def curve(a, b, dirv, L):
    plen = lambda p: float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())
    lo, hi = 0.0, 200.0
    for _ in range(40):
        h = (lo + hi) / 2
        if plen(bez(a, b, dirv, h)) < L: lo = h
        else: hi = h
    return bez(a, b, dirv, lo)

out_p = []
for key, label, *a in POSES:
    set_pose(*a)
    P = {k: tie(k) for k in TIES}
    c = (body_T('neck') @ axis_loc)[:3]
    mid = (P['T1'] + P['T2']) / 2 - c; mid[2] = 0; up = mid / (np.linalg.norm(mid) + 1e-9)
    side = np.array([0.15, 1.0, 0.1]); side /= np.linalg.norm(side)
    wires = {'T1-T2': curve(P['T1'], P['T2'], up, WIRE[('T1', 'T2')]), 'T2-T3': curve(P['T2'], P['T3'], side, WIRE[('T2', 'T3')]),
             'T2-T4': curve(P['T2'], P['T4'], side, WIRE[('T2', 'T4')])}
    Ts = {b: (body_T(b) @ np.linalg.inv(T0[b])) for b in BODIES}
    out_p.append(dict(key=key, label=label, T={b: Ts[b].ravel().round(5).tolist() for b in BODIES},
                      ties={k: P[k].round(2).tolist() for k in P}, dist={'-'.join(s): round(float(np.linalg.norm(P[s[0]] - P[s[1]])), 1) for s in SPANS},
                      wires={k: v.round(2).tolist() for k, v in wires.items()}))

# 3. meshes in the guide frame at HOME, reduced by vertex clustering
def cluster(tri):
    v = tri.reshape(-1, 3)
    cell = np.round(v / GRID).astype(np.int64)
    _, inv = np.unique(cell, axis=0, return_inverse=True); inv = inv.ravel()
    n = inv.max() + 1
    p = np.zeros((n, 3)); np.add.at(p, inv, v); p /= np.bincount(inv, minlength=n)[:, None]
    f = inv.reshape(-1, 3)
    f = f[(f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2])]
    f = np.unique(f, axis=0) if len(f) else f
    return p, f

def load_stl(path):
    r = path.read_bytes(); n = int.from_bytes(r[80:84], 'little')
    a = np.frombuffer(r[84:], dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', 9), ('a', '<u2')]), count=n)
    return a['v'].reshape(-1, 3, 3).astype(float)

meshes = []
def add(name, body, color, opacity, tri):
    p, f = cluster(tri)
    meshes.append(dict(name=name, body=body, color=color, opacity=opacity, p=base64.b64encode(p.astype('<f4').tobytes()).decode(), f=base64.b64encode(f.astype('<u4').tobytes()).decode()))
    return len(f)

set_pose()
tot = 0
for name, body, color, op in PARTS:
    tot += add(name, body, color, op, load_stl(WORLD / f'{name}.stl'))
Rb, pb = d.xmat[tb].reshape(3, 3), d.xpos[tb]
for bn, col in (('neck', 0x3A3C40), ('neck_pitch', 0x55585E), ('yaw_roll_motion', 0x55585E)):
    i = m.body(bn).id
    for g in range(m.ngeom):
        if m.geom_bodyid[g] != i or m.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH or m.geom_group[g] > 2: continue
        me = m.geom_dataid[g]
        va, vn, fa, fn = m.mesh_vertadr[me], m.mesh_vertnum[me], m.mesh_faceadr[me], m.mesh_facenum[me]
        w = (d.geom_xmat[g].reshape(3, 3) @ m.mesh_vert[va:va + vn].T).T + d.geom_xpos[g]
        G = (Rb.T @ (w - pb).T).T * 1e3
        tot += add(f'{bn}_{g}', bn, col, 1, G[m.mesh_face[fa:fa + fn]])
print('triangles', tot, 'meshes', len(meshes))
data = dict(poses=out_p, meshes=meshes, sweep=sweep)
(HERE / 'data.json').write_text(json.dumps(data, separators=(',', ':')))
print('data.json MB', round((HERE / 'data.json').stat().st_size / 1e6, 2))
