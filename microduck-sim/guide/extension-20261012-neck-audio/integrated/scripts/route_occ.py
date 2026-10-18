#!/usr/bin/env python3
"""Occupancy grid of the closed integrated head for routing the neck bundle (0.5 mm voxels, head frame).

Every solid of route_scene.scene() is sliced exactly (manifold3d Manifold.slice at each voxel-centre z, even-odd point
test) at every sampled pose of its sweep (jaw 0..40 deg in 2 deg steps; yaw body over roll -25..+25 deg in 2.5 deg
steps), so the grid holds the union of everything a wire inside the head must avoid. A second mask marks the cap
descent: every voxel that a cap-mounted solid passes through while the cap is lowered the last 40 mm (cap-mounted
occupancy extended 40 mm upward). A wire held on the lower head must stay outside that mask; a wire held on the cap
moves with it. The 8 bundle housings are kept in the grid as obstacles (the route ends in front of their wire exits).
Writes SCRATCH/route-occ.npz (labels: index into names, 0 = free; masks capMounted, descent).
"""
import time

import numpy as np
from matplotlib.path import Path as MPath

import int_lib as L
from route_scene import poses, scene

PITCH = 0.5
LO = np.array([-40.0, -50.0, 96.0])
HI = np.array([96.0, 50.0, 162.0])
DESCENT_MM = 40.0


def main():
    t0 = time.time()
    shape = np.round((HI - LO) / PITCH).astype(int) + 1
    xs, ys, zs = (LO[i] + PITCH * np.arange(shape[i]) for i in range(3))
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    occ = np.zeros(tuple(shape), np.uint8)
    capm = np.zeros(tuple(shape), bool)
    names = ['free']
    groups = ['']
    S = scene()
    for name, (M0, grp) in S.items():
        names.append(name)
        groups.append(grp)
        idx = len(names) - 1
        for M in poses(name, M0, grp):
            bl, bh = (np.array(M.bounding_box()).reshape(2, 3))
            if bh[2] < LO[2] or bl[2] > HI[2]:
                continue
            i0 = max(0, int(np.floor((bl[0] - LO[0]) / PITCH))); i1 = min(shape[0], int(np.ceil((bh[0] - LO[0]) / PITCH)) + 1)
            j0 = max(0, int(np.floor((bl[1] - LO[1]) / PITCH))); j1 = min(shape[1], int(np.ceil((bh[1] - LO[1]) / PITCH)) + 1)
            pts = np.stack([X[i0:i1, j0:j1].ravel(), Y[i0:i1, j0:j1].ravel()], 1)
            for k, z in enumerate(zs):
                if z < bl[2] or z > bh[2]:
                    continue
                polys = M.slice(float(z)).to_polygons()
                if not polys:
                    continue
                inside = np.zeros(len(pts), bool)
                for poly in polys:
                    poly = np.asarray(poly)
                    if len(poly) >= 3:
                        inside ^= MPath(poly).contains_points(pts)
                if inside.any():
                    blk = inside.reshape(i1 - i0, j1 - j0)
                    sub = occ[i0:i1, j0:j1, k]
                    sub[blk & (sub == 0)] = idx
                    if grp == 'cap':
                        capm[i0:i1, j0:j1, k] |= blk
        print(f'{name:45s} {grp:6s} {time.time() - t0:6.1f}s', flush=True)
    # descent: a voxel is swept if a cap-mounted voxel lies 0..40 mm below it (the cap comes down from above)
    n = int(round(DESCENT_MM / PITCH))
    cs = np.cumsum(capm, axis=2, dtype=np.int32)
    shifted = np.zeros_like(cs)
    shifted[:, :, n + 1:] = cs[:, :, :-(n + 1)]
    descent = (cs - shifted) > 0
    np.savez_compressed(L.SCRATCH / 'route-occ.npz', occ=occ, lo=LO, pitch=PITCH, names=np.array(names),
                        groups=np.array(groups), capMounted=capm, descent=descent)
    print('occupied fraction', round(float((occ > 0).mean()), 3), 'descent fraction', round(float(descent.mean()), 3),
          f'{time.time() - t0:.1f}s')


if __name__ == '__main__':
    main()
