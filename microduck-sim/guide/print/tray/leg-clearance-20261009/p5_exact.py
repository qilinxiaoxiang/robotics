"""Exact point-to-mesh check (leg samples 0.3 mm, nearest-candidate refinement) at governing poses."""
import sys, json, numpy as np, trimesh; sys.path.insert(0, '.')
import legsweep as L
from common import tm
from fastdist import surf_points
from scipy.spatial import cKDTree
G = '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world/'
T = {'tray': trimesh.load(G + 'openrb_tray.stl'), 'board': trimesh.load(G + 'openrb-board.stl'), 'power_support': tm('power_support'),
     'shell_torso_base': trimesh.util.concatenate([tm('shell_left'), tm('shell_right'), tm('torso_base')])}
CH = {'left': {'upper_leg_left': ['thigh', 'plate', 'motor8', 'motor7', 'ring7'], 'leg': ['lower', 'motor6', 'smallring', 'washer6'], 'ankle_left': ['ankle', 'foot']},
      'right': {'upper_leg_right': ['right_thigh', 'right_plate', 'motor3', 'motor2', 'ring2'], 'leg_2': ['right_lower', 'motor1', 'right_smallring', 'washer1'], 'ankle_right': ['right_ankle', 'right_foot']}}
TS = {k: cKDTree(surf_points(m, 0.5)) for k, m in T.items()}
def exact(side, q):
    Tq = L.body_T(q); out = {}
    parts = [(k, tm(k), Tq[b] @ np.linalg.inv(L.T0[b])) for b, ks in CH[side].items() for k in ks]
    for t, m in T.items():
        best = (99, None)
        for k, pm, M in parts:
            pm = pm.copy(); pm.apply_transform(M)
            lo = m.bounds[0] - 6; hi = m.bounds[1] + 6
            if np.any(pm.bounds[1] < lo) or np.any(pm.bounds[0] > hi): continue
            X = surf_points(pm, 0.3, (lo, hi))
            if not len(X): continue
            d, _ = TS[t].query(X, distance_upper_bound=8); idx = np.argsort(d)[:400]; idx = idx[np.isfinite(d[idx])]
            if not len(idx): continue
            _, dd, _ = trimesh.proximity.closest_point(m, X[idx]); i = int(np.argmin(dd))
            if dd[i] < best[0]: best = (round(float(dd[i]), 2), k)
        out[t] = best
    return out
cases = {
 'walkFrame54475_left_closestToTray': ('left', {'left_hip_yaw': -0.216, 'left_hip_roll': -0.175, 'left_hip_pitch': -0.207, 'left_knee': -0.021, 'left_ankle': 0.206}),
 'firstNew_left_straight_p0.475': ('left', {'left_hip_yaw': -0.12, 'left_hip_roll': -0.0873, 'left_hip_pitch': 0.475, 'left_knee': 0.0, 'left_ankle': 0.453}),
 'firstNew_left_straight_p0.45': ('left', {'left_hip_yaw': -0.12, 'left_hip_roll': -0.0873, 'left_hip_pitch': 0.45, 'left_knee': 0.0, 'left_ankle': 0.453}),
 'firstNew_left_kneeWalkMin_p0.15': ('left', {'left_hip_yaw': -0.16, 'left_hip_roll': -0.0873, 'left_hip_pitch': 0.15, 'left_knee': -0.487, 'left_ankle': 0.453}),
 'walkMaxPitch_left_p0.166_yaw-0.16_kneeMin': ('left', {'left_hip_yaw': -0.16, 'left_hip_roll': -0.0873, 'left_hip_pitch': 0.166, 'left_knee': -0.487, 'left_ankle': 0.453}),
 'firstNew_right_straight_p-0.475': ('right', {'right_hip_yaw': 0.12, 'right_hip_roll': 0.0873, 'right_hip_pitch': -0.475, 'right_knee': 0.0, 'right_ankle': -0.453}),
}
res = {}
for n, (s, q) in cases.items():
    res[n] = dict(q=q, exactMm=exact(s, q)); print(n, res[n]['exactMm'], flush=True)
json.dump(res, open('p5-exact.json', 'w'), indent=1)
