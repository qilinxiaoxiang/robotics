"""Pitch-independent leg parts (hip-yaw bracket + hip-roll motor, hip-roll bracket) vs tray/board/existing torso over
the full MJCF yaw range (0.01 rad) and roll {min, 0, max}. motor10/motor5/ring*_torso excluded (their mounts)."""
import sys, json, numpy as np, pickle, trimesh; sys.path.insert(0, '.')
import legsweep as L
from common import tm
from fastdist import surf_points
from scipy.spatial import cKDTree
GUIDE = '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world/'; SP = 0.5; CAP = 25.0
up = pickle.load(open('upstream_trunk_bodies.pkl', 'rb'))
TG = {'tray': trimesh.load(GUIDE + 'openrb_tray.stl'), 'board': trimesh.load(GUIDE + 'openrb-board.stl'), 'power_support': tm('power_support'),
      'shell_torso_base': trimesh.util.concatenate([tm('shell_left'), tm('shell_right'), tm('torso_base')]),
      'upstream_battery_bay': trimesh.util.concatenate([trimesh.Trimesh(d['v'], d['f']) for d in up.values()]),
      'regulator_imu': trimesh.util.concatenate([tm(k) for k in ('regulator_insert', 'regulator', 'imu_clamp', 'imu_cover')])}
TREE = {k: (cKDTree(surf_points(m, SP)), m.bounds[0] - CAP, m.bounds[1] + CAP) for k, m in TG.items()}
PARTS = {'left': {'yaw2roll': ['yaw', 'motor9', 'ring9', 'passive', 'washer9'], 'hip_l': ['hip', 'ring8']},
         'right': {'bearing_roll': ['right_yaw', 'motor4', 'ring4', 'right_passive', 'washer4'], 'hip_l_2': ['right_hip', 'ring3']}}
W = json.load(open('walk-stats-adopted.json'))['stats']; out = {}
for side, parts in PARTS.items():
    J = L.SIDE[side]['joints']; P = [(b, k, surf_points(tm(k), SP)) for b, ks in parts.items() for k in ks]
    ylo, yhi = L.M.jnt_range[L.M.joint(J[0]).id]; rlo, rhi = L.M.jnt_range[L.M.joint(J[1]).id]; rows = []
    for yv in np.arange(ylo, yhi + 1e-6, 0.01):
        for rv in (rlo, 0.0, rhi):
            Tq = L.body_T({J[0]: float(yv), J[1]: float(rv)}); X = []; lab = []
            for b, k, p in P:
                M = Tq[b] @ np.linalg.inv(L.T0[b]); X.append(p @ M[:3, :3].T + M[:3, 3]); lab += [k] * len(p)
            X = np.vstack(X); lab = np.array(lab); r = dict(yaw=round(float(yv), 3), roll=round(float(rv), 3))
            for t, (tr, lo, hi) in TREE.items():
                m = np.all((X > lo) & (X < hi), 1)
                if not m.any(): r[t] = [CAP, None]; continue
                d, _ = tr.query(X[m], distance_upper_bound=CAP); i = int(np.argmin(d)); r[t] = [round(float(min(d[i], CAP)), 2), str(lab[m][i]) if d[i] < CAP else None]
            rows.append(r)
    def summary(sel):
        return {t: min(([r[t][0], r['yaw'], r['roll'], r[t][1]] for r in sel), key=lambda z: z[0]) for t in TREE}
    wy = (W[J[0]]['min'], W[J[0]]['max'])
    out[side] = dict(fullRangeMin=summary(rows), walkYawRangeMin=summary([r for r in rows if wy[0] - 0.005 <= r['yaw'] <= wy[1] + 0.005]),
                     homeYawMin=summary([r for r in rows if abs(r['yaw']) < 0.006]),
                     firstYawUnder2mmTray=[(r['yaw'], r['roll'], r['tray']) for r in rows if r['tray'][0] < 2.0][:3] + [(r['yaw'], r['roll'], r['tray']) for r in rows if r['tray'][0] < 2.0][-3:],
                     rows=rows)
    print(side, 'full', out[side]['fullRangeMin'], '\n walk', out[side]['walkYawRangeMin'], '\n home', out[side]['homeYawMin'], flush=True)
json.dump(out, open('p5-yawbracket.json', 'w'), indent=1)
