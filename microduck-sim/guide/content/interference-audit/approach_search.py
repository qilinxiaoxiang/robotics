#!/usr/bin/env python3
"""Step 4b: search straight approach vectors that clear the obstacles that are really there.

For each colliding approach found by steps_audit.py, directions on a Fibonacci sphere (and the original
direction at shorter lengths) are swept against the parts that are physically installed at that step
(installed-before plus co-added parts already at their final pose, in the add order the viewer staggers).
The result lists the cleanest vectors; zero excess volume means the straight path is clear at 21 samples
plus the endpoint. Writes approach-search.json.
"""
from __future__ import annotations

import json
import sys

import numpy as np

from ia_lib import HERE, manifest, rnd
from steps_audit import Solids, collisions, physical_state, resolve, sweep
from ia_lib import load_guide


def fib(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = np.pi * (1 + 5 ** 0.5) * i
    return np.c_[np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)]


CASES = [
    # (step, movers (None = whole group/add), obstacles extra policy)
    ('torso-base', ['torso_base']), ('torso-base', ['ring10_torso']), ('torso-base', ['ring5_torso']),
    ('pack-in', ['rear_pack']), ('board', ['openrb_board']), ('converter', ['regulator']),
    ('junction-place', ['junction_j']), ('imu-board', ['imu_board']), ('imu-plug', ['imu_sh4_receiving']),
    ('pack-cover', ['rear_pack_cover']),
    ('jaw', ['jaw_frame']), ('jaw', ['lower_pad']), ('jaw', ['motor15']),
    ('jaw', '__all__'),
    ('head-bottom', ['head_bottom']),
    ('face', ['face_panel']),
    ('camera', ['camera_board']),   # V1.8: no camera_retainer (retired with the plate-only face)
    ('speaker', ['speaker_keeper']), ('speaker', ['speaker']), ('speaker', ['speaker_cradle']),
    ('amp', ['amplifier']), ('pi', '__all__'), ('cap-on', '__all__'), ('close', ['upper_pad']),
]


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', help='comma-separated CASES indices; results merge into approach-search.json')
    ap.add_argument('--dirs', type=int, default=160, help='Fibonacci-sphere directions')
    ap.add_argument('--samples', type=int, default=11, help='samples per path while screening; the chosen vector is re-checked at 41')
    args = ap.parse_args()
    only = {int(i) for i in args.only.split(',')} if args.only else set(range(len(CASES)))
    g = load_guide()
    man = manifest()
    steps, mods = resolve(g)
    phys = physical_state(steps, mods)
    by = {s['id']: s for s in steps}
    S = Solids(cap=60)
    dirs = fib(args.dirs)
    path = HERE / 'approach-search.json'
    prev = json.loads(path.read_text()) if path.exists() and args.only else []
    key = lambda r: (r['step'], json.dumps(r['movers']))
    out = []
    for ci, (sid, movers) in enumerate(CASES):
        if ci not in only:
            continue
        s = by[sid]
        st = phys[sid]
        legit = set(st['installedBefore'])
        if st['bench']:
            legit = set(st['bench'][1]) - set(s['add'])
        group = movers == '__all__'
        movers = list(s['add']) if group else movers
        # obstacles: what is physically there, plus co-added parts that come before the mover and stay put
        co = [k for k in s['add'] if k not in movers]
        if not group:
            order = s['add']
            co = [k for k in co if order.index(k) < order.index(movers[0])]
        obstacles = [k for k in legit if k in man and k not in movers] + co
        # parts of the moving set whose swept box can hit anything (speeds up the 70-part head groups)
        vec0 = np.asarray(s['approach'].get(movers[0], [0, 0, 30]), float)
        L = float(np.linalg.norm(vec0)) or 30.0
        cands = [('original', vec0)] + [('original x%.2f' % f, vec0 * f) for f in (0.75, 0.5, 0.35)] + \
                [('sphere', d * L) for d in dirs]
        if group:
            # one union solid for the whole moving group: same overlap volumes, one boolean per sample
            import manifold3d as m3d
            parts = [S.get(m) for m in movers if m in man]
            gid = '__group__' + sid
            man[gid] = {'bounds': [np.min([man[m]['bounds'][0] for m in movers if m in man], 0).tolist(),
                                   np.max([man[m]['bounds'][1] for m in movers if m in man], 0).tolist()]}
            S.c[gid] = m3d.Manifold.batch_boolean(parts, m3d.OpType.Add)
            sweep_movers = [gid]
        else:
            sweep_movers = movers
        res = []
        for label, vec in cands:
            tot, hits = 0.0, set()
            for m in sweep_movers:
                for c in collisions(sweep(S, man, m, vec, obstacles, n=args.samples)):
                    tot += c['maxExcessVolumeMm3']
                    hits.add(c['obstacle'])
            res.append({'label': label, 'vector': rnd(vec, 1), 'excessVolumeMm3': rnd(tot, 2), 'obstacles': sorted(hits)})
        res.sort(key=lambda r: (r['excessVolumeMm3'], -abs(np.dot(np.asarray(r['vector']), vec0)) / (L * L + 1e-9)))
        clean = [r for r in res if r['excessVolumeMm3'] == 0]
        # among clean ones prefer the one closest to the original direction
        best = max(clean, key=lambda r: float(np.dot(np.asarray(r['vector']), vec0)) / (np.linalg.norm(r['vector']) * L + 1e-9)) if clean else res[0]
        # re-check the chosen vector (and the original) at the full 41 samples used by steps_audit.py
        def full(vec):
            tot, hits = 0.0, set()
            for m in sweep_movers:
                for c in collisions(sweep(S, man, m, vec, obstacles, n=41)):
                    tot += c['maxExcessVolumeMm3']
                    hits.add(c['obstacle'])
            return {'excessVolumeMm3': rnd(tot, 2), 'obstacles': sorted(hits)}
        best = dict(best, check41=full(np.asarray(best['vector'], float)))
        rec = {'step': sid, 'movers': 'group' if group else movers, 'directionsTried': len(cands), 'screenSamples': args.samples, 'guideRevision': g.get('revision'), 'original': rnd(vec0, 1), 'obstacles': sorted(obstacles),
               'originalResult': next(r for r in res if r['label'] == 'original'), 'cleanCount': len(clean),
               'bestClosestToOriginal': best, 'top5': res[:5]}
        out.append(rec)
        print(sid, rec['movers'] if not group else 'group', 'orig', rec['originalResult']['excessVolumeMm3'], 'clean', len(clean),
              'best', best['vector'], best['excessVolumeMm3'], best['obstacles'][:4], file=sys.stderr, flush=True)
        done = {key(r) for r in out}
        merged = [r for r in prev if key(r) not in done] + out
        path.write_text(json.dumps(merged, indent=1))


if __name__ == '__main__':
    main()
