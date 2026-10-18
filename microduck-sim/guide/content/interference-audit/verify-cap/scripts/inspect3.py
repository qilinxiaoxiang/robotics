"""Rear obstacles under the Pi rails: for each y slice, the largest x of obstacle material at or above height z (descent shadow)."""
import json, sys
import numpy as np
sys.path.insert(0, __import__('os').path.dirname(__file__))
from vc import *

S, prov = solids()
REAR = ['jaw_support', 'motor15', 'jaw_frame', 'mouth_sliding_ring', 'head_bottom', 'motor14', 'head_yaw_link', 'lower_pad',
        'head_roll_ring_b', 'motor13']
out = {}
ys = [-32.2, -31.0, -29.0, -27.4, -26.0, -25.4, -20.0, -10.0, 0.0, 10.0, 20.0, 25.4, 26.0, 27.4, 29.0, 31.0, 32.2]
zs = np.arange(112.0, 150.01, 1.0)
for k in REAR:
    m = mf_to_tm(S[k])
    prof = {}
    for y in ys:
        sec = m.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
        if sec is None:
            continue
        P = np.vstack(sec.discrete)
        row = {}
        for z0 in zs:
            sel = P[:, 2] >= z0
            if sel.any():
                row[f'{z0:.0f}'] = round(float(P[sel, 0].max()), 3)
        if row:
            prof[str(y)] = row
    out[k] = prof
json.dump(out, open(HERE / 'inspect3.json', 'w'), indent=1)
for k, prof in out.items():
    print(k)
    for y, row in prof.items():
        items = list(row.items())
        print('  y', y, ' '.join(f'{z}:{x}' for z, x in items[::3]))
