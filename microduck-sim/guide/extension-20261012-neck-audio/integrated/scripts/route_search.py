#!/usr/bin/env python3
"""Task 2: widest way for the neck bundle from the top of the -y slot to the front of the 8 bundle housings
(Pi pins 1, 2, 3, 5, 6, 8, 9, 10), through the closed integrated head with every audio part, the Pi-mount A rails, the
camera ribbon, the head servo cables, the jaw sweep and the head-roll sweep in place (route-occ.npz).

Grid search (0.5 mm voxels): clearance(voxel) = distance from the voxel centre to the nearest occupied voxel centre
minus 0.25 mm. Domain: free voxels inside the convex hull of the closed head (integrated cap + lower shell + face).
A corridor is a maximin path: the largest clearance t at which start and goal connect (26-connected), then the
shortest path inside that set. route_exact.py re-measures every clearance exactly.
Start: free voxels within 2 mm of the top of the -y slot route (neck-route A2 head points up to its head tie).
Goal: the space in front of the 8 housings' wire-exit faces (x 74.6..77, y 12.7..25.4, z 112..121).
Scenarios:
  any          everything allowed
  over-top     around the Pi over its top edge (the Pi zone x 50..66 closed below z 146)
  under        around the Pi under its bottom edge (the Pi zone closed above z 114)
  lower-held   any way, but outside the cap-descent mask (a route held only on the lower head)
  over-top-plus-y / over-top-minus-y   over the Pi top edge at y > 15 (where V1.8 crosses) / at y < -15
  A3-clip-over-top-plus-y   as over-top-plus-y but starting at the head clip (H-jaw_support-03) instead of the slot top
  A3-slot-to-clip           from the slot top to the head clip (goal: around the clip hook)
Writes ../route-search.json and SCRATCH/route-search-<scenario>.npz (path voxels).
"""
import json
import sys
import time

import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull

import int_lib as L

d = np.load(L.SCRATCH / 'route-occ.npz')
occ, LO, P, names, groups = d['occ'], d['lo'], float(d['pitch']), list(d['names']), list(d['groups'])
descent = d['descent']
shape = np.array(occ.shape)
SLOT = np.array([[33.3, -26.9, 118.9], [34.0, -26.3, 130.8], [35.6, -23.0, 136.3]])
GOAL = ([74.6, 12.7, 112.0], [77.0, 25.4, 121.0])
SCEN = {'any': {}, 'over-top': {'block': [([50, -60, 0], [66, 60, 146.0])]},
        'under': {'block': [([50, -60, 114.0], [66, 60, 200])]}, 'lower-held': {'avoidDescent': True},
        'over-top-plus-y': {'block': [([50, -60, 0], [66, 60, 146.0]), ([50, -60, 0], [66, 15.0, 200])]},
        'over-top-minus-y': {'block': [([50, -60, 0], [66, 60, 146.0]), ([50, -15.0, 0], [66, 60, 200])]},
        # final route A3: from the head clip under jaw-support screw H-jaw_support-03 (seat 42.1, -30, 113.2; the group
        # passes 3.8 mm above the seat: screw head 1.5 + clip 1.0 + half the group) over the Pi top at y > 15
        'A3-clip-over-top-plus-y': {'start': [[42.1, -29.0, 117.0]], 'startR': 1.5,
                                    'block': [([50, -60, 0], [66, 60, 146.0]), ([50, -60, 0], [66, 15.0, 200])]},
        # the short head span before it: from the top of the slot over the jaw-support cross wall to the head clip
        'A3-slot-to-clip': {'goal': ([42.0, -30.5, 116.0], [45.0, -27.5, 119.0])}}


def box(lo, hi):
    a = np.clip(np.floor((np.asarray(lo) - LO) / P).astype(int), 0, shape - 1)
    b = np.clip(np.ceil((np.asarray(hi) - LO) / P).astype(int) + 1, 0, shape)
    return tuple(slice(a[i], b[i]) for i in range(3))


def xyz(idx):
    return LO + P * np.asarray(idx, float)


def hull_mask():
    import trimesh
    from scene import load_tm
    pts = [trimesh.load(L.INTEGRATED_CAP, force='mesh').vertices, load_tm('head_bottom').vertices, load_tm('face_panel').vertices]
    H = ConvexHull(np.vstack(pts))
    A, b = H.equations[:, :3], H.equations[:, 3]
    xs, ys, zs = (LO[i] + P * np.arange(shape[i]) for i in range(3))
    m = np.zeros(occ.shape, bool)
    Yg, Zg = np.meshgrid(ys, zs, indexing='ij')
    for i, x in enumerate(xs):
        q = np.stack([np.full(Yg.size, x), Yg.ravel(), Zg.ravel()], 1)
        ins = np.ones(len(q), bool)
        for c in range(0, len(A), 64):
            ins &= (q @ A[c:c + 64].T + b[c:c + 64] <= 0).all(1)
        m[i] = ins.reshape(Yg.shape)
    return m


def near_polyline(pts, r):
    xs, ys, zs = (LO[i] + P * np.arange(shape[i]) for i in range(3))
    lo, hi = pts.min(0) - r - 1, pts.max(0) + r + 1
    sl = box(lo, hi)
    G = np.stack(np.meshgrid(xs[sl[0]], ys[sl[1]], zs[sl[2]], indexing='ij'), -1)
    dmin = np.full(G.shape[:3], np.inf)
    for a, b in zip(pts[:-1], pts[1:]):
        ab = b - a
        t = np.clip(((G - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
        dmin = np.minimum(dmin, np.linalg.norm(G - (a + t[..., None] * ab), axis=-1))
    m = np.zeros(occ.shape, bool)
    m[sl] = dmin <= r
    return m


def maximin(dom, clear, smask, gmask):
    st = np.ones((3, 3, 3), bool)
    vals = np.round(np.arange(0.25, 8.0, 0.05), 3)
    lo_i, hi_i, best = 0, len(vals) - 1, None
    while lo_i <= hi_i:
        mid = (lo_i + hi_i) // 2
        m = dom & (clear >= vals[mid] - 1e-6)
        ok = False
        if (m & smask).any():
            lab, _ = ndimage.label(m, structure=st)
            sl = set(np.unique(lab[smask & m])) - {0}
            gl = set(np.unique(lab[gmask & m])) - {0}
            ok = bool(sl & gl)
        if ok:
            best, lo_i = vals[mid], mid + 1
        else:
            hi_i = mid - 1
    return best


def geodesic_path(m, smask, gmask):
    idx = np.argwhere(m)
    a, b = idx.min(0), idx.max(0) + 1
    sl = tuple(slice(a[i], b[i]) for i in range(3))
    m, gm, sm = m[sl], gmask[sl], smask[sl] & m[sl]
    dist = np.full(m.shape, -1, np.int32)
    dist[sm] = 0
    front, reached = sm.copy(), sm.copy()
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


def main():
    t0 = time.time()
    dom0 = (occ == 0) & hull_mask()
    edt = ndimage.distance_transform_edt(occ == 0) * P - P / 2
    clear = np.where(dom0, edt, 0.0).astype(np.float32)
    del edt
    smask = near_polyline(SLOT, 2.0) & dom0
    gm0 = np.zeros(occ.shape, bool)
    gm0[box(*GOAL)] = True
    print(f'domain ready {time.time() - t0:.1f}s; start voxels {int(smask.sum())}, goal voxels {int((gm0 & dom0).sum())}', flush=True)
    out = {'_method': __doc__.strip(), 'start': SLOT, 'goal': GOAL, 'scenarios': {}}
    which = sys.argv[1:] or list(SCEN)
    for name in which:
        sc = SCEN[name]
        dom = dom0.copy()
        for lo, hi in sc.get('block', []):
            dom[box(lo, hi)] = False
        if sc.get('avoidDescent'):
            dom &= ~descent
        if 'goal' in sc:
            gmask = np.zeros(occ.shape, bool)
            gmask[box(*sc['goal'])] = True
            gmask &= dom
        else:
            gmask = gm0 & dom
        sm = (near_polyline(np.array(sc['start'] * 2, float), sc['startR']) & dom0) if 'start' in sc else smask
        t = maximin(dom, clear, sm & dom, gmask)
        if t is None:
            out['scenarios'][name] = {'connected': False}
            print(name, 'not connected', flush=True)
            continue
        m = dom & (clear >= t - 1e-6)
        path = geodesic_path(m, sm & dom, gmask)
        pts = np.array([xyz(i) for i in path])
        cl = np.array([clear[tuple(i)] for i in path])
        k = int(np.argmin(cl))
        # what bounds the bottleneck: the occupied voxels nearest to it
        bi = np.array(path[k])
        r = int(np.ceil((t + 1.0) / P))
        sub = occ[tuple(slice(max(0, bi[i] - r), bi[i] + r + 1) for i in range(3))]
        ids, cnt = np.unique(sub[sub > 0], return_counts=True)
        sub_idx = np.argwhere(sub > 0) + np.maximum(0, bi - r)
        dd = np.linalg.norm(sub_idx - bi, axis=1) * P
        near = {}
        for (ii, jj, kk), dv in zip(sub_idx, dd):
            nm = names[occ[ii, jj, kk]]
            near[nm] = min(near.get(nm, 99.0), float(dv))
        inD = descent[tuple(np.array(path).T)]
        out['scenarios'][name] = {'connected': True, 'gridBottleneckRadiusMm': float(t), 'pathVoxels': len(path),
                                  'gridPathLengthMm': float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum()),
                                  'bottleneckAt': pts[k], 'bottleneckNeighbours': dict(sorted(near.items(), key=lambda kv: kv[1])[:5]),
                                  'pointsInCapDescentMask': int(inD.sum()), 'firstPointInDescentMask': int(np.argmax(inD)) if inD.any() else None}
        np.savez_compressed(L.SCRATCH / f'route-search-{name}.npz', path=np.array(path), pts=pts, clear=cl, inDescent=inD)
        print(name, json.dumps(L.rnd(out['scenarios'][name], 2)), f'{time.time() - t0:.0f}s', flush=True)
    prev = json.loads((L.STUDY / 'route-search.json').read_text()) if (L.STUDY / 'route-search.json').exists() else {}
    prev.update({k: v for k, v in out.items() if k != 'scenarios'})
    prev.setdefault('scenarios', {}).update(out['scenarios'])
    L.jdump(L.rnd(prev, 3), L.STUDY / 'route-search.json')


if __name__ == '__main__':
    main()
