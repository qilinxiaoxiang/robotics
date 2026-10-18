#!/usr/bin/env python3
"""Step 4: what each guide step draws, and what its approach animation drives through.

State check. Steps are resolved exactly as viewer/app.js does (module names expand; add wins over show,
show over context; every part is drawn at its final world pose). The physical build state is reconstructed
from steps.py semantics: legs start installed; non-bench steps install their `add` parts; bench steps
(servo-ids, flash, jumper-tails, uart-wires, harness bench, the neck bench and the head-cap bench) and the
inventory steps (overview, parts, prints, tools) install nothing. A drawn part that is neither installed,
nor added in this step, nor part of the bench subassembly being built is "drawn where it is not yet".

Sweep check. Each `approach` is animated by the viewer along a path of offsets ending at the seated pose: a
vector v is the straight path [v, 0]; a waypoint list is followed leg by leg, timed by leg length (a `group`
moves all added parts together). A step `pose` turns its parts about an axis through a pivot; with `from` it
swings to `deg` on the same eased progress as the path. A step `flex` springs a part's arms apart along Y while it
moves (vertices beyond |y| ramp[1] by the full spread, the whole part by any `shift`), carrying its riders, and releases them as it seats. The moving solid is sampled at 41 progress values and
intersected exactly (manifold3d) with every other part drawn in the step, posed parts at their pose. A path
collision is any sample whose overlap exceeds the final-pose overlap by more than 0.5 mm^3 with local thickness
> 0.1 mm. For each collision on a straight unposed approach, straight alternatives (+-x, +-y, +-z, same length)
are tested against the obstacles that should legitimately be present. Writes steps-raw.json.
"""
from __future__ import annotations

import gc
import json
import sys
from collections import OrderedDict

import numpy as np

from ia_lib import HERE, aabb_overlap, from_manifold, load_guide, load_solid, manifest, obb_extents, rnd, to_manifold
from pairs import local_thickness

# Steps whose parts are only gathered or printed: they install nothing and are not checked for drawn state.
INVENTORY = {'overview', 'parts', 'prints', 'tools'}
# Bench steps come from each step's 'bench' flag in guide-data.json (guide revision guide-20261009 onward).
# A bench run is a maximal sequence of consecutive bench steps in one chapter; its subassembly accumulates the
# steps' `add` parts. Bench steps install nothing on the robot until a later non-bench step adds those parts.


def bench_runs(steps):
    runs, cur = [], None
    for s in steps:
        if s.get('bench') and s['id'] not in INVENTORY:
            if cur and cur[0] == s['chapter'] and cur[1][-1] == prev:
                cur[1].append(s['id'])
            else:
                cur = (s['chapter'], [s['id']])
                runs.append(cur)
        prev = s['id']
    return runs
N = 41
VOL_TOL = 0.5


class Solids:
    def __init__(self, cap=40):
        self.c, self.cap = OrderedDict(), cap

    def get(self, k):
        if k in self.c:
            self.c.move_to_end(k)
            return self.c[k]
        m = to_manifold(*load_solid(k))
        self.c[k] = m
        if len(self.c) > self.cap:
            self.c.popitem(last=False)
            gc.collect()
        return m


def resolve(g):
    mods = {}
    for p in g['parts']:
        mods.setdefault(p['module'], []).append(p['key'])

    def res(lst):
        out = []
        for r in lst or []:
            for k in (mods[r] if r in mods else [r]):
                if k not in out:
                    out.append(k)
        return out
    steps = []
    for s in g['steps']:
        add = res(s.get('add'))
        show = [k for k in res(s.get('show')) if k not in add]
        ctx = [k for k in res(s.get('context')) if k not in add and k not in show]
        appr = {}
        for ref, vec in (s.get('approach') or {}).items():
            for k in res([ref]):
                if k in add:
                    appr[k] = vec
        if s.get('group'):
            appr = {k: s['group']['approach'] for k in add}
        pose = None
        if s.get('pose'):
            pr = s['pose']
            pose = {'set': res(pr.get('parts')), 'pivot': pr['pivot'], 'axis': pr['axis'], 'deg': float(pr['deg']),
                    'from': float(pr.get('from', pr['deg']))}
        flex = None
        if s.get('flex'):
            fr = s['flex']
            riders = {kk: int(np.sign(sg)) for k, sg in (fr.get('riders') or {}).items() for kk in res([k])}
            flex = {'set': res(fr.get('parts')), 'riders': riders, 'ramp': fr['ramp'], 'spread': fr['spread'],
                    'shift': float(fr.get('shift', 0.0)), 'window': fr['window']}
        steps.append({'id': s['id'], 'chapter': s['chapter'], 'title': s['title'], 'add': add, 'show': show, 'ctx': ctx,
                      'remove': res(s.get('remove')),
                      'approach': appr, 'group': bool(s.get('group')), 'cables': s.get('cables') or [],
                      'bench': bool(s.get('bench')), 'pose': pose, 'flex': flex})
    return steps, mods


def physical_state(steps, mods):
    legs = mods['left-leg'] + mods['right-leg']
    installed = set(legs)
    bench_of = {}
    for name, ids in bench_runs(steps):
        acc = set()
        for sid in ids:
            s = next(x for x in steps if x['id'] == sid)
            acc |= set(s['add'])
            bench_of[sid] = (name, set(acc) | set(s['show']))
    out = {}
    for s in steps:
        # a swap step (steps.py remove=) takes its removed parts off the robot before it adds its own
        installed -= set(s['remove'])
        out[s['id']] = {'installedBefore': set(installed), 'bench': bench_of.get(s['id'])}
        if not s['bench'] and s['id'] not in INVENTORY:
            installed |= set(s['add'])
    return out


def to_path(v):
    """viewer toPath: a vector v is [v, 0]; a waypoint list gets a final [0, 0, 0] when it does not end there."""
    if v is None:
        return None
    if len(v) and not isinstance(v[0], (list, tuple)):
        return np.array([v, [0, 0, 0]], float)
    pts = [[float(x) for x in w] for w in v]
    if any(pts[-1]):
        pts.append([0.0, 0.0, 0.0])
    return np.array(pts, float)


def path_at(path, e):
    """viewer pathAt: the offset at progress e (0 = first waypoint, 1 = seated), legs timed by their length."""
    lens = np.linalg.norm(np.diff(path, axis=0), axis=1)
    total = lens.sum()
    if total <= 0:
        return path[-1]
    d = e * total
    for k, ln in enumerate(lens):
        if d <= ln or k == len(lens) - 1:
            t = min(1.0, d / ln) if ln > 0 else 1.0
            return path[k] + (path[k + 1] - path[k]) * t
        d -= ln
    return path[-1]


def rot_about(axis, deg, pivot):
    """3x4 affine turning deg about the axis through pivot, right-handed like THREE.Quaternion.setFromAxisAngle."""
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    t = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    R = np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * K @ K
    p = np.asarray(pivot, float)
    return np.c_[R, p - R @ p]


def motion(s, mk):
    """Progress u (0 = start, 1 = seated) -> (offset, pose angle or None) for part mk, as viewer applyProgress places it."""
    path = to_path(s['approach'].get(mk))
    pose = s.get('pose')
    posed = pose is not None and mk in pose['set']
    def at(u):
        off = path_at(path, u) if path is not None else np.zeros(3)
        ang = pose['from'] + (pose['deg'] - pose['from']) * u if posed else None
        return off, ang
    return at


def flex_at(f, e):
    """viewer flexAt: spread fraction at progress e, up over [0, in], held, released over [out, 1]."""
    w0, w1 = f['window']
    return 0.0 if e <= 0 or e >= 1 else e / w0 if e < w0 else 1.0 if e <= w1 else (1 - e) / (1 - w1)


def bend(f, a):
    """viewer bendPart: y moves out by the side's spread times a, ramped in between |y| ramp[0] and ramp[1], plus the
    whole-part shift times a."""
    (r0, r1), (sn, sp), sh = f['ramp'], f['spread'], f.get('shift', 0.0)
    def warp(v):
        v = np.array(v, dtype=float, copy=True)
        w = np.clip((np.abs(v[:, 1]) - r0) / (r1 - r0), 0, 1)
        v[:, 1] += (np.where(v[:, 1] < 0, -sn, sp) * w + sh) * a
        return v
    return warp


def placed(S, s, mk, at, u):
    off, ang = at(u)
    M = S.get(mk)
    fl = s.get('flex')
    a = flex_at(fl, u) if fl else 0.0
    if a and mk in fl['set']:
        M = M.warp_batch(bend(fl, a))
    if a and mk in fl['riders']:
        sg = fl['riders'][mk]
        off = off + np.array([0.0, (sg * (fl['spread'][0] if sg < 0 else fl['spread'][1]) + fl.get('shift', 0.0)) * a, 0.0])
    if ang:
        M = M.transform(rot_about(s['pose']['axis'], ang, s['pose']['pivot']))
    return M.translate(list(off))


def static_solid(S, s, o, cache):
    """An obstacle at its drawn pose: turned by a step pose that holds it (not swinging), else as built."""
    pose = s.get('pose')
    if pose is None or o not in pose['set'] or not pose['deg']:
        return S.get(o)
    if o not in cache:
        cache[o] = S.get(o).transform(rot_about(pose['axis'], pose['deg'], pose['pivot']))
    return cache[o]


def sweep(S, man, s, mk, obstacles, n=N, cache=None):
    """Return per-obstacle overlap curve along the step's motion of mk (s=1 start, s=0 seated)."""
    at = motion(s, mk)
    ss = np.linspace(1, 0, n)
    Ms = [placed(S, s, mk, at, 1 - x) for x in ss]
    lo = np.min([np.asarray(M.bounding_box()[:3]) for M in Ms], axis=0) - 0.1
    hi = np.max([np.asarray(M.bounding_box()[3:]) for M in Ms], axis=0) + 0.1
    sw = [lo, hi]
    cache = {} if cache is None else cache
    res = {}
    for o in obstacles:
        if o == mk or not aabb_overlap(sw, man[o]['bounds']):
            continue
        O = static_solid(S, s, o, cache)
        vols = np.array([(M ^ O).volume() for M in Ms])
        res[o] = (ss, vols)
    return res


def sweep_vec(S, man, mk, vec, obstacles, n=N):
    """Straight unposed alternative vec for mk."""
    return sweep(S, man, {'approach': {mk: vec}, 'pose': None, 'flex': None}, mk, obstacles, n=n)


def worst(S, s, mk, o, x, cache):
    inter = placed(S, s, mk, motion(s, mk), 1 - x) ^ static_solid(S, s, o, cache)
    v, f = from_manifold(inter)
    med, p95 = local_thickness(v, f, n=200) if len(f) else (0, 0)
    return {'centroid': rnd(v.mean(0), 2) if len(v) else None, 'bounds': rnd([v.min(0), v.max(0)], 2) if len(v) else None,
            'pcaExtentsMm': rnd(obb_extents(v), 2) if len(v) else None, 'thicknessMedianMm': rnd(med, 3)}


LEAD_STEP = 1.5
LEAD_MAX = 600.0


def lead_in(S, man, s, movers, obstacles):
    """The start of an approach must be reachable: continue its first leg backwards from the start until the moving
    parts' box clears the box of every obstacle, and sweep that lead-in (a group moves together, other movers alone).
    A hit is any lead-in sample whose overlap exceeds the seated overlap by more than VOL_TOL."""
    obs = [o for o in obstacles if o in man]
    if not obs:
        return []
    olo = np.min([man[o]['bounds'][0] for o in obs], axis=0)
    ohi = np.max([man[o]['bounds'][1] for o in obs], axis=0)
    sets = [list(movers)] if s['group'] else [[m] for m in movers]
    out = []
    for ms in sets:
        path = to_path(s['approach'][ms[0]])
        d = path[0] - path[1]
        if not np.linalg.norm(d):
            continue
        d = d / np.linalg.norm(d)
        base = {m: S.get(m) for m in ms}
        seated = {}
        hits = {}
        for t in np.arange(0.0, LEAD_MAX + LEAD_STEP, LEAD_STEP):
            off = path[0] + d * t
            boxes = {m: np.asarray(base[m].bounding_box(), float) + np.r_[off, off] for m in ms}
            lo = np.min([b[:3] for b in boxes.values()], axis=0)
            hi = np.max([b[3:] for b in boxes.values()], axis=0)
            if np.any(lo > ohi) or np.any(hi < olo):
                break
            for m in ms:
                for o in obs:
                    if not aabb_overlap([boxes[m][:3], boxes[m][3:]], man[o]['bounds']):
                        continue
                    if (m, o) not in seated:
                        seated[(m, o)] = (base[m] ^ S.get(o)).volume()
                    x = (base[m].translate(list(off)) ^ S.get(o)).volume() - seated[(m, o)]
                    if x > VOL_TOL:
                        h = hits.setdefault((m, o), {'moving': m, 'obstacle': o, 'segment': 'lead-in',
                                                     'path': path.tolist(), 'firstHitBeyondStartMm': rnd(t, 1),
                                                     'maxExcessVolumeMm3': 0.0, 'obstacleLegitimatelyPresent': True})
                        if x > h['maxExcessVolumeMm3']:
                            h['maxExcessVolumeMm3'], h['_off'] = rnd(x, 2), off
        for h in hits.values():
            v, f = from_manifold(base[h['moving']].translate(list(h.pop('_off'))) ^ S.get(h['obstacle']))
            med, _ = local_thickness(v, f, n=200) if len(f) else (0, 0)
            h['worst'] = {'centroid': rnd(v.mean(0), 2) if len(v) else None, 'thicknessMedianMm': rnd(med, 3)}
            if med > 0.1:
                out.append(h)
    return out


def collisions(curves, final_tol=VOL_TOL):
    out = []
    for o, (ss, vols) in curves.items():
        fin = vols[-1]
        excess = vols - fin
        if excess.max() > final_tol:
            k = int(np.argmax(excess))
            hit = np.flatnonzero(excess > 0.05)
            out.append({'obstacle': o, 'maxExcessVolumeMm3': rnd(excess.max(), 2), 'atFraction': rnd(ss[k], 3),
                        'firstContactFraction': rnd(ss[hit.min()] if len(hit) else 0, 3),
                        'lastContactFraction': rnd(ss[hit.max()] if len(hit) else 0, 3),
                        'finalOverlapMm3': rnd(fin, 3)})
    return out


def main():
    g = load_guide()
    man = manifest()
    steps, mods = resolve(g)
    phys = physical_state(steps, mods)
    S = Solids()
    report = []
    for s in steps:
        drawn = set(s['add']) | set(s['show']) | set(s['ctx'])
        st = phys[s['id']]
        legit = set(st['installedBefore']) | set(s['add'])
        if st['bench']:
            legit = set(st['bench'][1])
        rec = {'step': s['id'], 'chapter': s['chapter'], 'title': s['title'], 'bench': s['bench'], 'inventory': s['id'] in INVENTORY,
               'drawnParts': len(drawn), 'add': s['add'], 'approach': s['approach'], 'group': s['group'], 'cables': s['cables']}
        if s['id'] not in INVENTORY:
            # parts drawn that exist nowhere yet (neither installed on the robot nor on the bench in this run)
            exists = legit | set(st['installedBefore'])
            rec['drawnButNotPresent'] = sorted(drawn - exists)
            if st['bench']:
                # the bench subassembly is drawn at its final robot pose; robot parts drawn with it suggest it is mounted
                rec['benchSubassembly'] = st['bench'][0]
                rec['robotContextDrawnWithBench'] = sorted((drawn - st['bench'][1]) & set(st['installedBefore']))
        # sweeps: approach paths, plus every drawn posed part while a pose swings
        coll = []
        pose = s.get('pose')
        if pose and pose['deg'] and pose['from'] == pose['deg']:
            # a held pose (the jaw open while screws or the upper pad go in): new overlap at the pose over the seated one
            held = [k for k in pose['set'] if k in drawn and k in man and k not in s['approach']]
            others = [k for k in drawn if k in man and k not in pose['set']]
            hold = {'approach': {}, 'pose': {**pose, 'from': 0.0}, 'flex': None}
            rec['heldPoseOverlaps'] = [dict(c, moving=mk) for mk in held for c in collisions(sweep(S, man, hold, mk, others, n=2))]
        swinging = [k for k in (pose['set'] if pose and pose['from'] != pose['deg'] else [])
                    if k in drawn and k in man and k not in s['approach']]
        movers = [k for k in s['approach'] if k in man] + swinging
        if movers:
            rec['pose'] = {k: v for k, v in pose.items() if k != 'set'} | {'parts': pose['set']} if pose else None
            rec['flex'] = {k: v for k, v in s['flex'].items() if k != 'set'} | {'parts': s['flex']['set']} if s.get('flex') else None
            static = [k for k in (s['show'] + s['ctx']) if k in man and k not in movers] + \
                [k for k in s['add'] if k not in movers and k in man]
            cache = {}
            for mk in movers:
                curves = sweep(S, man, s, mk, static, cache=cache)
                for c in collisions(curves):
                    c['moving'] = mk
                    c['path'] = to_path(s['approach'].get(mk)).tolist() if mk in s['approach'] else None
                    c['swingDeg'] = [pose['from'], pose['deg']] if pose and mk in pose['set'] else None
                    c['obstacleRole'] = 'context (ghost)' if c['obstacle'] in s['ctx'] else ('co-added part at final pose' if c['obstacle'] in s['add'] else 'shown')
                    c['obstacleLegitimatelyPresent'] = c['obstacle'] in legit
                    c['worst'] = worst(S, s, mk, c['obstacle'], c['atFraction'], cache)
                    if c['worst']['thicknessMedianMm'] > 0.1:
                        coll.append(c)
            # alternatives against legitimately present obstacles only, for straight unposed approaches
            alts = {}
            fl = s.get('flex')
            straight = lambda k: (k in s['approach'] and len(to_path(s['approach'][k])) == 2 and not (pose and k in pose['set'])
                                  and not (fl and (k in fl['set'] or k in fl['riders'])))
            bad_movers = sorted({c['moving'] for c in coll if c['obstacleLegitimatelyPresent'] and straight(c['moving'])})
            legit_static = [k for k in static if k in legit]
            if s['group'] and bad_movers:
                bad_movers = ['__group__']
            for mk in bad_movers:
                movers = list(s['approach']) if mk == '__group__' else [mk]
                vec0 = to_path(next(iter(s['approach'].values())) if mk == '__group__' else s['approach'][mk])[0]
                L = float(np.linalg.norm(vec0))
                tried = []
                for d in ([1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]):
                    vec = list(np.asarray(d, float) * L)
                    tot, hits = 0.0, set()
                    for m in movers:
                        cs = collisions(sweep_vec(S, man, m, vec, [o for o in legit_static if o not in movers], n=21))
                        for c in cs:
                            tot += c['maxExcessVolumeMm3']
                            hits.add(c['obstacle'])
                    tried.append({'vector': rnd(vec, 1), 'excessVolumeMm3': rnd(tot, 2), 'obstacles': sorted(hits)})
                tried.sort(key=lambda t: t['excessVolumeMm3'])
                alts[mk] = tried
            rec['alternatives'] = alts
            # lead-in: straight and waypoint approaches of unposed, unflexed movers, against what is really present
            leaders = [k for k in s['approach'] if k in man and not (pose and k in pose['set'])
                       and not (fl and (k in fl['set'] or k in fl['riders']))]
            if leaders:
                coll += lead_in(S, man, s, leaders, [o for o in legit_static if o not in s['approach']])
        rec['pathCollisions'] = coll
        report.append(rec)
        print(s['id'], 'premature', len(rec.get('drawnButNotPresent', [])), 'collisions', len(coll), file=sys.stderr, flush=True)
    (HERE / 'steps-raw.json').write_text(json.dumps({'samplesPerPath': N, 'volumeTolerance': VOL_TOL, 'steps': report}, indent=1))
    print(json.dumps({'steps': len(report), 'withPremature': sum(bool(r.get('drawnButNotPresent')) for r in report),
                      'pathCollisions': sum(len(r['pathCollisions']) for r in report)}))


if __name__ == '__main__':
    main()
