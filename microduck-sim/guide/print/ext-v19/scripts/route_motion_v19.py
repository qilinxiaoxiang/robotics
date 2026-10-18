#!/usr/bin/env python3
"""Slack and pinch of the V1.9 bundle route (route-v19.json) over neck and head motion, including the recorded
walking frames. Same model as neck-route/motion.py (taut straight spans between points riding on their bodies;
pinch = exact distance from the span centreline to parts on bodies other than the span's two end bodies, minus the
group radius; wrap = free-span samples inside a solid), with the V1.9 scene: release head cap, V1.9 rear pack and the
new parts (clips, retainer, speaker, amplifier) added to their bodies.
Pose sets: policy box, beak pickup, each joint alone over its MJCF range, head yaw sweep (motion.py), plus 'walking':
every adopted phase-1 frame (not fallen, not a blend run), neck joints rounded to 1 deg, jaw closed.
Fan and audio wires (all on the head body) are checked for pinch against the other bodies.
Usage: route_motion_v19.py  -> ../checks/route-v19-motion.json
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np
import trimesh

import ext_lib as E
from motion import BodyFields, pose_sets, sample_route
from nr_lib import BODY_ORDER, FK, body_of, rnd
import scene_check as SCN


def main():
    t0 = time.time()
    spec = json.loads((E.OUT / 'route-v19.json').read_text())
    fk = FK()
    sets = pose_sets(fk)
    walk, winfo, _ = SCN.walking_poses()
    sets['walking'] = walk
    # pinch on walking frames: poses unique at 3 deg (slack uses every 1 deg pose)
    deg = np.array([[np.degrees(q[j]) for j in ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll')] for q in walk])
    _, first = np.unique(np.round(deg / 3.0), axis=0, return_index=True)
    pinch_sel = {'walking': set(first.tolist())}
    keys = [k for k in E.ia_lib.manifest() if body_of(k) is not None and k not in ('head_cap', 'rear_pack')]
    BF = BodyFields(keys)
    BF.parts['jaw_soft'].append(('head_cap_v19', trimesh.load(E.PARTS['head_cap_v19'], force='mesh')))
    BF.parts['trunk_base'].append(('rear_pack_v19', trimesh.load(E.PACK_V19, force='mesh')))
    for nm, (M, body, capg, _) in SCN.new_parts().items():
        if nm == 'head_cap_v19':
            continue
        BF.parts[body].append((nm, E.tm(M)))
    out = {'_method': __doc__.strip(), '_walking': winfo, '_poseSets': {k: len(v) for k, v in sets.items()}}
    routes = list(spec['routes'])
    for grp, key in (('fanWires', 'fan'), ('audioWires', 'audio')):
        for nm, pl in spec[grp]['polylines'].items():
            routes.append({'name': f'{key}-{nm}', 'groupRadiusMm': spec[grp]['radiusMm'],
                           'points': [list(p[:3]) + ['jaw_soft', 'guide'] for p in pl]})
    # cap-lift slack (taut lower bound): with the Pi plugged, the cap group is lowered the last 40 mm; the stretch from
    # the last lower-head tie (head clip exit) to the first cap tie must reach the cap tie raised 40 mm
    pts0 = spec['routes'][0]['points']
    ih = max(i for i, p in enumerate(pts0) if p[4] == 'tie' and p[2] < 120 and p[0] > 40)
    ic = min(i for i, p in enumerate(pts0) if p[4] == 'tie' and i > ih and p[2] > 140)
    P0 = np.array([p[:3] for p in pts0], float)
    closed = float(np.linalg.norm(np.diff(P0[ih:ic + 1], axis=0), axis=1).sum())
    raised = float(np.linalg.norm(P0[ic] + [0, 0, 40.0] - P0[ih]))
    out['capLiftSlack'] = {'fromTie': pts0[ih], 'toTie': pts0[ic], 'closedLengthMm': rnd(closed, 1),
                           'straightToRaisedCapTieMm': rnd(raised, 1), 'extraNeededTautMm': rnd(raised - closed, 1),
                           'method': 'taut lower bound: straight line from the head clip exit to the cap clip tie raised 40 mm'}
    print('cap lift', out['capLiftSlack'], flush=True)
    for r in routes:
        pts = np.array([p[:3] for p in r['points']], float)
        bodies = [p[3] for p in r['points']]
        rad = float(r.get('groupRadiusMm', 0.0))
        smp = sample_route(pts)
        si = np.array([s[0] for s in smp])
        st = np.array([s[1] for s in smp])
        L0 = float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
        free_spans = [i for i in range(len(pts) - 1) if bodies[i] != bodies[i + 1]]
        res = {'description': r.get('description'), 'groupRadiusMm': rad, 'lengthAtQ0Mm': rnd(L0, 1), 'sets': {}}
        for sname, poses in sets.items():
            if sname == 'walking' and not r['name'].startswith('neck-bundle'):
                continue                         # wires inside the head: head joints are covered by the MJCF sets
            worst_len, worst_pose = -1e9, None
            span_worst = {i: (-1e9, None) for i in free_spans}
            pinch = {'clearanceMm': np.inf}
            wraps = 0
            wrap_ex = []
            sel = pinch_sel.get(sname)
            for qi, q in enumerate(poses):
                T = fk.part_T(q)
                W = np.array([T[b][:3, :3] @ p + T[b][:3, 3] for p, b in zip(pts, bodies)])
                Lq = float(np.linalg.norm(np.diff(W, axis=0), axis=1).sum())
                if Lq - L0 > worst_len:
                    worst_len, worst_pose = Lq - L0, q
                for i in free_spans:
                    dl = float(np.linalg.norm(W[i + 1] - W[i]) - np.linalg.norm(pts[i + 1] - pts[i]))
                    if dl > span_worst[i][0]:
                        span_worst[i] = (dl, q)
                S = W[si] + st[:, None] * (W[si + 1] - W[si])
                own_a = np.array([bodies[i] for i in si])
                own_b = np.array([bodies[i + 1] for i in si])
                dA = np.linalg.norm(S - W[si], axis=1)
                dB = np.linalg.norm(S - W[si + 1], axis=1)
                wrapped = False
                if sel is not None and qi not in sel:
                    continue
                for b in BODY_ORDER:
                    if not BF.parts[b]:
                        continue
                    other = (own_a != b) & (own_b != b)
                    if not other.any():
                        continue
                    Ti = np.linalg.inv(T[b])
                    Pl = S @ Ti[:3, :3].T + Ti[:3, 3]
                    d, ins, who = BF.dist(Pl, b)
                    j = np.where(other)[0][np.argmin(d[other])]
                    c = d[j] * (-1 if ins[j] else 1) - rad
                    if c < pinch['clearanceMm']:
                        pinch = {'clearanceMm': c, 'centrelineDistanceMm': d[j], 'inside': bool(ins[j]), 'part': who[j], 'body': b,
                                 'at': S[j], 'routeSegment': int(si[j]), 'pose': q}
                    free = (own_a != own_b) & (dA > 3) & (dB > 3) & ins & other
                    if free.any():
                        wrapped = True
                        if len(wrap_ex) < 6:
                            wrap_ex.append({'part': who[np.where(free)[0][0]], 'body': b, 'segment': int(si[np.where(free)[0][0]]),
                                            'poseDeg': {k: rnd(np.degrees(v) if k != 'jaw' else v, 1) for k, v in q.items()}})
                wraps += int(wrapped)
            res['sets'][sname] = {
                'poses': len(poses), 'posesWithPinchCheck': len(sel) if sel is not None else len(poses),
                'slackNeededMm': rnd(worst_len, 1),
                'worstPoseDeg': {k: rnd(np.degrees(v) if k != 'jaw' else v, 1) for k, v in worst_pose.items()},
                'freeSpans': [{'from': bodies[i], 'to': bodies[i + 1], 'segment': i, 'lengthQ0Mm': rnd(np.linalg.norm(pts[i + 1] - pts[i]), 1),
                               'slackNeededMm': rnd(span_worst[i][0], 1),
                               'worstPoseDeg': {k: rnd(np.degrees(v) if k != 'jaw' else v, 1) for k, v in span_worst[i][1].items()}}
                              for i in free_spans],
                'pinch': {k: (rnd(v, 2) if isinstance(v, (float, np.floating, np.ndarray)) else v) for k, v in pinch.items() if k != 'pose'}
                         | {'poseDeg': {k: rnd(np.degrees(v) if k != 'jaw' else v, 1) for k, v in pinch.get('pose', {}).items()}},
                'tautSpanThroughSolids': {'poses': wraps, 'examples': wrap_ex}}
            print(r['name'], sname, len(poses), 'slack', round(worst_len, 1), 'pinch', round(float(pinch['clearanceMm']), 2),
                  pinch.get('part'), 'wraps', wraps, f'{time.time() - t0:.0f}s', flush=True)
        out[r['name']] = res
        E.jdump(out, E.OUT / 'checks' / 'route-v19-motion.json')


if __name__ == '__main__':
    main()
