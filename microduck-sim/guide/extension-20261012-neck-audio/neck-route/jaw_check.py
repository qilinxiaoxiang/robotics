#!/usr/bin/env python3
"""How close the open jaw comes to the neck-side wire spans, compared with how close it comes to the neck itself.

For every pose of the policy and pickup sets with the jaw open (40 deg) and closed (0 deg), exact smallest gaps
(manifold3d min_gap, 10 mm search) between the jaw frame and
  (a) each wire span of a route below the head (the conductor group as a tube of radius r = 1.7 mm, a flat group of
      eight wires lying two deep; the tube follows the taut centreline between the clip points), and
  (b) the parts the span lies on (torso shell, ID12/ID11 cases and links, head-pitch bracket).
Poses where the jaw already touches a neck part (gap < 0.2 mm) cannot be reached by the robot itself and are reported
separately; in the remaining (reachable) poses the wire group must stay clear of the jaw. Routes from route-candidates.json; spans on bodies below the
head only. Writes jaw-check.json.
Usage: jaw_check.py [route ...]
"""
import json
import sys
import time

import numpy as np
import manifold3d as m3

sys.path.insert(0, __import__('os').path.dirname(__file__))
from nr_lib import FK, HERE, body_of, ia_lib, jdump, load_solid, rnd  # noqa: E402
from motion import pose_sets  # noqa: E402

R_GROUP = 1.7
BELOW = ('trunk_base', 'neck', 'neck_pitch')
NECK_PARTS = ['shell_right', 'shell_left', 'motor12', 'motor11', 'neck_link_a', 'neck_link_b', 'neck_pitch', 'idler11',
              'idler_cap11', 'idler12', 'idler_cap12']


def tube(a, b, r):
    d = b - a
    L = float(np.linalg.norm(d))
    if L < 1e-6:
        return m3.Manifold.sphere(r, 16).translate(a.tolist())
    z = d / L
    x = np.cross(z, [0, 0, 1.0]) if abs(z[2]) < 0.9 else np.cross(z, [1.0, 0, 0])
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    M = np.eye(4)[:3]
    M[:, 0], M[:, 1], M[:, 2], M[:, 3] = x, y, z, a
    cyl = m3.Manifold.cylinder(L, r, r, 16).transform(M.tolist())
    return cyl + m3.Manifold.sphere(r, 16).translate(a.tolist()) + m3.Manifold.sphere(r, 16).translate(b.tolist())


def tf(man, T):
    return man.transform(T[:3, :].tolist())


def main():
    t0 = time.time()
    spec = json.loads((HERE / 'route-candidates.json').read_text())
    names = sys.argv[1:] or [r['name'] for r in spec['routes'] if r['name'] != 'current-external']
    fk = FK()
    sets = pose_sets(fk)
    v, f = load_solid('jaw_frame')
    jaw = ia_lib.to_manifold(v, f)
    neck = {k: (ia_lib.to_manifold(*load_solid(k)), body_of(k)) for k in NECK_PARTS}
    out = json.loads((HERE / 'jaw-check.json').read_text()) if (HERE / 'jaw-check.json').exists() else {}
    out['_method'] = __doc__.strip()
    for r in spec['routes']:
        if r['name'] not in names:
            continue
        pts = np.array([p[:3] for p in r['points']], float)
        bodies = [p[3] for p in r['points']]
        spans = [i for i in range(len(pts) - 1) if bodies[i] in BELOW and bodies[i + 1] in BELOW]
        res = {}
        fmt = lambda q: {a: rnd(np.degrees(x) if a != 'jaw' else x, 1) for a, x in q.items()} if q else None  # noqa: E731
        for sname in ('policy', 'pickup'):
            per = []
            for q in sets[sname]:
                T = fk.part_T(q)
                J = tf(jaw, T['jaw'])
                W = np.array([T[b][:3, :3] @ p + T[b][:3, 3] for p, b in zip(pts, bodies)])
                gw = {i: float(J.min_gap(tube(W[i], W[i + 1], R_GROUP), 10.0)) for i in spans}
                gn = {k: float(J.min_gap(tf(m, T[b]), 10.0)) for k, (m, b) in neck.items()}
                kn = min(gn, key=gn.get)
                per.append((q, gw, gn[kn], kn))
            # a pose where the jaw already touches a neck part (gap < 0.2 mm) is blocked by the robot itself; the wire
            # matters only in poses the robot can reach: there the wire must stay clear of the jaw.
            reach = [x for x in per if x[2] >= 0.2]
            rows = []
            for i in spans:
                hits = [x for x in reach if x[1][i] < 0.2]
                best = min(reach, key=lambda x: x[1][i]) if reach else None
                rows.append({'segment': i, 'from': bodies[i], 'to': bodies[i + 1],
                             'minJawToWireGroupSurfaceInReachablePosesMm': rnd(min(best[1][i], 10.0), 2) if best else None,
                             'atPoseDeg': fmt(best[0]) if best else None,
                             'jawToNeckPartsAtThatPoseMm': rnd(min(best[2], 10.0), 2) if best else None,
                             'reachablePosesWhereJawTouchesWire': len(hits),
                             'examples': [fmt(x[0]) for x in hits[:4]]})
            res[sname] = {'poses': len(per), 'posesBlockedByJawOnNeckParts': len(per) - len(reach),
                          'blockedExamples': [{'poseDeg': fmt(x[0]), 'part': x[3]} for x in per if x[2] < 0.2][:4],
                          'spans': rows}
            for row in rows:
                print(r['name'], sname, row['segment'], row['from'], row['to'], 'min jaw-wire (reachable)',
                      row['minJawToWireGroupSurfaceInReachablePosesMm'], 'touching poses', row['reachablePosesWhereJawTouchesWire'],
                      row['atPoseDeg'], f'{time.time() - t0:.0f}s', flush=True)
            print(r['name'], sname, 'poses blocked by jaw on neck parts', len(per) - len(reach), 'of', len(per), flush=True)
        out[r['name']] = {'groupRadiusMm': R_GROUP, **res}
        jdump(out, HERE / 'jaw-check.json')


if __name__ == '__main__':
    main()
