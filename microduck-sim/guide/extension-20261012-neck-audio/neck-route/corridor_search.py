#!/usr/bin/env python3
"""Widest corridors from the torso top through the neck into the closed head and on to the Pi header (q = 0).

Grid search only (0.5 mm voxels from occ.py); corridor.py re-measures every clearance exactly.
  clearance(voxel) = Euclidean distance from the voxel centre to the nearest occupied voxel centre - 0.25 mm
Domain: free voxels; above z HULL_Z (101.5, just above the lower-shell floor) only inside the convex hull of the closed head (notch-less cap + lower shell + face), so
a route must enter the head from below; below it only behind the jaw (x <= 52). A corridor is a maximin path: the
largest threshold t for which start and goal are connected through voxels with clearance >= t (binary search with
26-connected labelling), then the geodesic shortest path inside that threshold set.
Scenarios block or force regions to separate the distinct ways into the head and around the Pi (see SCEN).
Usage: corridor_search.py [cables] [scenario ...] (default: all; 'cables' uses occ-nonotch-cables.npz). Writes SCRATCH/search-<scenario>.json (path + grid bottleneck).
"""
import json
import sys
import time

import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull

sys.path.insert(0, __import__('os').path.dirname(__file__))
from nr_lib import SCRATCH, ia_lib, jdump, load_solid  # noqa: E402

TAG = '-cables' if 'cables' in sys.argv[1:] else ''
d = np.load(SCRATCH / f'occ-nonotch{TAG}.npz')
occ, LO, P, names = d['occ'], d['lo'], float(d['pitch']), list(d['names'])
shape = np.array(occ.shape)
START = np.array([-16.0, 3.0, 41.0])            # current bundle start above the torso plate notch
HULL_Z = 101.5                                  # hull test starts above the lower-shell floor (z 98.7..101)
GOAL = np.array([76.5, 19.0, 117.0])            # in front of the jumper-housing wire exits (pins 1-10 rows)
# Target regions (inside the domain). FRONT: the compartment between the Pi component face and the camera/face, where
# the jumper housings sit. ABOVE: the head volume above every servo and the yaw link (z >= 131), behind the Pi.
REGIONS = {'front': ([63.0, -32.0, 110.0], [78.0, 40.0, 152.0]), 'above': ([-25.0, -40.0, 131.0], [53.0, 40.0, 152.0])}


def ijk(p):
    return tuple(np.round((np.asarray(p) - LO) / P).astype(int))


def xyz(idx):
    return LO + P * np.asarray(idx, float)


def hull_mask():
    pts = []
    for k in ('head_cap_nonotch', 'head_bottom', 'face_panel'):
        v, _ = load_solid(k)
        pts.append(v)
    H = ConvexHull(np.vstack(pts))
    A, b = H.equations[:, :3], H.equations[:, 3]
    m = np.zeros(occ.shape, bool)
    xs, ys, zs = (LO[i] + P * np.arange(shape[i]) for i in range(3))
    k0 = int((HULL_Z - LO[2]) / P)
    Y, Z = np.meshgrid(ys, zs[k0:], indexing='ij')
    for i, x in enumerate(xs):
        q = np.stack([np.full(Y.size, x), Y.ravel(), Z.ravel()], 1)
        ins = np.ones(len(q), bool)
        for c in range(0, len(A), 64):                     # facet chunks keep the product small
            ins &= (q @ A[c:c + 64].T + b[c:c + 64] <= 0).all(1)
        m[i, :, k0:] = ins.reshape(Y.shape)
    return m, k0


def base_domain():
    free = occ == 0
    hm, k0 = hull_mask()
    dom = free.copy()
    dom[:, :, k0:] &= hm[:, :, k0:]
    xs = LO[0] + P * np.arange(shape[0])
    dom[xs > 52.0, :, :k0] = False
    return dom


def box(lo, hi):
    a = np.clip(np.floor((np.asarray(lo) - LO) / P).astype(int), 0, shape - 1)
    b = np.clip(np.ceil((np.asarray(hi) - LO) / P).astype(int) + 1, 0, shape)
    return tuple(slice(a[i], b[i]) for i in range(3))


# Scenarios. target: region name; block: boxes removed from the domain; exclude_near: spheres (centre, radius) removed to
# find the next-widest distinct corridor after a bottleneck is known.
PI_TOP = ([50, -60, 0], [66, 60, 146.0])
SCEN = {
    # Into the head from below: the widest way from the torso top to the space above the servos.
    'entry-1': {'target': 'above'},
    # The whole run to the Pi front, any way round the Pi; then forced over its top / round its +y or -y edge / under it.
    'front-any': {'target': 'front'},
    'front-over-top': {'target': 'front', 'block': [PI_TOP]},
    'front-plus-y': {'target': 'front', 'block': [([50, -60, 0], [66, 60, 112.0]), ([50, -60, 0], [66, 33.0, 200]), ([50, -60, 146.5], [66, 60, 200])]},
    'front-minus-y': {'target': 'front', 'block': [([50, -60, 0], [66, 60, 112.0]), ([50, -33.0, 0], [66, 60, 200]), ([50, -60, 146.5], [66, 60, 200])]},
    'front-under': {'target': 'front', 'block': [([50, -60, 114.0], [66, 60, 200])]},
}
ENTRY_ROUNDS = 4          # entry-2.. : block 6 mm around every earlier entry bottleneck and search again


def region_mask(name, dom):
    m = np.zeros(dom.shape, bool)
    m[box(*REGIONS[name])] = True
    return m & dom


def maximin(dom, clear, s, gmask):
    st = np.ones((3, 3, 3), bool)
    vals = np.round(np.arange(0.25, 8.0, 0.05), 3)
    lo_i, hi_i, best = 0, len(vals) - 1, None
    while lo_i <= hi_i:
        mid = (lo_i + hi_i) // 2
        t = vals[mid]
        m = dom & (clear >= t - 1e-6)
        ok = False
        if m[s]:
            lab, _ = ndimage.label(m, structure=st)
            ok = bool((lab[gmask] == lab[s]).any())
        if ok:
            best = t
            lo_i = mid + 1
        else:
            hi_i = mid - 1
    return best


def geodesic_path(m, s, gmask):
    """Breadth-first wave inside mask m (26-connected) until it reaches the goal region, then walk back."""
    idx = np.argwhere(m)
    a, b = idx.min(0), idx.max(0) + 1
    sl = tuple(slice(a[i], b[i]) for i in range(3))
    m, gm = m[sl], gmask[sl]
    s = tuple(np.array(s) - a)
    dist = np.full(m.shape, -1, np.int32)
    dist[s] = 0
    front = np.zeros(m.shape, bool)
    front[s] = True
    reached = front.copy()
    st = np.ones((3, 3, 3), bool)
    step = 0
    while not (reached & gm).any():
        step += 1
        nf = ndimage.binary_dilation(front, structure=st) & m & ~reached
        if not nf.any():
            return None
        dist[nf] = step
        reached |= nf
        front = nf
    cur = np.argwhere(reached & gm & (dist == step))[0]
    path = [cur]
    offs = np.array([(i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1) if (i, j, k) != (0, 0, 0)])
    while dist[tuple(cur)] > 0:
        nb = cur + offs
        ok = (nb >= 0).all(1) & (nb < np.array(m.shape)).all(1)
        nb = nb[ok]
        cand = nb[dist[nb[:, 0], nb[:, 1], nb[:, 2]] == dist[tuple(cur)] - 1]
        cur = cand[np.argmin(np.abs(cand - cur).sum(1))]
        path.append(cur)
    return [p + a for p in path[::-1]]


def run(name, sc, dom0, clear, s, t0):
    dom = dom0.copy()
    for lo, hi in sc.get('block', []):
        dom[box(lo, hi)] = False
    for c, r in sc.get('exclude_near', []):
        bb = box(np.array(c) - r, np.array(c) + r)
        X, Y, Z = np.meshgrid(*[LO[i] + P * np.arange(bb[i].start, bb[i].stop) for i in range(3)], indexing='ij')
        dom[bb] &= ((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2) > r * r
    gmask = region_mask(sc['target'], dom)
    t = maximin(dom, clear, s, gmask)
    if t is None:
        print(name, 'no connection at any positive clearance', flush=True)
        res = {'scenario': name, 'connected': False, **sc}
        jdump(res, SCRATCH / f'search-{name}{TAG}.json')
        return res
    m = dom & (clear >= t - 1e-6)
    path = geodesic_path(m, s, gmask)
    pts = np.array([xyz(i) for i in path])
    cl = np.array([clear[tuple(i)] for i in path])
    k = int(np.argmin(cl))
    names_at = [names[occ[tuple(i)]] for i in path]
    res = {'scenario': name, 'connected': True, 'gridBottleneckMm': float(t), 'pathVoxels': len(path),
           'pathPoints': pts, 'pathGridClearance': cl, 'bottleneckAt': pts[k], **sc}
    jdump(res, SCRATCH / f'search-{name}{TAG}.json')
    print(f'{name}: grid bottleneck {t:.2f} mm at {np.round(pts[k], 1).tolist()} path {len(path)} voxels '
          f'({time.time() - t0:.1f}s)', flush=True)
    return res


def main():
    t0 = time.time()
    dom0 = base_domain()
    edt = ndimage.distance_transform_edt(occ == 0) * P - P / 2
    clear = np.where(dom0, edt, 0.0).astype(np.float32)
    del edt
    s = ijk(START)
    print(f'domain ready {time.time() - t0:.1f}s; start clearance {clear[s]:.2f}', flush=True)
    which = [a for a in sys.argv[1:] if a != 'cables'] or (list(SCEN) + ['entry-rounds'])
    for name in which:
        if name == 'entry-rounds':
            excl = []
            for r in range(2, ENTRY_ROUNDS + 1):
                prev = json.loads((SCRATCH / f'search-entry-{r - 1}{TAG}.json').read_text())
                if not prev.get('connected'):
                    break
                excl.append((prev['bottleneckAt'], 6.0))
                run(f'entry-{r}', {'target': 'above', 'exclude_near': list(excl)}, dom0, clear, s, t0)
            continue
        run(name, SCEN[name], dom0, clear, s, t0)


if __name__ == '__main__':
    main()
