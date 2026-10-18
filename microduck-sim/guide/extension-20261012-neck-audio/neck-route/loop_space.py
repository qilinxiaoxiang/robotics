#!/usr/bin/env python3
"""Where the yaw/roll service loop can hang beside the head-pitch bracket without being reached by a moving part.

Grid in the head-pitch bracket's own frame (MJCF body neck_pitch; equal to the robot frame at q = 0), 1 mm voxels,
x 4..46, y -36..-14, z 60..104 (the -y side of the bracket under the head). At every pose of a pose set, every part on
another body (torso, neck, yaw link, head, jaw) is moved into the bracket frame and sliced exactly (manifold3d) at each
grid z; voxel centres inside a section are 'reached' at that pose. The bracket's own parts are occupied at every pose.
A voxel is 'always free' when no pose reaches it. Reports the always-free volume, its largest inscribed sphere (EDT on
the 1 mm grid, so +-0.5 mm), and the always-free space within 6 mm outside the bracket's -y plate (where a loop held by
the bracket clip would lie), per z band. Pose sets: policy (jaw 0 only, and jaw 0 + 40) and pickup, from motion.py.
Writes loop-space.json.
"""
import sys
import time

import numpy as np
from scipy import ndimage
from matplotlib.path import Path as MPath

sys.path.insert(0, __import__('os').path.dirname(__file__))
from nr_lib import FK, HERE, body_of, ia_lib, jdump, load_solid, rnd  # noqa: E402
from motion import pose_sets  # noqa: E402

LO = np.array([4.0, -36.0, 60.0])
HI = np.array([46.0, -14.0, 104.0])
P = 1.0
xs, ys, zs = (np.arange(LO[i], HI[i] + 1e-9, P) for i in range(3))
X, Y = np.meshgrid(xs, ys, indexing='ij')
XY = np.stack([X.ravel(), Y.ravel()], 1)


def occupancy(man):
    occ = np.zeros((len(xs), len(ys), len(zs)), bool)
    for k, z in enumerate(zs):
        polys = man.slice(float(z)).to_polygons()
        if not polys:
            continue
        ins = np.zeros(len(XY), bool)
        for poly in polys:
            poly = np.asarray(poly)
            if len(poly) >= 3:
                ins ^= MPath(poly).contains_points(XY)
        occ[:, :, k] = ins.reshape(len(xs), len(ys))
    return occ


def main():
    t0 = time.time()
    fk = FK()
    sets = pose_sets(fk)
    g = ia_lib.load_guide()
    keys = [p['key'] for p in g['parts'] if body_of(p['key']) is not None and p['key'] != 'head_cap'] + ['head_cap_nonotch']
    own, other = [], []
    for k in keys:
        v, f = load_solid(k)
        if v[:, 2].max() < 30:
            continue
        b = body_of(k.replace('_nonotch', ''))
        (own if b == 'neck_pitch' else other).append((k, b, v, f))
    static = np.zeros((len(xs), len(ys), len(zs)), bool)
    for k, b, v, f in own:
        if (v.max(0) < LO).any() or (v.min(0) > HI).any():
            continue
        static |= occupancy(ia_lib.to_manifold(v, f))
    out = {'_method': __doc__.strip(), 'gridMm': [LO.tolist(), HI.tolist(), P], 'sets': {}}
    plate = (X >= 17) & (X <= 35)
    for sname, poses in (('policy-jaw-closed', [q for q in sets['policy'] if q['jaw'] == 0.0]),
                         ('policy', sets['policy']), ('pickup', sets['pickup'])):
        reached = static.copy()
        for q in poses:
            T = fk.part_T(q)
            Tn_inv = np.linalg.inv(T['neck_pitch'])
            for k, b, v, f in other:
                M = Tn_inv @ T[b]
                w = v @ M[:3, :3].T + M[:3, 3]
                if (w.max(0) < LO).any() or (w.min(0) > HI).any():
                    continue
                reached |= occupancy(ia_lib.to_manifold(w, f))
        free = ~reached
        D = ndimage.distance_transform_edt(free) * P
        i = np.unravel_index(np.argmax(D), D.shape)
        bands = []
        for z0 in range(60, 104, 4):
            kk = (zs >= z0) & (zs < z0 + 4)
            strip = free[:, :, kk] & ((Y >= -25.5) & (Y <= -19.0) & plate)[:, :, None]
            Ds = D[:, :, kk][((Y >= -25.5) & (Y <= -19.0) & plate)]
            bands.append({'zMm': [z0, z0 + 4], 'alwaysFreeVoxelsBesidePlate': int(strip.sum()),
                          'largestSphereRadiusBesidePlateMm': rnd(float(Ds.max()) if Ds.size else 0.0, 1)})
        out['sets'][sname] = {'poses': len(poses), 'alwaysFreeVolumeMm3': int(free.sum() * P ** 3),
                              'largestSphereRadiusMm': rnd(float(D[i]), 1),
                              'largestSphereCentreBracketFrame': [rnd(xs[i[0]], 1), rnd(ys[i[1]], 1), rnd(zs[i[2]], 1)],
                              'besideBracketPlate_y_-25.5_to_-19_x_17_to_35': bands}
        print(sname, 'free mm3', out['sets'][sname]['alwaysFreeVolumeMm3'], 'largest r', out['sets'][sname]['largestSphereRadiusMm'],
              out['sets'][sname]['largestSphereCentreBracketFrame'], f'{time.time() - t0:.0f}s', flush=True)
        for bnd in bands:
            print('   ', bnd, flush=True)
        jdump(out, HERE / 'loop-space.json')


if __name__ == '__main__':
    main()
