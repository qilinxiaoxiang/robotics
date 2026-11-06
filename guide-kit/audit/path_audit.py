#!/usr/bin/env python3
"""Exact path audit: does any part, as the guide page animates it, pass through another part?

    python3 path_audit.py --guide <guide-data.json | built page.html> [--adapter adapter.json] [--out report.json]
                          [--steps id,id] [--samples 41]

Each step is played as viewer/app.js plays it (buildTimeline windows and easing, approach paths and waypoints,
group, pose swing, flex spread and riders). At every sample the moving parts are placed and intersected exactly
(manifold3d) with every other part drawn in that step, other moving parts included at their own place on the
timeline. A collision is an overlap that exceeds the seated overlap of the same pair by more than VOL_TOL mm^3
with a median local thickness above THICK_MM; a sleeve already in its bore at rest only fails when the motion adds
material on top of the rest overlap. Parts matching the adapter's `flexible` globs are not swept. Any part whose
mesh is not a closed volume is listed under `unaudited` and fails the run, because no exact answer exists for it.

Exit status 1 when there is a collision or an unaudited part, so a build can gate on it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guide_geom import Solids, bbox, boxes_touch, load_adapter, load_guide, matches, posed_solid, resolve_steps, thickness, timeline  # noqa: E402

VOL_TOL = 0.5      # mm^3, as microduck steps_audit.py
THICK_MM = 0.1


def audit_step(S, step, adapter, samples):
    flexible = adapter['flexible']
    drawn = [k for k in step['add'] + step['show'] + step['ctx'] if not matches(k, flexible)]
    items = {it['key']: it for it in timeline(step, adapter['stagger'])}
    pose = step['pose']
    swing = set(pose['set']) if pose and pose['from'] != pose['deg'] else set()
    flexset = set(step['flex']['set']) if step['flex'] else set()
    movers = [k for k in drawn if (k in items and items[k]['path'] is not None) or k in swing or k in flexset]
    if not movers:
        return [], movers
    role = lambda k: 'added' if k in step['add'] else 'shown' if k in step['show'] else 'context (ghost)'
    rest = {k: posed_solid(S, step, k, items.get(k), 1.0) for k in drawn}
    rest = {k: m for k, m in rest.items() if m is not None}
    rest_box = {k: bbox(m) for k, m in rest.items()}
    rest_vol: dict = {}
    worst: dict = {}
    for pp in np.linspace(0.0, 1.0, samples):
        now = {k: posed_solid(S, step, k, items.get(k), pp) for k in movers if k in rest}
        now = {k: m for k, m in now.items() if m is not None}
        boxes = {k: bbox(m) for k, m in now.items()}
        for a in now:
            for b in rest:
                if b == a or (b in now and b < a):        # each moving pair once
                    continue
                mb = now.get(b, rest[b])
                bb = boxes.get(b, rest_box[b])
                if not boxes_touch(boxes[a], bb, 0.05):
                    continue
                pair = (a, b)
                if pair not in rest_vol:
                    rest_vol[pair] = (rest[a] ^ rest[b]).volume() if boxes_touch(rest_box[a], rest_box[b], 0.05) else 0.0
                inter = now[a] ^ mb
                x = inter.volume() - rest_vol[pair]
                if x > VOL_TOL and (pair not in worst or x > worst[pair]['excessMm3']):
                    worst[pair] = {'excessMm3': x, 'atProgress': float(pp), 'inter': inter}
    hits = []
    for (a, b), w in worst.items():
        t = thickness(w.pop('inter'))
        if t <= THICK_MM:
            continue
        hits.append({'moving': a, 'obstacle': b, 'obstacleRole': role(b), 'bothMoving': b in movers,
                     'excessVolumeMm3': round(w['excessMm3'], 2), 'atProgress': round(w['atProgress'], 3),
                     'restOverlapMm3': round(rest_vol[(a, b)], 3), 'thicknessMedianMm': round(t, 3)})
    hits.sort(key=lambda h: -h['excessVolumeMm3'])
    return hits, movers


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--guide', required=True, type=Path)
    ap.add_argument('--adapter', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--steps', help='comma-separated step ids (default: all)')
    ap.add_argument('--samples', type=int, default=41)
    a = ap.parse_args(argv)
    g = load_guide(a.guide)
    adapter = load_adapter(a.adapter)
    S = Solids(g, adapter)
    only = set(a.steps.split(',')) if a.steps else None
    report = []
    for st in resolve_steps(g):
        if st['id'] in adapter['ignoreSteps'] or (only and st['id'] not in only):
            continue
        hits, movers = audit_step(S, st, adapter, a.samples)
        report.append({'step': st['id'], 'title': st['title'], 'movers': movers, 'pathCollisions': hits})
        print(f"{st['id']}: movers {len(movers)} collisions {len(hits)}", file=sys.stderr, flush=True)
    summary = {'guide': str(a.guide), 'samples': a.samples, 'volumeToleranceMm3': VOL_TOL, 'thicknessMinMm': THICK_MM,
               'stagger': adapter['stagger'], 'steps': len(report),
               'stepsWithCollisions': sum(bool(r['pathCollisions']) for r in report),
               'pathCollisions': sum(len(r['pathCollisions']) for r in report),
               'unaudited': S.failed}
    out = {'summary': summary, 'steps': report}
    if a.out:
        a.out.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(summary))
    return 1 if summary['pathCollisions'] or S.failed else 0


if __name__ == '__main__':
    sys.exit(main())
