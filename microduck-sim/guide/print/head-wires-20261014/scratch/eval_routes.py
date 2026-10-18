#!/usr/bin/env python3
"""Slack and pinch of bundle route candidates over neck/head motion (taut-span model of neck-route/motion.py, exact
distances to the current audit solids). Usage: eval_routes.py ROUTE [maxSeconds]  -> eval-ROUTE.json
Routes: designed (route-v19.json), leftrear (Shawn's left-rear entry, no lower clips), hybrid (lower clips kept, crossing
behind the bracket to the left-rear entry)."""
import sys, json, os, time
os.environ['EXT19_IA_CACHE'] = '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/ia-cache'
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/ext-v19/scripts')
import numpy as np, trimesh, itertools
import ext_lib as E
from motion import BodyFields, pose_sets, sample_route, POLICY
from nr_lib import BODY_ORDER, FK, body_of, rnd
import scene_check as SCN
D2R = np.radians
HERE = os.path.dirname(os.path.abspath(__file__))
ROUTES = json.load(open(os.path.join(HERE, 'routes_candidates.json')))

def build_sets(fk):
    sets = pose_sets(fk)
    sets['rollSweep'] = [{'head_roll': D2R(a), 'jaw': 0.0} for a in np.arange(-25, 25.01, 2.5)]
    sets['rollYaw'] = [{'head_roll': D2R(r), 'head_yaw': D2R(y), 'jaw': 0.0} for r in (-25, -12.5, 0, 12.5, 25) for y in (-80, -40, 0, 40, 80)]
    lo, hi = [-22.6, -0.9, -26.8, -21.4], [44.0, 68.2, 34.0, 11.2]      # recorded walking frames (route-v19-motion.json)
    sets['walkBox'] = [dict(neck_pitch=D2R(n), head_pitch=D2R(h), head_yaw=D2R(y), head_roll=D2R(r), jaw=0.0)
                       for n, h, y, r in itertools.product(*[(a, (a + b) / 2, b) for a, b in zip(lo, hi)])]
    sets['jawSweep'] = [{'jaw': float(a)} for a in np.arange(0, 40.01, 5)]
    return sets

def main():
    name = sys.argv[1]; budget = float(sys.argv[2]) if len(sys.argv) > 2 else 250.0
    only = sys.argv[3].split(",") if len(sys.argv) > 3 else None; tag = sys.argv[4] if len(sys.argv) > 4 else ""
    t0 = time.time()
    r = ROUTES[name]
    fk = FK(); sets = build_sets(fk)
    if only: sets = {k: v for k, v in sets.items() if k in only}
    keys = [k for k in E.ia_lib.manifest() if body_of(k) is not None]
    BF = BodyFields(keys)
    extra_body = {'amplifier': 'jaw_soft', 'speaker': 'jaw_soft', 'speaker_retainer': 'jaw_soft', 'speaker_tape': 'jaw_soft',
                  'clip_head': 'jaw_soft', 'clip_cap': 'jaw_soft', 'clip_torso': 'trunk_base', 'clip_bracket': 'neck_pitch',
                  'rear_frame': 'trunk_base', 'rear_lid': 'trunk_base', 'xl4015_top': 'trunk_base', 'xl4015_mid': 'trunk_base', 'pd5991': 'trunk_base'}
    excl = set(r.get('exclude', []))
    for k, b in extra_body.items():
        if k in excl: continue
        v, f = E.ia_lib.load_solid(k); BF.parts[b].append((k, trimesh.Trimesh(v, f, process=False)))
    for nm, (M, body, capg, _) in SCN.new_parts().items():
        if nm in ('head_cap_v19', 'speaker_retainer_v19', 'speaker', 'amplifier') or nm.startswith('clip_') or nm in excl:
            continue
        BF.parts[body].append((nm, E.tm(M)))
    loaded = {b: [k for k, _ in BF.parts[b]] for b in BODY_ORDER}
    pts = np.array([p[:3] for p in r['points']], float); bodies = [p[3] for p in r['points']]
    rad = float(r.get('groupRadiusMm', 1.7))
    smp = sample_route(pts); si = np.array([s[0] for s in smp]); st = np.array([s[1] for s in smp])
    L0 = float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
    free_spans = [i for i in range(len(pts) - 1) if bodies[i] != bodies[i + 1]]
    out = {'route': name, 'description': r.get('description'), 'groupRadiusMm': rad, 'lengthAtQ0Mm': rnd(L0, 1),
           'points': r['points'], 'excludedObstacles': sorted(excl), 'loadedParts': loaded, 'sets': {}, 'partMin': {}, 'rollTable': []}
    partmin = {}
    done = True
    for sname, poses in sets.items():
        worst_len, worst_pose = -1e9, None
        span_worst = {i: (-1e9, None) for i in free_spans}
        pinch = {'clearanceMm': np.inf}; wraps = 0; wrap_ex = []
        for qi, q in enumerate(poses):
            if time.time() - t0 > budget:
                done = False; break
            T = fk.part_T(q)
            W = np.array([T[b][:3, :3] @ p + T[b][:3, 3] for p, b in zip(pts, bodies)])
            Lq = float(np.linalg.norm(np.diff(W, axis=0), axis=1).sum())
            if Lq - L0 > worst_len: worst_len, worst_pose = Lq - L0, q
            for i in free_spans:
                dl = float(np.linalg.norm(W[i + 1] - W[i]) - np.linalg.norm(pts[i + 1] - pts[i]))
                if dl > span_worst[i][0]: span_worst[i] = (dl, q)
            S = W[si] + st[:, None] * (W[si + 1] - W[si])
            own_a = np.array([bodies[i] for i in si]); own_b = np.array([bodies[i + 1] for i in si])
            dA = np.linalg.norm(S - W[si], axis=1); dB = np.linalg.norm(S - W[si + 1], axis=1)
            wrapped = False; pose_min = np.inf; pose_min_part = None
            for b in BODY_ORDER:
                if not BF.parts[b]: continue
                other = (own_a != b) & (own_b != b)
                if not other.any(): continue
                Ti = np.linalg.inv(T[b]); Pl = S @ Ti[:3, :3].T + Ti[:3, 3]
                d, ins, who = BF.dist(Pl, b)
                oi = np.where(other)[0]
                for k in set(who[oi]) - {''}:
                    m = oi[who[oi] == k]; j = m[np.argmin(d[m])]
                    c = d[j] * (-1 if ins[j] else 1) - rad
                    pm = partmin.get(k)
                    if pm is None or c < pm['clearanceMm']:
                        partmin[k] = {'clearanceMm': rnd(c, 2), 'set': sname, 'segment': int(si[j]), 'at': rnd(S[j], 1),
                                      'poseDeg': {kk: rnd(np.degrees(v) if kk != 'jaw' else v, 1) for kk, v in q.items()}}
                j = oi[np.argmin(d[oi])]
                c = d[j] * (-1 if ins[j] else 1) - rad
                if c < pose_min: pose_min, pose_min_part = c, who[j]
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
            if sname in ('rollSweep', 'jawSweep'):
                out['rollTable'].append({'set': sname, 'poseDeg': {k: rnd(np.degrees(v) if k != 'jaw' else v, 1) for k, v in q.items()},
                                         'minClearanceMm': rnd(pose_min, 2), 'part': pose_min_part, 'slackNeededMm': rnd(Lq - L0, 1)})
        if worst_pose is None: break
        fmt = lambda q: {k: rnd(np.degrees(v) if k != 'jaw' else v, 1) for k, v in q.items()}
        out['sets'][sname] = {
            'poses': len(poses), 'posesChecked': qi + 1, 'slackNeededMm': rnd(worst_len, 1), 'worstPoseDeg': fmt(worst_pose),
            'freeSpans': [{'from': bodies[i], 'to': bodies[i + 1], 'segment': i, 'lengthQ0Mm': rnd(np.linalg.norm(pts[i + 1] - pts[i]), 1),
                           'slackNeededMm': rnd(span_worst[i][0], 1), 'worstPoseDeg': fmt(span_worst[i][1])} for i in free_spans],
            'pinch': {k: (rnd(v, 2) if isinstance(v, (float, np.floating, np.ndarray)) else v) for k, v in pinch.items() if k != 'pose'}
                     | {'poseDeg': fmt(pinch.get('pose', {}))},
            'tautSpanThroughSolids': {'poses': wraps, 'examples': wrap_ex}}
        print(name, sname, len(poses), 'slack', round(worst_len, 1), 'pinch', round(float(pinch['clearanceMm']), 2), pinch.get('part'),
              'wraps', wraps, f'{time.time() - t0:.0f}s', flush=True)
        if not done: break
    out['partMin'] = dict(sorted(partmin.items(), key=lambda kv: kv[1]['clearanceMm']))
    out['complete'] = done; out['elapsedSeconds'] = rnd(time.time() - t0, 0)
    E.jdump(out, os.path.join(HERE, f'eval-{name}{tag}.json'))
    print('written', done)

if __name__ == '__main__':
    main()
