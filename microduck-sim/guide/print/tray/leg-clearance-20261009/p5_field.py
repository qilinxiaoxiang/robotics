"""1 mm unsigned distance fields (EDT of surface voxels) for tray, board and existing torso parts; adaptive hip-pitch sweeps
of pitch-chain leg parts (1 mm surface samples, trilinear lookup). Field error <= ~0.9 mm; governing boundaries are refined
afterwards by exact point-to-mesh distance. Writes p5-field.json."""
import sys, json, itertools, time, pickle, numpy as np, trimesh; sys.path.insert(0, '.')
from scipy import ndimage
import legsweep as L
from common import tm
from fastdist import surf_points
GUIDE = '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world/'
up = pickle.load(open('upstream_trunk_bodies.pkl', 'rb'))
TG = {'tray': trimesh.load(GUIDE + 'openrb_tray.stl'), 'board': trimesh.load(GUIDE + 'openrb-board.stl'), 'power_support': tm('power_support'),
      'shell_torso_base': trimesh.util.concatenate([tm('shell_left'), tm('shell_right'), tm('torso_base')]),
      'upstream_battery_bay': trimesh.util.concatenate([trimesh.Trimesh(d['v'], d['f']) for d in up.values()]),
      'other_torso': trimesh.util.concatenate([tm(k) for k in ('regulator_insert', 'regulator', 'imu_clamp', 'imu_cover', 'motor10', 'motor5', 'ring10_torso', 'ring5_torso')])}
VS = 1.0; LO = np.array([-125., -75., -125.]); HI = np.array([45., 75., 45.]); SH = np.ceil((HI - LO) / VS).astype(int) + 1
F = {}
for k, m in TG.items():
    g = np.ones(SH, bool); p = surf_points(m, 0.4); idx = np.round((p - LO) / VS).astype(int); ok = np.all((idx >= 0) & (idx < SH), 1); idx = idx[ok]
    g[idx[:, 0], idx[:, 1], idx[:, 2]] = False; F[k] = ndimage.distance_transform_edt(g, sampling=VS).astype(np.float32); del g
CHAIN = {'left': {'upper_leg_left': ['thigh', 'plate', 'motor8', 'motor7', 'ring7'], 'leg': ['lower', 'motor6', 'smallring', 'washer6'], 'ankle_left': ['ankle', 'foot']},
         'right': {'upper_leg_right': ['right_thigh', 'right_plate', 'motor3', 'motor2', 'ring2'], 'leg_2': ['right_lower', 'motor1', 'right_smallring', 'washer1'], 'ankle_right': ['right_ankle', 'right_foot']}}
LAB = {'thigh': 'thigh', 'plate': 'thigh', 'ring7': 'thigh', 'motor8': 'hip-pitch motor', 'motor7': 'knee motor', 'lower': 'shin', 'smallring': 'shin', 'washer6': 'shin', 'motor6': 'ankle motor', 'ankle': 'ankle', 'foot': 'foot'}
for a, b in list(LAB.items()):
    LAB[{'thigh': 'right_thigh', 'plate': 'right_plate', 'ring7': 'ring2', 'motor8': 'motor3', 'motor7': 'motor2', 'lower': 'right_lower', 'smallring': 'right_smallring', 'washer6': 'washer1', 'motor6': 'motor1', 'ankle': 'right_ankle', 'foot': 'right_foot'}[a]] = b
PTS = {}
for side, ch in CHAIN.items():
    P = []; lab = []
    for b, keys in ch.items():
        for k in keys: p = surf_points(tm(k), 1.0); P.append((b, p)); lab += [LAB[k]] * len(p)
    PTS[side] = (P, np.array(lab))
def evaluate(side, q):
    Tq = L.body_T(q); P, lab = PTS[side]; X = np.vstack([p @ (Tq[b] @ np.linalg.inv(L.T0[b]))[:3, :3].T + (Tq[b] @ np.linalg.inv(L.T0[b]))[:3, 3] for b, p in P])
    c = ((X - LO) / VS).T; out = {}
    inside = np.all((X > LO) & (X < HI), 1)
    for k, f in F.items():
        d = np.full(len(X), 99.0); d[inside] = ndimage.map_coordinates(f, c[:, inside], order=1, mode='nearest'); i = int(np.argmin(d)); out[k] = (float(d[i]), str(lab[i]))
    return out, X
def anchor(j):
    jid = L.M.joint(j).id; tb = L.M.body('trunk_base').id; R0 = L.D.xmat[tb].reshape(3, 3); return R0.T @ (L.D.xanchor[jid] - L.D.xpos[tb]) * 1000
W = json.load(open('walk-stats-adopted.json'))['stats']
HOME = {'left_hip_yaw': 0.0, 'left_hip_roll': -0.0873, 'left_hip_pitch': -0.4579, 'left_knee': -0.0049, 'left_ankle': 0.4530,
        'right_hip_yaw': 0.0, 'right_hip_roll': 0.0873, 'right_hip_pitch': 0.4579, 'right_knee': 0.0049, 'right_ankle': -0.4530}
def rng(j): return tuple(float(x) for x in L.M.jnt_range[L.M.joint(j).id])
def sweep(side, fixed, p0, p1):
    pj = L.SIDE[side]['joints'][2]; sgn = 1.0 if p1 > p0 else -1.0; first = {k: None for k in F}; p = p0; R = None; start = None
    while True:
        q = dict(fixed); q[pj] = p; res, X = evaluate(side, q)
        if R is None: R = float(np.max(np.linalg.norm(X - anchor(pj), axis=1))); start = {k: round(v[0], 2) for k, v in res.items()}
        for k, (d, part) in res.items():
            if first[k] is None and d < 2.0: first[k] = [round(p, 3), part]
        act = [d for k, (d, _) in res.items() if first[k] is None]
        if not act or abs(p - p1) < 1e-9: break
        p = p + sgn * max(0.003, (min(act) - 2.0 - 0.9) / R)
        if (p1 - p) * sgn < 0: p = p1
    return first, start
if __name__ == '__main__':
    out = {}; t0 = time.time()
    for mode in ('walk', 'full'):
        out[mode] = {}
        for side in ('left', 'right'):
            y, r, pj, kj, aj = L.SIDE[side]['joints']; lim = rng(pj)[1] if side == 'left' else rng(pj)[0]
            if mode == 'walk':
                Y = np.linspace(W[y]['min'], W[y]['max'], 12); R_ = (W[r]['min'], HOME[r], W[r]['max']); K = {'straight': 0.0, 'walkMin': W[kj]['min'], 'walkMax': W[kj]['max']}; A = (W[aj]['min'], HOME[aj], W[aj]['max'])
            else:
                Y = np.linspace(*rng(y), 13); R_ = (rng(r)[0], HOME[r], rng(r)[1]); K = {'straight': 0.0, 'home': HOME[kj]}; A = (HOME[aj],)
            rows = []
            for yy, rr, (kn, kv), aa in itertools.product(Y, R_, K.items(), A):
                first, start = sweep(side, {y: float(yy), r: float(rr), kj: kv, aj: float(aa)}, HOME[pj], lim)
                rows.append(dict(yaw=round(float(yy), 3), roll=round(float(rr), 3), knee=kn, ankle=round(float(aa), 3), first=first, startMm=start))
            out[mode][side] = rows
            print(mode, side, len(rows), 'sweeps', round(time.time() - t0), 's', flush=True)
    json.dump(out, open('p5-field.json', 'w'), indent=1)
