#!/usr/bin/env python3
"""Exact clearance along the corridors found by corridor_search.py (q = 0).

For each search result the voxel path is resampled every 0.5 mm. At every sample the exact unsigned point-to-mesh
distance to every solid within reach (closed audit solids, notch-less study cap) is maximised within the plane
perpendicular to the path (projected gradient ascent on the distance, at most 3 mm from the voxel path). That maximum
is the radius of the largest circle-section free tube centred in that cross-section; the minimum over the path is the
corridor's free-space radius (its narrowest cross-section). The parts within 0.3 mm of that distance bound it.
Usage: corridor.py [cables] <scenario> ...  ('cables': read the search run with the existing cables as obstacles and
include them in the exact distance)   Writes corridors.json (merged per scenario) and SCRATCH/exact-<scenario>.npz.
"""
import json
import sys
import time

import numpy as np
import trimesh

sys.path.insert(0, __import__('os').path.dirname(__file__))
from nr_lib import HERE, SCRATCH, body_of, ia_lib, jdump, load_solid, resample, rnd  # noqa: E402

MAXSHIFT = 3.0


class Field:
    """Exact distance to a set of solids, with the identity of the nearest one."""

    def __init__(self, keys, lo, hi, pad=12.0, transforms=None):
        self.meshes, self.keys = [], []
        for k in keys:
            v, f = load_solid(k)
            if transforms is not None:
                T = transforms(k)
                v = v @ T[:3, :3].T + T[:3, 3]
            if (v.min(0) > hi + pad).any() or (v.max(0) < lo - pad).any():
                continue
            self.meshes.append(trimesh.Trimesh(v, f, process=False))
            self.keys.append(k)

    def add_cables(self):
        from scipy.spatial import cKDTree
        from nr_lib import cable_tubes
        self.cables = [(cid, cKDTree(pts), pts, r) for cid, pts, r in cable_tubes(0.1)]

    def query(self, p):
        p = np.atleast_2d(p)
        best = np.full(len(p), np.inf)
        cp = np.zeros_like(p)
        who = np.full(len(p), -1)
        per = np.full((len(p), len(self.meshes)), np.inf)
        for i, m in enumerate(self.meshes):
            lo, hi = m.bounds
            gap = np.linalg.norm(np.maximum(0, np.maximum(lo - p, p - hi)), axis=1)
            sel = gap < np.minimum(best, 15.0)
            if not sel.any():
                continue
            c, d, _ = trimesh.proximity.closest_point(m, p[sel])
            per[sel, i] = d
            better = d < best[sel]
            upd = np.where(sel)[0][better]
            best[upd] = d[better]
            cp[upd] = c[better]
            who[upd] = i
        for j, (cid, tree, pts, r) in enumerate(getattr(self, 'cables', [])):
            d0, ii = tree.query(p)
            d = np.maximum(d0 - r, 0.0)
            c = pts[ii] + (p - pts[ii]) * (r / np.maximum(d0, 1e-9))[:, None]
            per = np.hstack([per, d[:, None]])
            better = d < best
            best[better], cp[better], who[better] = d[better], c[better], len(self.keys) + j
        return best, cp, who, per


def all_keys(cap='head_cap_nonotch'):
    g = ia_lib.load_guide()
    ks = [p['key'] for p in g['parts'] if body_of(p['key']) is not None and p['key'] != 'head_cap']
    return ks + [cap]


def refine(F, pts, iters=40):
    pts = resample(pts, 0.5)
    tang = np.gradient(pts, axis=0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True) + 1e-12
    p0 = pts.copy()
    p = pts.copy()
    step = 0.4
    d, cp, _, _ = F.query(p)
    for _ in range(iters):
        gdir = (p - cp) / np.maximum(d[:, None], 1e-9)
        gdir -= (gdir * tang).sum(1, keepdims=True) * tang
        q = p + step * gdir
        off = q - p0
        off -= (off * tang).sum(1, keepdims=True) * tang
        n = np.linalg.norm(off, axis=1, keepdims=True)
        q = p0 + off * np.minimum(1, MAXSHIFT / np.maximum(n, 1e-9))
        dq, cq, _, _ = F.query(q)
        better = dq > d
        p[better], d[better], cp[better] = q[better], dq[better], cq[better]
        step *= 0.93
    return p0, p, d


def main():
    t0 = time.time()
    out_path = HERE / 'corridors.json'
    allres = json.loads(out_path.read_text()) if out_path.exists() else {}
    args = [a for a in sys.argv[1:] if a != 'cables']
    cables = 'cables' in sys.argv[1:]
    for name in args:
        s = json.loads((SCRATCH / f'search-{name}{"-cables" if cables else ""}.json').read_text())
        name = name + ('+cables' if cables else '')
        if not s.get('connected'):
            allres[name] = {'connected': False}
            continue
        pts = np.array(s['pathPoints'])
        F = Field(all_keys(), pts.min(0), pts.max(0))
        if cables:
            F.add_cables()
        KEYS = F.keys + ['cable:' + c[0] for c in getattr(F, 'cables', [])]
        p0, p, d = refine(F, pts)
        dd, _, who, per = F.query(p)
        k = int(np.argmin(dd))
        near = sorted([(KEYS[i], float(per[k, i])) for i in range(len(KEYS)) if per[k, i] <= dd[k] + 0.3],
                      key=lambda x: x[1])
        # Sections along the path: the narrowest point inside each z band (where the corridor meets each body).
        bands = []
        for zlo, zhi, label in ((40, 60, 'beside ID12 / neck links'), (60, 92, 'beside ID11'),
                                (92, 104, 'neck-pitch bracket and floor opening'), (104, 131, 'servo level inside the head'),
                                (131, 160, 'above the servos / round the Pi')):
            sel = (p[:, 2] >= zlo) & (p[:, 2] < zhi)
            if sel.any():
                j = np.where(sel)[0][np.argmin(dd[sel])]
                bands.append({'zBand': [zlo, zhi], 'where': label, 'minRadiusMm': rnd(dd[j], 2), 'at': rnd(p[j], 1),
                              'nearest': KEYS[who[j]], 'nearestBody': body_of(KEYS[who[j]].replace('_nonotch', ''))})
        allres[name] = {
            'connected': True, 'target': s.get('target'), 'blocks': s.get('block', []), 'excludeNear': s.get('exclude_near', []),
            'gridBottleneckMm': s['gridBottleneckMm'],
            'exactNarrowestRadiusMm': rnd(dd[k], 3), 'exactNarrowestDiameterMm': rnd(2 * dd[k], 2),
            'narrowestAt': rnd(p[k], 2), 'boundedBy': [{'part': a, 'body': body_of(a.replace('_nonotch', '')), 'distanceMm': rnd(b, 3)} for a, b in near],
            'pathLengthMm': rnd(np.linalg.norm(np.diff(p, axis=0), axis=1).sum(), 1),
            'bands': bands, 'samples': len(p)}
        np.savez(SCRATCH / f'exact-{name}.npz', p0=p0, p=p, d=dd)
        print(name, allres[name]['exactNarrowestRadiusMm'], allres[name]['narrowestAt'], near[:4], f'{time.time() - t0:.0f}s', flush=True)
        jdump(allres, out_path)


if __name__ == '__main__':
    main()
