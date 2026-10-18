#!/usr/bin/env python3
"""Where the 8 bundle wires leave the group and reach their Pi-header housings (pins 1, 2, 3, 5, 6, 8, 9, 10).

The housings' wire-exit faces point along the header axis (+x, 10 deg down; face centres: odd row x 73.705 z 114.07,
even row x 74.146 z 116.571, measured on the V1.8 housing meshes). In front of them run
two audio jumpers: pin 4 (climbs at x ~76.4, y 21.6, z 117..121.5) and pin 12 (drops at y 11.4, runs +y under the housing
ends at z 113.9 and climbs at y 16.3, right in front of pin 8). Below is the head floor (head_bottom top z 111.5).
Further forward the camera board and face panel are lower-head parts, so any cap-held wire must also stay out of the
40 mm column under them (the cap, with the Pi and these wires, is lowered the last 40 mm onto the lower head).

Grid search on route-occ.npz (0.5 mm voxels, every jaw and roll pose occupied, same as route_search.py):
  domain   = free voxels inside the head hull, minus voxels that have a lower-head / jaw / yaw voxel within 40 mm above
             them (cap-descent sweep of a cap-held wire)
  group    = maximin corridor from the end of the A3 corridor (route-exact-A3-clip-over-top-plus-y) to a gather point G
  wire n   = maximin corridor from a stub point 0.8 mm out of housing n's exit face (along the axis) to G. Voxels within 1.2 mm of
             the stub point are exempt from the clearance threshold (the wire leaves its own housing there).
Each voxel path is simplified (Ramer-Douglas-Peucker 0.35 mm) and starts at the real exit-face centre.
Exact clearances of the resulting wire solids are measured by pairwise.py; this script only finds the paths.
Writes ../route-fan.json.
"""
import json
import time

import numpy as np

import int_lib as L
import route_search as RS

PINS = {1: (24.13, 'odd'), 2: (24.13, 'even'), 3: (21.59, 'odd'), 5: (19.05, 'odd'), 6: (19.05, 'even'),
        8: (16.51, 'even'), 9: (13.97, 'odd'), 10: (13.97, 'even')}
FACE = {'odd': (73.705, 114.07), 'even': (74.146, 116.571)}   # exit-face centres (measured on the V1.8 housing meshes)
G = np.array([77.0, 27.5, 115.5])
AXIS = np.array([0.984808, 0.0, -0.173648])      # housing / header-pin axis, pointing out of the exit face (Pi tilted 10 deg)
DESCENT_MM = 40.0


def rdp(P, eps):
    P = np.asarray(P, float)
    if len(P) < 3:
        return P
    a, b = P[0], P[-1]
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    d = np.linalg.norm(P - (a + t[:, None] * ab), axis=1)
    i = int(np.argmax(d))
    if d[i] <= eps:
        return np.array([a, b])
    return np.vstack([rdp(P[:i + 1], eps)[:-1], rdp(P[i:], eps)])


def ball(c, r):
    return RS.near_polyline(np.array([c, c], float), r)


def corridor(dom, clear, smask, gmask, exempt=None):
    cl = clear.copy()
    if exempt is not None:
        cl[exempt & dom] = 9.0
    t = RS.maximin(dom, cl, smask & dom, gmask & dom)
    if t is None:
        return None
    m = dom & (cl >= t - 1e-6)
    path = RS.geodesic_path(m, smask & dom, gmask & dom)
    pts = np.array([RS.xyz(i) for i in path])
    c_true = np.array([clear[tuple(i)] for i in path])
    ex = np.array([exempt[tuple(i)] for i in path]) if exempt is not None else np.zeros(len(path), bool)
    k = int(np.argmin(np.where(ex, 99, c_true)))
    return {'gridBottleneckRadiusMm': float(c_true[k]), 'bottleneckAt': pts[k], 'pts': pts}


def main():
    t0 = time.time()
    occ, names, groups = RS.occ, RS.names, RS.groups
    low_ids = [i for i, g in enumerate(groups) if g in ('lower', 'jaw', 'yaw')]
    lowv = np.isin(occ, low_ids)
    n = int(round(DESCENT_MM / RS.P))
    c = np.concatenate([np.zeros(occ.shape[:2] + (1,), np.int32), np.cumsum(lowv, axis=2, dtype=np.int32)], axis=2)
    zi = np.arange(occ.shape[2])
    hi = np.minimum(zi + n + 1, occ.shape[2])
    under_lower = (c[:, :, hi] - c[:, :, zi]) > 0                  # a lower voxel within [z, z + 40 mm]
    from scipy import ndimage
    dom0 = (occ == 0) & RS.hull_mask()
    dom = dom0 & ~under_lower
    edt = ndimage.distance_transform_edt(occ == 0) * RS.P - RS.P / 2
    clear = np.where(dom0, edt, 0.0).astype(np.float32)
    del edt
    print(f'domain ready {time.time() - t0:.1f}s; G in domain {bool(dom[tuple(np.round((G - RS.LO) / RS.P).astype(int))])}', flush=True)
    E = np.load(L.SCRATCH / 'route-exact-A3-clip-over-top-plus-y.npz')['S'][-1]
    out = {'_method': __doc__.strip(), 'gatherPoint': G, 'corridorEnd': E, 'descentSweepMm': DESCENT_MM, 'wires': {}}
    gm = ball(G, 1.0)
    g = corridor(dom, clear, ball(E, 1.0), gm)
    gp = rdp(np.vstack([E, g['pts'][1:-1], G]), 0.35)
    out['group'] = {'gridBottleneckRadiusMm': g['gridBottleneckRadiusMm'], 'bottleneckAt': g['bottleneckAt'],
                    'polyline': gp, 'lengthMm': float(np.linalg.norm(np.diff(gp, axis=0), axis=1).sum())}
    print('group', L.rnd(out['group'], 2), f'{time.time() - t0:.0f}s', flush=True)
    for p, (y, row) in PINS.items():
        xf, zc = FACE[row]
        q = np.array([xf, y, zc]) + 0.8 * AXIS
        r = corridor(dom, clear, ball(q, 0.6), gm, exempt=ball(q, 1.2))
        if r is None:
            out['wires'][str(p)] = {'connected': False}
            print('pin', p, 'not connected', flush=True)
            continue
        poly = rdp(np.vstack([[xf, y, zc], q, r['pts'][1:-1], G]), 0.35)
        out['wires'][str(p)] = {'connected': True, 'gridBottleneckRadiusMm': r['gridBottleneckRadiusMm'],
                                'bottleneckAt': r['bottleneckAt'], 'polyline': poly,
                                'lengthMm': float(np.linalg.norm(np.diff(poly, axis=0), axis=1).sum())}
        print('pin', p, L.rnd({k: v for k, v in out['wires'][str(p)].items() if k != 'polyline'}, 2), f'{time.time() - t0:.0f}s', flush=True)
    L.jdump(L.rnd(out, 3), L.STUDY / 'route-fan.json')


if __name__ == '__main__':
    main()
