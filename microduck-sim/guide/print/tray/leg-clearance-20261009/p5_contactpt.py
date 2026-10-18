import sys, json, numpy as np, trimesh; sys.path.insert(0, '.')
import legsweep as L
from common import tm
from fastdist import surf_points
G = '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world/'
tray = trimesh.load(G + 'openrb_tray.stl'); ps = tm('power_support')
cases = {'walkEnvelopeWorst_p0.166': ('left', {'left_hip_yaw': -0.16, 'left_hip_roll': -0.0873, 'left_hip_pitch': 0.166, 'left_knee': -0.487, 'left_ankle': 0.453}, 'ankle_left', 'foot'),
         'straight_p0.45': ('left', {'left_hip_yaw': -0.12, 'left_hip_roll': -0.0873, 'left_hip_pitch': 0.45, 'left_knee': 0.0, 'left_ankle': 0.453}, 'ankle_left', 'foot'),
         'walkFrame54475': ('left', {'left_hip_yaw': -0.216, 'left_hip_roll': -0.175, 'left_hip_pitch': -0.207, 'left_knee': -0.021, 'left_ankle': 0.206}, 'leg', 'lower')}
out = {}
for n, (s, q, b, k) in cases.items():
    Tq = L.body_T(q); m = tm(k); m.apply_transform(Tq[b] @ np.linalg.inv(L.T0[b]))
    X = surf_points(m, 0.3, (tray.bounds[0] - 4, tray.bounds[1] + 4))
    cp, d, _ = trimesh.proximity.closest_point(tray, X); i = np.argsort(d)[:1][0]
    near = cp[d < d[i] + 1.0]
    cp2, d2, _ = trimesh.proximity.closest_point(ps, X); j = int(np.argmin(d2))
    out[n] = dict(trayMm=round(float(d[i]), 2), trayPoint=cp[i].round(1).tolist(), legPoint=X[i].round(1).tolist(), trayPatchWithin1mm=[near.min(0).round(1).tolist(), near.max(0).round(1).tolist()],
                  psMm=round(float(d2[j]), 2), psPoint=cp2[j].round(1).tolist())
    print(n, out[n], flush=True)
json.dump(out, open('p5-contactpt.json', 'w'), indent=1)
