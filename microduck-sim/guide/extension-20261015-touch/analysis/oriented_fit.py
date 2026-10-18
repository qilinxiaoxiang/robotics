"""Oriented fit of board-sized boxes in the free head space from head_space.py.

The free grid is rotated (nearest neighbour) for each orientation on a 15 degree grid of roll, pitch and yaw; a box
fits where a box-sum over the rotated grid equals the box volume. Output: oriented_fit.json.
"""
import json, itertools
from pathlib import Path
import numpy as np
from scipy import ndimage
from scipy.spatial.transform import Rotation as R

HERE = Path(__file__).resolve().parent
d = np.load(HERE / 'head_space.npz'); free, lo = d['free'].astype(np.float32), d['lo']
c = (np.array(free.shape) - 1) / 2
BOXES = {'mpr121_bare_33x19x4': (33, 19, 4), 'mpr121_plug_41x19x6': (41, 19, 6), 'cap1188_42x18x4': (42, 18, 4),
         'ads1115_bare_26x18x4': (26, 18, 4), 'ads1115_plug_34x18x6': (34, 18, 6),
         'xiao_22x18x5': (22, 18, 5), 'xiao_wires_26x18x5': (26, 18, 5)}
angles = np.arange(-60, 61, 15)
out = {}
for name, dims in BOXES.items():
    hits = []
    for yaw in (0, 30, 60, 90, 120, 150):
        for roll, pitch in itertools.product(angles, angles):
            rot = R.from_euler('zyx', [yaw, pitch, roll], degrees=True)
            M = rot.as_matrix()                      # box frame -> world
            # sample world at  x_world = M @ x_box ; affine_transform maps output index o -> input M@(o-c)+c
            g = ndimage.affine_transform(free, M, offset=c - M @ c, order=0, mode='constant', cval=0)
            s = ndimage.uniform_filter(g, size=dims, mode='constant') * np.prod(dims)
            ok = s > np.prod(dims) - 0.5
            if ok.any():
                o = np.argwhere(ok)
                w = (M @ (o - c).T).T + c + lo + 0.5
                hits.append({'yaw_pitch_roll': [int(yaw), int(pitch), int(roll)], 'n': int(len(o)),
                             'centre_mean': np.round(w.mean(0), 1).tolist(),
                             'x': [round(w[:, 0].min()), round(w[:, 0].max())], 'y': [round(w[:, 1].min()), round(w[:, 1].max())],
                             'z': [round(w[:, 2].min()), round(w[:, 2].max())]})
    out[name] = {'dims': dims, 'orientations_fitting': len(hits), 'best': sorted(hits, key=lambda h: -h['n'])[:5]}
    print(name, dims, 'orientations fitting:', len(hits), out[name]['best'][:2])
(HERE / 'oriented_fit.json').write_text(json.dumps(out, indent=1))
