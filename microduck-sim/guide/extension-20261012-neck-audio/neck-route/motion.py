#!/usr/bin/env python3
"""Slack and pinch clearance of candidate bundle routes over the neck and jaw motion.

A route (route-candidates.json) is a polyline whose points each ride on one MJCF body ('tie' = fixed to that body by a
tie or clip; 'guide' = held in a passage of that body). At pose q every point moves with its body; spans between points
on different bodies are free spans, modelled taut (straight). For each route and pose set:
  slack needed  = max over poses of (route length at q - route length at q = 0), total and per free span;
  pinch         = smallest exact distance from the route centreline to a part on a body other than the two bodies the
                  span is attached to (minus the conductor-group radius = clearance of the wire surface);
  wrap          = free-span samples (farther than 3 mm from their end points) that lie inside a solid at that pose:
                  the taut line would cut through a part, so the real cable wraps it (length then exceeds the taut value).
Pose sets: 'policy' (box over the walking-policy trace ranges), 'pickup' (neck pitched forward/down, head pitched down,
the bend-forward beak-pickup family), 'mjcf' (each joint alone over its full MJCF range in 10 deg steps).
Jaw 0 and 40 deg (open) in every set. Writes motion.json.
Usage: motion.py [route ...]
"""
import itertools
import json
import sys
import time

import numpy as np
import trimesh

sys.path.insert(0, __import__('os').path.dirname(__file__))
from nr_lib import BODY_ORDER, FK, HERE, body_of, ia_lib, jdump, load_solid, rnd  # noqa: E402

D2R = np.radians
POLICY = {'neck_pitch': (-22.6, 39.8), 'head_pitch': (5.9, 68.2), 'head_yaw': (-24.6, 34.0), 'head_roll': (-21.4, 9.9)}


def pose_sets(fk):
    sets = {}
    vals = {j: (a, (a + b) / 2, b) for j, (a, b) in POLICY.items()}
    sets['policy'] = [dict(neck_pitch=D2R(n), head_pitch=D2R(h), head_yaw=D2R(y), head_roll=D2R(r), jaw=jw)
                      for n, h, y, r, jw in itertools.product(*vals.values(), (0.0, 40.0))]
    sets['pickup'] = [dict(neck_pitch=D2R(n), head_pitch=D2R(h), head_yaw=D2R(y), head_roll=0.0, jaw=jw)
                      for n, h, y, jw in itertools.product((-90.0, -60.0, -45.0), (0.0, 45.0, 90.0), (-24.6, 0.0, 34.0), (0.0, 40.0))]
    mj = []
    for j in POLICY:
        lo, hi = np.degrees(fk.range[j])
        for a in np.unique(np.concatenate([np.arange(np.ceil(lo / 10) * 10, hi + 1e-6, 10.0), [lo, hi]])):
            for jw in (0.0, 40.0):
                mj.append({j: D2R(a), 'jaw': jw})
    sets['mjcf'] = mj
    # head yaw alone over its whole MJCF range (the joint with the largest range), to find where the yaw crossing stops
    # being clean
    sets['yawSweep'] = [{'head_yaw': D2R(a), 'jaw': 0.0} for a in np.arange(-170.0, 171.0, 10.0)]
    return sets


class BodyFields:
    """Exact distance to every part, grouped by body; queried in each body's q = 0 frame."""

    def __init__(self, keys):
        self.parts = {b: [] for b in BODY_ORDER}
        for k in keys:
            v, f = load_solid(k)
            if v[:, 2].max() < 20:
                continue
            b = body_of(k.replace('_nonotch', ''))
            self.parts[b].append((k, trimesh.Trimesh(v, f, process=False)))

    def dist(self, p, body, maxd=12.0):
        """min distance from points p (already in body's q = 0 frame) to that body's parts; inside flag; part name."""
        best = np.full(len(p), np.inf)
        who = np.full(len(p), '', dtype=object)
        inside = np.zeros(len(p), bool)
        for k, m in self.parts[body]:
            lo, hi = m.bounds
            gap = np.linalg.norm(np.maximum(0, np.maximum(lo - p, p - hi)), axis=1)
            sel = gap < np.minimum(best, maxd)
            if not sel.any():
                continue
            ps = p[sel]
            parts = [trimesh.proximity.closest_point(m, ps[i:i + 48]) for i in range(0, len(ps), 48)]   # chunks bound memory
            c = np.concatenate([a[0] for a in parts])
            d = np.concatenate([a[1] for a in parts])
            tri = np.concatenate([a[2] for a in parts])
            nrm = m.face_normals[tri]
            ins = ((p[sel] - c) * nrm).sum(1) < 0           # behind the closest face = inside the closed solid
            better = d < best[sel]
            idx = np.where(sel)[0][better]
            best[idx] = d[better]
            who[idx] = k
            inside[idx] = ins[better]
        return best, inside, who


def sample_route(P):
    seg = []
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]
        n = max(2, int(np.ceil(np.linalg.norm(b - a) / 1.0)) + 1)
        t = np.linspace(0, 1, n)[:-1] if i < len(P) - 2 else np.linspace(0, 1, n)
        for tt in t:
            seg.append((i, tt))
    return seg


def main():
    t0 = time.time()
    spec = json.loads((HERE / 'route-candidates.json').read_text())
    names = sys.argv[1:] or [r['name'] for r in spec['routes']]
    fk = FK()
    sets = pose_sets(fk)
    g = ia_lib.load_guide()
    keys = [p['key'] for p in g['parts'] if body_of(p['key']) is not None and p['key'] != 'head_cap'] + ['head_cap_nonotch']
    BF = BodyFields(keys)
    out_path = HERE / 'motion.json'
    out = json.loads(out_path.read_text()) if out_path.exists() else {}
    out['_method'] = __doc__.strip()
    out['_poseSets'] = {k: len(v) for k, v in sets.items()}
    for r in spec['routes']:
        if r['name'] not in names:
            continue
        pts = np.array([p[:3] for p in r['points']], float)
        bodies = [p[3] for p in r['points']]
        kinds = [p[4] for p in r['points']]
        rad = float(r.get('groupRadiusMm', 0.0))
        smp = sample_route(pts)
        si = np.array([s[0] for s in smp])
        st = np.array([s[1] for s in smp])
        L0 = float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
        free_spans = [i for i in range(len(pts) - 1) if bodies[i] != bodies[i + 1]]
        res = {'description': r.get('description'), 'groupRadiusMm': rad, 'lengthAtQ0Mm': rnd(L0, 1), 'sets': {}}
        for sname, poses in sets.items():
            worst_len, worst_pose = -1e9, None
            span_worst = {i: (-1e9, None) for i in free_spans}
            pinch = {'clearanceMm': np.inf}
            wraps = []
            segmin = {}                                   # per route segment: smallest other-body distance over poses
            per_pose = []
            for q in poses:
                T = fk.part_T(q)
                W = np.array([T[b][:3, :3] @ p + T[b][:3, 3] for p, b in zip(pts, bodies)])
                L = float(np.linalg.norm(np.diff(W, axis=0), axis=1).sum())
                if L - L0 > worst_len:
                    worst_len, worst_pose = L - L0, q
                for i in free_spans:
                    dl = float(np.linalg.norm(W[i + 1] - W[i]) - np.linalg.norm(pts[i + 1] - pts[i]))
                    if dl > span_worst[i][0]:
                        span_worst[i] = (dl, q)
                S = W[si] + st[:, None] * (W[si + 1] - W[si])
                own_a = np.array([bodies[i] for i in si])
                own_b = np.array([bodies[i + 1] for i in si])
                dA = np.linalg.norm(S - W[si], axis=1)
                dB = np.linalg.norm(S - W[si + 1], axis=1)
                for b in BODY_ORDER:
                    if not BF.parts[b]:
                        continue
                    Ti = np.linalg.inv(T[b])
                    Pl = S @ Ti[:3, :3].T + Ti[:3, 3]
                    d, ins, who = BF.dist(Pl, b)
                    other = (own_a != b) & (own_b != b)
                    for sgi in np.unique(si[other]):
                        mm = other & (si == sgi)
                        jj = np.where(mm)[0][np.argmin(d[mm])]
                        val = d[jj] * (-1 if ins[jj] else 1)
                        if sgi not in segmin or val < segmin[sgi][0]:
                            segmin[sgi] = (val, who[jj], b, q)
                    if other.any():
                        j = np.where(other)[0][np.argmin(d[other])]
                        c = d[j] * (-1 if ins[j] else 1) - rad
                        if c < pinch['clearanceMm']:
                            pinch = {'clearanceMm': c, 'centrelineDistanceMm': d[j], 'inside': bool(ins[j]), 'part': who[j], 'body': b,
                                     'at': S[j], 'routeSegment': int(si[j]), 'pose': q}
                    free = (own_a != own_b) & (dA > 3) & (dB > 3) & ins
                    if free.any():
                        wraps.append({'part': who[np.where(free)[0][0]], 'body': b, 'segment': int(si[np.where(free)[0][0]]),
                                      'samples': int(free.sum()), 'pose': q})
            seg_rows = [{'segment': int(k), 'from': bodies[k], 'to': bodies[k + 1], 'kind': 'free span' if bodies[k] != bodies[k + 1] else 'on one body',
                         'minOtherBodyDistanceMm': rnd(v[0], 2), 'part': v[1], 'body': v[2],
                         'poseDeg': {a: rnd(np.degrees(x) if a != 'jaw' else x, 1) for a, x in v[3].items()}} for k, v in sorted(segmin.items())]
            res['sets'][sname] = {
                'perSegment': seg_rows,
                'poses': len(poses), 'slackNeededMm': rnd(worst_len, 1), 'worstPoseDeg': {k: rnd(np.degrees(v) if k != 'jaw' else v, 1) for k, v in worst_pose.items()},
                'freeSpans': [{'from': bodies[i], 'to': bodies[i + 1], 'segment': i, 'lengthQ0Mm': rnd(np.linalg.norm(pts[i + 1] - pts[i]), 1),
                               'slackNeededMm': rnd(span_worst[i][0], 1),
                               'worstPoseDeg': {k: rnd(np.degrees(v) if k != 'jaw' else v, 1) for k, v in span_worst[i][1].items()}} for i in free_spans],
                'pinch': {k: (rnd(v, 2) if isinstance(v, (float, np.floating, np.ndarray)) else v) for k, v in pinch.items() if k != 'pose'}
                         | {'poseDeg': {k: rnd(np.degrees(v) if k != 'jaw' else v, 1) for k, v in pinch.get('pose', {}).items()}},
                'tautSpanThroughSolids': {'poses': len({json.dumps({k: round(float(v), 4) for k, v in w['pose'].items()}) for w in wraps}),
                                          'examples': [{**{k: v for k, v in w.items() if k != 'pose'},
                                                        'poseDeg': {k: rnd(np.degrees(v) if k != 'jaw' else v, 1) for k, v in w['pose'].items()}} for w in wraps[:6]]}}
            print(r['name'], sname, 'slack', round(worst_len, 1), 'pinch', round(float(pinch['clearanceMm']), 2), pinch.get('part'),
                  'wraps', res['sets'][sname]['tautSpanThroughSolids']['poses'], f'{time.time() - t0:.0f}s', flush=True)
        out[r['name']] = res
        jdump(out, out_path)


if __name__ == '__main__':
    main()
