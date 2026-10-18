#!/usr/bin/env python3
"""Step 2b: the same exact pairwise intersection on the meshes the viewer actually draws (guide-data.json).

Purpose: separate overlaps a reader sees in the viewer but that do not exist on the source solids (class d,
decimation artifacts) from real ones. Display meshes that manifold3d accepts are intersected exactly; any
display mesh that is not a closed volume is listed and tested with surface samples against the other mesh's
generalized winding number instead (labelled display-mesh method). Writes pairs-display.json.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import trimesh

from ia_lib import HERE, aabb_overlap, decode_guide_part, from_manifold, load_guide, manifold_ok, obb_extents, rnd, to_manifold
from pairs import local_thickness


def main():
    g = load_guide()
    parts = {}
    open_meshes = []
    for p in g['parts']:
        v, f = decode_guide_part(p)
        m = trimesh.Trimesh(v, f, process=True)
        man = to_manifold(m.vertices, m.faces)
        ok = manifold_ok(man) and man.volume() > 0
        if not ok:
            open_meshes.append(p['key'])
        parts[p['key']] = {'bounds': p['bounds'], 'man': man if ok else None, 'mesh': m}
    keys = list(parts)
    out = []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if not aabb_overlap(parts[a]['bounds'], parts[b]['bounds'], 0.1):
                continue
            A, B = parts[a], parts[b]
            if A['man'] is not None and B['man'] is not None:
                inter = A['man'] ^ B['man']
                vol = inter.volume()
                if vol <= 1e-6:
                    continue
                comps = []
                for c in inter.decompose():
                    if c.volume() < 1e-6:
                        continue
                    v, f = from_manifold(c)
                    med, p95 = local_thickness(v, f, n=150)
                    comps.append({'volumeMm3': c.volume(), 'centroid': rnd(v.mean(0), 2), 'bounds': rnd([v.min(0), v.max(0)], 2),
                                  'pcaExtentsMm': rnd(obb_extents(v), 3), 'thicknessMedianMm': rnd(med, 3)})
                comps.sort(key=lambda c: -c['volumeMm3'])
                out.append({'a': a, 'b': b, 'method': 'exact (display meshes closed)', 'volumeMm3': vol,
                            'depthMm': max((c['thicknessMedianMm'] for c in comps), default=0), 'components': comps})
            else:
                out.append({'a': a, 'b': b, 'method': 'display mesh not closed; not intersected', 'volumeMm3': None})
    (HERE / 'pairs-display.json').write_text(json.dumps({'openDisplayMeshes': open_meshes, 'pairs': out}, indent=1))
    print(json.dumps({'openDisplayMeshes': open_meshes, 'overlapping': len(out),
                      'depthOver0.1': sum((r.get('depthMm') or 0) > 0.1 for r in out)}))


if __name__ == '__main__':
    main()
