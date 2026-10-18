#!/usr/bin/env python3
"""Step 2: exact part-part overlap in the final assembled scene.

Every pair of the 160 audit solids whose axis-aligned boxes overlap (0.1 mm pad) is intersected exactly with
manifold3d (all 160 solids are closed volumes; see solids-report.json). For each overlap component:
volume, centroid, world box, PCA box extents, and a local thickness (shape-diameter) measured by casting rays
from the component surface inward along the normal to the opposite face. depthMm is the area-weighted median
local thickness: a 0.2 mm slab or a 0.2 mm radial ring reads 0.2 mm; a pin fully inside a housing reads about
its diameter. Writes pairs-raw.json.
"""
from __future__ import annotations

import gc
import json
import sys
from collections import OrderedDict

import numpy as np
import trimesh

from ia_lib import CACHE, HERE, aabb_overlap, alternate_of, apart, load_guide, from_manifold, load_solid, manifest, obb_extents, rnd, to_manifold

MAX_CACHE = 24


class Solids:
    def __init__(self):
        self.c = OrderedDict()

    def get(self, key):
        if key in self.c:
            self.c.move_to_end(key)
            return self.c[key]
        v, f = load_solid(key)
        m = to_manifold(v, f)
        self.c[key] = m
        if len(self.c) > MAX_CACHE:
            self.c.popitem(last=False)
            gc.collect()
        return m


def local_thickness(v, f, n=300):
    m = trimesh.Trimesh(v, f, process=False)
    if m.area <= 0:
        return 0.0, 0.0
    pts, fi = trimesh.sample.sample_surface(m, n, seed=0)
    nrm = m.face_normals[fi]
    origins = pts - nrm * 1e-4
    ray = trimesh.ray.ray_triangle.RayMeshIntersector(m)
    loc, idx_ray, _ = ray.intersects_location(origins, -nrm, multiple_hits=True)
    d = np.full(len(pts), np.nan)
    if len(loc):
        dist = np.linalg.norm(loc - origins[idx_ray], axis=1)
        ok = dist > 2e-4
        for r, dd in zip(idx_ray[ok], dist[ok]):
            if np.isnan(d[r]) or dd < d[r]:
                d[r] = dd
    d = d[~np.isnan(d)]
    if not len(d):
        return 0.0, 0.0
    return float(np.median(d)), float(np.percentile(d, 95))


def main():
    man = manifest()
    keys = list(man)
    alt = alternate_of(load_guide())   # swap alternatives (rear converter box, battery backpack) never meet
    pairs, skipped = [], []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if aabb_overlap(man[a]['bounds'], man[b]['bounds'], 0.1):
                (skipped if apart(alt, a, b) else pairs).append((a, b))
    print('aabb candidate pairs', len(pairs), file=sys.stderr, flush=True)
    S = Solids()
    out = []
    for n, (a, b) in enumerate(pairs):
        ma, mb = S.get(a), S.get(b)
        inter = ma ^ mb
        vol = inter.volume()
        rec = {'a': a, 'b': b, 'volumeMm3': float(vol)}
        if vol > 1e-6:
            comps = []
            for c in inter.decompose():
                cv = c.volume()
                if cv < 1e-6:
                    continue
                v, f = from_manifold(c)
                med, p95 = local_thickness(v, f)
                comps.append({'volumeMm3': cv, 'centroid': rnd(v.mean(0), 2), 'bounds': rnd([v.min(0), v.max(0)], 2),
                              'pcaExtentsMm': rnd(obb_extents(v), 3), 'thicknessMedianMm': rnd(med, 3), 'thicknessP95Mm': rnd(p95, 3)})
            comps.sort(key=lambda c: -c['volumeMm3'])
            rec['components'] = comps
            rec['depthMm'] = max((c['thicknessMedianMm'] for c in comps), default=0.0)
        out.append(rec)
        if n % 100 == 0:
            print(n, a, b, round(vol, 3), file=sys.stderr, flush=True)
    (HERE / 'pairs-raw.json').write_text(json.dumps({'candidatePairs': len(pairs), 'skippedAlternatePairs': [list(x) for x in skipped], 'pairs': out}, indent=1))
    hits = [r for r in out if r['volumeMm3'] > 1e-6]
    print(json.dumps({'candidatePairs': len(pairs), 'overlapping': len(hits),
                      'depthOver0.1': sum(r.get('depthMm', 0) > 0.1 for r in hits)}))


if __name__ == '__main__':
    main()
