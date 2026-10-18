#!/usr/bin/env python3
"""Copy the eight in-leg servo cable centrelines into routes.json (ttl-05-04 ... ttl-07-06).

    python3 guide/content/leg_routes.py

Each route is the middle conductor of the neutral leg routes reviewed on 2026-10-09
(build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/motor-wires/slack-packaging/
mixed-centerlines.json and INSTALL-SEQUENCE.md): knee links 4->3 and 9->8 from mixed-all.json (100 mm class), the
middle links 3->2 and 8->7 from shared-port-repair/joint-*.json and the ankle links 2->1 and 7->6 from mixed-all.json.
The two hip links 5->4 and 10->9 are set here (HIP) for the V1.8 rear pack. Lines keep their end points; arcs are sampled every 30 degrees. Coordinates stay in the robot frame (mm, identity transform).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
WIRES = HERE.parents[1] / 'build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/motor-wires'
ROUTES = HERE / 'routes.json'

SOURCES = {
    'ttl-04-03': ('slack-packaging/mixed-all.json', 'ttl-04-03-2'),
    'ttl-03-02': ('shared-port-repair/joint-right.json', 'ttl-03-02-2'),
    'ttl-02-01': ('slack-packaging/mixed-all.json', 'ttl-02-01-2'),
    'ttl-09-08': ('slack-packaging/mixed-all.json', 'ttl-09-08-2'),
    'ttl-08-07': ('shared-port-repair/joint-left.json', 'ttl-08-07-2'),
    'ttl-07-06': ('slack-packaging/mixed-all.json', 'ttl-07-06-2'),
}

# The 2026-10-09 hip links (hip-coiled-*.json) stored their spare length as a coil in the old power support's rear
# pocket; the V1.8 rear pack plate now fills that space (cable_check: 1.9 mm into rear_pack). Both hip links instead
# drop through the torso base's central 12 x 6 mm cable opening (x -6..6, y -3..3), beside the BNO085, and turn out
# to the inboard rear socket of the hip-roll motor. Control points follow an A* corridor on the current closed solids
# with 2 mm clearance (session study, the R/L controller plugs blocked as boxes) and were then checked with
# interference-audit/cable_check.py. The right link starts at the outboard socket of ID5 and crosses the motor top
# behind the R plug; the left link starts at the inboard socket of ID10.
HIP = {
    'ttl-05-04': [[-3.0, -25.5, 22.0], [-3.0, -25.5, 29.0], [-5.0, -23.0, 30.5], [-9.0, -19.0, 29.5], [-11.5, -15.0, 27.5],
                  [-11.5, -10.0, 26.0], [-11.5, -5.6, 24.5], [-11.0, -5.0, 18.0], [-10.5, -5.0, 10.0], [-8.0, -4.0, 5.5],
                  [-4.5, -1.6, 2.5], [-4.5, -1.6, -3.0], [-4.5, -1.6, -13.0], [-6.0, -2.5, -18.0], [-8.0, -5.0, -22.0],
                  [-8.0, -8.0, -25.0], [-7.5, -9.5, -26.5], [-4.5, -9.5, -26.5]],
    'ttl-10-09': [[-3.0, 9.5, 22.0], [-3.0, 9.5, 29.0], [-3.0, 7.5, 30.5], [-3.0, 5.2, 27.0], [-3.0, 4.9, 20.0], [-3.0, 4.8, 12.0],
                  [-3.0, 4.5, 6.0], [-3.0, 1.6, 2.5], [-3.0, 1.6, -3.0], [-3.0, 1.6, -13.0], [-5.0, 2.5, -18.0],
                  [-8.0, 5.0, -22.0], [-8.0, 8.0, -25.0], [-7.5, 9.5, -26.5], [-4.5, 9.5, -26.5]],
}


def rotate(v, axis, a):
    axis = axis / np.linalg.norm(axis)
    return v * math.cos(a) + np.cross(axis, v) * math.sin(a) + axis * np.dot(axis, v) * (1 - math.cos(a))


def arc_points(p):
    c, s, m = (np.array(p[k], float) for k in ('center', 'start', 'mid'))
    n = np.array(p['normal'], float)
    sweep = float(p['sweepRadians'])
    if np.linalg.norm(c + rotate(s - c, n, sweep / 2) - m) > 1e-3:
        n = -n
    k = max(2, int(math.ceil(sweep / math.radians(30))))
    return [list(c + rotate(s - c, n, sweep * i / k)) for i in range(1, k + 1)]


def from_primitives(prims):
    pts = [prims[0]['start']]
    for p in prims:
        pts += arc_points(p) if p['kind'] == 'arc' else [p['end']]
    return pts


def main():
    routes = json.loads(ROUTES.read_text())
    lengths = {}
    for rid, pts in HIP.items():
        routes['routes'][rid] = pts
        lengths[rid] = round(sum(math.dist(a, b) for a, b in zip(pts, pts[1:])), 1)
    for rid, (fname, key) in SOURCES.items():
        d = json.loads((WIRES / fname).read_text())
        rows = d.get('rows') or d['strands']
        row = next(r for r in rows if r['key'] == key)
        pts = from_primitives(row['primitives'])
        clean = [[round(float(x), 2) for x in p] for p in pts]
        clean = [clean[0]] + [p for a, p in zip(clean, clean[1:]) if math.dist(a, p) > 1e-6]
        routes['routes'][rid] = clean
        lengths[rid] = round(sum(math.dist(a, b) for a, b in zip(clean, clean[1:])), 1)
    routes['source']['legs'] = str(WIRES / 'slack-packaging/mixed-centerlines.json') + ' (middle conductors; guide/content/leg_routes.py)'
    ROUTES.write_text(json.dumps(routes, indent=1) + '\n')
    print(json.dumps(lengths, indent=1))


if __name__ == '__main__':
    main()
