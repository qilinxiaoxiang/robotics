#!/usr/bin/env python3
"""Occupancy grid of the neck + head region at q = 0 (0.5 mm voxels), from exact manifold slices of the closed audit solids.

Every voxel centre is classified by slicing each solid at the voxel-centre z (manifold3d Manifold.slice) and testing the
centre against the section polygons (even-odd). The grid stores, per voxel, the index of one part that contains it
(0 = free). The notch-less study cap replaces the V1.8 cap (pass 'notch' to use the V1.8 cap instead; pass 'cables' to add the existing neck/head cables as obstacles:
the servo-chain kit cables and the camera ribbon, drawn as tubes of the guide radius).
Writes SCRATCH/occ-<cap>.npz. Used only to search for corridors; every reported clearance is re-measured exactly
(point-to-mesh distance) in corridor.py.
"""
import json
import sys
import time

import numpy as np
from matplotlib.path import Path as MPath

sys.path.insert(0, __import__('os').path.dirname(__file__))
from nr_lib import SCRATCH, body_of, ia_lib, load_solid  # noqa: E402

CAP = 'notch' if 'notch' in sys.argv[1:] else 'nonotch'
WITH_CABLES = 'cables' in sys.argv[1:]
PITCH = 0.5
LO = np.array([-40.0, -50.0, 20.0])
HI = np.array([96.0, 50.0, 160.0])
shape = np.round((HI - LO) / PITCH).astype(int) + 1
xs, ys, zs = (LO[i] + PITCH * np.arange(shape[i]) for i in range(3))

g = ia_lib.load_guide()
keys = [p['key'] for p in g['parts'] if body_of(p['key']) is not None]
keys = [k for k in keys if k != 'head_cap'] + ['head_cap_nonotch' if CAP == 'nonotch' else 'head_cap']
occ = np.zeros(tuple(shape), np.uint8)
names = ['free']
t0 = time.time()
X, Y = np.meshgrid(xs, ys, indexing='ij')
for key in keys:
    v, f = load_solid(key)
    if v[:, 2].max() < LO[2] or v[:, 2].min() > HI[2]:
        continue
    man = ia_lib.to_manifold(v, f)
    names.append(key)
    idx = len(names) - 1
    bl, bh = v.min(0), v.max(0)
    i0 = max(0, int(np.floor((bl[0] - LO[0]) / PITCH))); i1 = min(shape[0], int(np.ceil((bh[0] - LO[0]) / PITCH)) + 1)
    j0 = max(0, int(np.floor((bl[1] - LO[1]) / PITCH))); j1 = min(shape[1], int(np.ceil((bh[1] - LO[1]) / PITCH)) + 1)
    pts = np.stack([X[i0:i1, j0:j1].ravel(), Y[i0:i1, j0:j1].ravel()], 1)
    for k, z in enumerate(zs):
        if z < bl[2] or z > bh[2]:
            continue
        polys = man.slice(float(z)).to_polygons()
        if not polys:
            continue
        inside = np.zeros(len(pts), bool)
        for poly in polys:
            poly = np.asarray(poly)
            if len(poly) < 3:
                continue
            inside ^= MPath(poly).contains_points(pts)
        if inside.any():
            sub = occ[i0:i1, j0:j1, k].ravel()
            sub[inside & (sub == 0)] = idx
            occ[i0:i1, j0:j1, k] = sub.reshape(i1 - i0, j1 - j0)
if WITH_CABLES:
    from nr_lib import cable_tubes
    from scipy.spatial import cKDTree
    for cid, pts, r in cable_tubes():
        names.append('cable:' + cid)
        idx = len(names) - 1
        tree = cKDTree(pts)
        bl, bh = pts.min(0) - r - 1, pts.max(0) + r + 1
        sl = []
        for i in range(3):
            a = max(0, int(np.floor((bl[i] - LO[i]) / PITCH))); b = min(shape[i], int(np.ceil((bh[i] - LO[i]) / PITCH)) + 1)
            sl.append(slice(a, b))
        G = np.stack(np.meshgrid(xs[sl[0]], ys[sl[1]], zs[sl[2]], indexing='ij'), -1).reshape(-1, 3)
        dd, _ = tree.query(G, distance_upper_bound=r + 0.3)
        sub = occ[tuple(sl)].ravel()
        sub[(dd <= r) & (sub == 0)] = idx
        occ[tuple(sl)] = sub.reshape(occ[tuple(sl)].shape)
print(f'{len(names) - 1} parts sliced in {time.time() - t0:.1f}s; occupied fraction {(occ > 0).mean():.3f}', flush=True)
TAG = CAP + ('-cables' if WITH_CABLES else '')
np.savez_compressed(SCRATCH / f'occ-{TAG}.npz', occ=occ, lo=LO, pitch=PITCH, names=np.array(names))
print('wrote', SCRATCH / f'occ-{TAG}.npz')
