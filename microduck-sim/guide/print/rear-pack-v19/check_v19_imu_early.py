"""BNO085 fitted on the bench, so it is present from pack-in on: straight drivers (dia 3, 5, 6, 8, 70 mm) for the four hip-yaw case screws of
torso-fasten against the board model and its two M2 x 4. Writes check_v19_imu_early.json."""
import sys, json
from pathlib import Path
import numpy as np
V19 = Path(__file__).resolve().parent
sys.path.insert(0, str(V19.parent / 'rear-pack'))
import pack_lib as P
G = V19.parent.parent
IMU = P.mesh_to_m(P.imu_mesh())
SCR = P.union([P.cyl_y(2.0, -0.695, 0.805, x, z) + P.cyl_y(1.0, -4.695, -0.695, x, z) for (x, z) in ((-15.46, 8.04), (-15.46, 28.36))])
B = IMU + SCR
fast = {f['id']: f for f in json.load(open(G / 'content' / 'fasteners.json'))['screws']}
out = {}
for sid in ('S10-case-072', 'S05-case-076', 'S10-case-069', 'S05-case-074'):
    f = fast[sid]; c = np.array(f['center'], float); a = np.array(f['axis'], float)
    top = c - a * f['headHeightMm']
    row = {}
    for dia in (3.0, 5.0, 6.0, 8.0):
        z0, z1 = sorted([top[2], top[2] - a[2] * 70.0])
        sh = P.cyl_z(dia / 2, z0, z1, c[0], c[1])
        row[f'dia{dia:g}'] = dict(overlapMm3=round(float((sh ^ B).volume()), 3), gapMm=round(float(sh.min_gap(B, 6.0)), 3))
    out[sid] = row
print(json.dumps(out))
json.dump(out, open(V19 / 'check_v19_imu_early.json', 'w'), indent=1)
