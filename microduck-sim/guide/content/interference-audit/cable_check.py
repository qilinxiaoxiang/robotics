#!/usr/bin/env python3
"""Re-check named guide cables with the cables.py test and report their smallest clearances (read-only).

Usage: cable_check.py <cable id> [...]   (for example: cable_check.py csi pi-trunk imu uart i2s)
For each cable in the current guide-data.json: the drawn-spline and polyline penetration findings exactly as
cables.py / cable_fix.verify compute them (depth > 0.1 mm is a finding), and, for the drawn tube, the smallest
clearance to each nearby audit solid (negative = penetration) with the point where it occurs. Nothing is written;
use it after a routes.json edit and a guide-data rebuild, before re-running cables.py on the whole set.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import trimesh

from cable_fix import Meshes, verify
from cables import spline_samples
from ia_lib import aabb_overlap, load_guide, manifest, rnd


def clearances(meshes, man, path, r, top=8):
    x, _ = spline_samples(path)
    lo, hi = x.min(0) - r - 3.0, x.max(0) + r + 3.0
    out = []
    for k, m in man.items():
        if not aabb_overlap(m['bounds'], [lo, hi]):
            continue
        b = np.array(m['bounds'])
        near = np.all((x >= b[0] - r - 3.0) & (x <= b[1] + r + 3.0), axis=1)
        if not near.any():
            continue
        mesh = meshes.get(k)
        idx = np.flatnonzero(near)
        sd = np.full(len(x), -np.inf)
        for q in range(0, len(idx), 64):
            sd[idx[q:q + 64]] = trimesh.proximity.signed_distance(mesh, x[idx[q:q + 64]])
        kk = int(np.argmax(sd))
        out.append({'part': k, 'clearanceMm': rnd(-sd[kk] - r, 3), 'at': rnd(x[kk], 2)})
    out.sort(key=lambda o: o['clearanceMm'])
    return out[:top]


def main():
    g = load_guide()
    man = manifest()
    meshes = Meshes()
    report = {}
    for cid in sys.argv[1:]:
        c = next(x for x in g['cables'] if x['id'] == cid)
        r = float(c.get('radius') or 0.9)
        path = np.array(c['path'], float)
        f = verify(meshes, man, path, r)
        mid = [x for x in f if x['atEnd'] is None]
        ends = [x for x in f if x['atEnd']]
        cl = clearances(meshes, man, path, r)
        report[cid] = {'radius': r, 'points': len(path), 'midRouteFindings': mid, 'endFindings': ends, 'smallestClearances': cl}
        print(cid, 'r', r, 'mid findings', [(x['mode'], x['part'], x['segments'], x['depthMm'], x['deepestPoint']) for x in mid],
              'end findings', [(x['mode'], x['part'], x['depthMm']) for x in ends], flush=True)
        for o in cl:
            print('   ', o['part'], o['clearanceMm'], o['at'])
    print(json.dumps(report))


if __name__ == '__main__':
    main()
