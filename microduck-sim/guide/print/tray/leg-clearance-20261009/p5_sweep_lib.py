"""P5 tray decision: adaptive hip-pitch sweep of the pitch-chain leg parts (thigh, hip-pitch motor, knee motor, shin,
ankle motor, ankle, foot) against the printed tray, the OpenRB board and the existing torso parts.
Frames: scene meshes are at MJCF qpos0 in the trunk frame (mm); verified by p5_explore.py (identical bounds).
Usage: p5_sweep.py <walk|full>. Writes p5-sweep-<mode>.json."""
import sys, json, itertools, pickle, time, numpy as np, mujoco, trimesh; sys.path.insert(0, '.')
import legsweep as L
from common import tm
from fastdist import surf_points
from scipy.spatial import cKDTree
GUIDE = '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world/'
LABEL = {'thigh': 'thigh', 'plate': 'thigh plate', 'ring7': 'thigh', 'motor8': 'hip-pitch motor', 'motor7': 'knee motor',
         'lower': 'shin', 'smallring': 'shin', 'washer6': 'shin', 'motor6': 'ankle motor', 'ankle': 'ankle', 'foot': 'foot',
         'right_thigh': 'thigh', 'right_plate': 'thigh plate', 'ring2': 'thigh', 'motor3': 'hip-pitch motor', 'motor2': 'knee motor',
         'right_lower': 'shin', 'right_smallring': 'shin', 'washer1': 'shin', 'motor1': 'ankle motor', 'right_ankle': 'ankle', 'right_foot': 'foot'}
CHAIN = {'left': {'upper_leg_left': ['thigh', 'plate', 'motor8', 'motor7', 'ring7'], 'leg': ['lower', 'motor6', 'smallring', 'washer6'], 'ankle_left': ['ankle', 'foot']},
         'right': {'upper_leg_right': ['right_thigh', 'right_plate', 'motor3', 'motor2', 'ring2'], 'leg_2': ['right_lower', 'motor1', 'right_smallring', 'washer1'], 'ankle_right': ['right_ankle', 'right_foot']}}
SP = 0.6; LSP = 1.4; CAP = 12.0
up = pickle.load(open('upstream_trunk_bodies.pkl', 'rb'))
TG = {'tray': [trimesh.load(GUIDE + 'openrb_tray.stl')], 'board': [trimesh.load(GUIDE + 'openrb-board.stl')],
      'power_support': [tm('power_support')], 'shell_torso_base': [tm('shell_left'), tm('shell_right'), tm('torso_base')],
      'upstream_battery_bay': [trimesh.Trimesh(d['v'], d['f']) for d in up.values()],
      'other_torso': [tm(k) for k in ('regulator_insert', 'regulator', 'imu_clamp', 'imu_cover', 'motor10', 'motor5', 'ring10_torso', 'ring5_torso')]}
TGM = {k: trimesh.util.concatenate(v) for k, v in TG.items()}
TREE = {k: (cKDTree(surf_points(m, SP)), m.bounds[0] - CAP, m.bounds[1] + CAP) for k, m in TGM.items()}
PTS = {}
for side, ch in CHAIN.items():
    P = []; lab = []
    for b, keys in ch.items():
        for k in keys:
            p = surf_points(tm(k), LSP); P.append((b, p)); lab += [k] * len(p)
    PTS[side] = (P, np.array(lab))
def evaluate(side, q):
    Tq = L.body_T(q); P, lab = PTS[side]; Xs = []
    for b, p in P:
        M = Tq[b] @ np.linalg.inv(L.T0[b]); Xs.append(p @ M[:3, :3].T + M[:3, 3])
    X = np.vstack(Xs); out = {}
    for k, (tr, lo, hi) in TREE.items():
        m = np.all((X > lo) & (X < hi), 1)
        if not m.any(): out[k] = (CAP, None); continue
        d, _ = tr.query(X[m], distance_upper_bound=CAP); i = int(np.argmin(d))
        out[k] = (float(min(d[i], CAP)), lab[m][i] if d[i] < CAP else None)
    return out, X
def anchor(jname):
    j = L.M.joint(jname).id; tb = L.M.body('trunk_base').id; R0 = L.D.xmat[tb].reshape(3, 3)
    return R0.T @ (L.D.xanchor[j] - L.D.xpos[tb]) * 1000
W = json.load(open('walk-stats-adopted.json'))['stats']
HOME = {'left_hip_yaw': 0.0, 'left_hip_roll': -0.0873, 'left_hip_pitch': -0.4579, 'left_knee': -0.0049, 'left_ankle': 0.4530,
        'right_hip_yaw': 0.0, 'right_hip_roll': 0.0873, 'right_hip_pitch': 0.4579, 'right_knee': 0.0049, 'right_ankle': -0.4530}
def rng(j): return tuple(float(x) for x in L.M.jnt_range[L.M.joint(j).id])
def sweep(side, fixed, p0, p1):
    J = L.SIDE[side]['joints']; pj = J[2]; sgn = 1.0 if p1 > p0 else -1.0
    first = {k: {'under2': None, 'contact0.3': None} for k in TREE}; p = p0; n = 0; start = None; R = None
    while (p1 - p) * sgn >= -1e-9:
        q = dict(fixed); q[pj] = p; res, X = evaluate(side, q); n += 1
        if R is None: R = float(np.max(np.linalg.norm(X - anchor(pj), axis=1)))
        if start is None: start = {k: round(v[0], 2) for k, v in res.items()}
        for k, (d, part) in res.items():
            for key, thr in (('under2', 2.0), ('contact0.3', 0.3)):
                if first[k][key] is None and d < thr: first[k][key] = dict(pitch=round(p, 4), dMm=round(d, 2), part=LABEL.get(part, part))
        act = [(d, (0.3 if d < 2.0 else 2.0)) for k, (d, _) in res.items() if first[k]['contact0.3'] is None]
        if not act or (first['tray']['contact0.3'] and first['board']['contact0.3']): break
        step = max(0.004, min((d - thr - 1.0) / R for d, thr in act))
        if abs(p - p1) < 1e-9: break
        p = p + sgn * step
        if (p1 - p) * sgn < 0: p = p1
    return dict(first=first, startMm=start, poses=n, RmaxMm=round(R, 1))
