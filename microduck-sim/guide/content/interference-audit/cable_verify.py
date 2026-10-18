#!/usr/bin/env python3
"""Verify hand-chosen routes.json waypoint moves for one cable with the cables.py test.

Usage: cable_verify.py <cable> <route>:<index>=x,y,z [...]
The moves are applied to the guide cable path through cable_fix.guide_index_map, the whole cable is
re-checked against every audit solid (drawn spline and polyline), and the result is merged into
cable-fix.json as that cable's record (method 'manual', with the same fields as the optimiser output).
"""
from __future__ import annotations

import json
import sys

import numpy as np

from cable_fix import ROUTES, Meshes, guide_index_map, verify
from ia_lib import HERE, load_guide, manifest, rnd


def main():
    cid, specs = sys.argv[1], sys.argv[2:]
    g = load_guide()
    man = manifest()
    R = json.loads(ROUTES.read_text())['routes']
    c = next(x for x in g['cables'] if x['id'] == cid)
    r = float(c.get('radius') or 0.9)
    path = np.array(c['path'], float)
    inv = {(rid, ri): i for i, (rid, ri, _) in guide_index_map(cid, R).items()}
    P = path.copy()
    moves = []
    for sp in specs:
        key, val = sp.split('=')
        rid, ri = key.split(':')
        new = [float(v) for v in val.split(',')]
        P[inv[(rid, int(ri))]] = new
        old = R[rid][int(ri)]
        moves.append({'route': rid, 'index': int(ri), 'from': old, 'to': new, 'moveMm': rnd(float(np.linalg.norm(np.subtract(new, old))), 2)})
    meshes = Meshes()
    before, after = verify(meshes, man, path, r), verify(meshes, man, P, r)
    mid = lambda fs: [f for f in fs if f['atEnd'] is None]  # noqa: E731
    L0 = float(np.sum(np.linalg.norm(np.diff(path, axis=0), axis=1)))
    L1 = float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1)))
    rec = {'cable': cid, 'radius': r, 'method': 'manual waypoints, verified', 'converged': not mid(after), 'waypointMoves': moves,
           'polylineLengthMm': [rnd(L0, 1), rnd(L1, 1)], 'midRouteFindingsBefore': mid(before), 'midRouteFindingsAfter': mid(after),
           'endFindingsAfter': [f for f in after if f['atEnd']]}
    out = HERE / 'cable-fix.json'
    d = json.loads(out.read_text())
    d['cables'] = [x for x in d['cables'] if x['cable'] != cid] + [rec]
    out.write_text(json.dumps(d, indent=1))
    print(json.dumps({'cable': cid, 'midAfter': [(f['mode'], f['part'], f['segments'], f['depthMm'], f['deepestPoint']) for f in mid(after)]}))


if __name__ == '__main__':
    main()
