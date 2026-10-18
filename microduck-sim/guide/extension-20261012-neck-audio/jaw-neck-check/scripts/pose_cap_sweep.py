#!/usr/bin/env python3
"""First jaw contact angle on a head-pose grid, for the pose-dependent jaw cap in guide/firmware/pi/jaw_limits.json.

Grid (the runtime's calibrated joint ranges, calibration.template.json = MJCF): head_pitch -90..90 step 5,
head_yaw -170..170 step 10, head_roll -25..25 step 5; neck_pitch -90..60 step 15 for the torso parts only.
Parts and kinematics as jn_lib (V1.8 jaw frame vs the head-pitch bracket group, motor 11/12 and neck links, torso).
Each part group depends only on the joints between it and the jaw (jn_lib.DEPENDS), so it gets its own grid:
bracket group (head_yaw, head_roll), neck group (head_pitch, head_yaw, head_roll), torso (all four).

Method, per group:
  1. Rigorous pre-filter. Part surfaces are sampled by longest-edge bisection (every surface point within E_PART of
     a sample, KD-tree). The jaw swept over 0..HI deg is covered by spheres: jaw surface samples (within E_JAW) at 1 deg
     steps (an intermediate angle moves a point at most r_jaw * 0.5 deg) binned into CUBE mm cubes. The lower bound of
     the jaw-to-part gap over the whole sweep at a pose is min over spheres (KD distance of centre - radius) - E_PART.
  2. Box search over the group's joint grid. For a box with centre c and half-widths h, every sphere centre moves at
     most sum_j R_j h_j relative to the part (R_j bounds the distance of the swept jaw from joint j's anchor, built
     outward from the roll anchor). A box whose centre lower bound exceeds that motion plus the contact threshold is
     clear for every pose inside it (first contact >= HI); otherwise it is split, down to single grid nodes.
  3. Each remaining node: the jaw is scanned from 0 deg with steps no larger than the exact gap allows (a jaw point
     moves at most r_jaw per radian of jaw), then bisected to 0.25 deg. Meshes are simplified to SIMPLIFY mm and the
     contact threshold widened by twice that, which only moves contact earlier (checked against the full meshes).
     Result: first contact angle, or null when clear to HI. Exact gaps use a 10 mm search radius.
Clear boxes hold for every pose inside them; contact values are computed at the grid nodes.
Torso group: the cap table keeps min(bracket, neck, torso) per (neck_pitch, head_pitch, head_yaw, head_roll), so a
torso node is scanned only up to the smallest bracket/neck contact for its head pose; a node with nothing found below
that limit records it as scanLimitDeg (contact, if any, is at or beyond it), and head poses whose bracket/neck contact
is already 0 are skipped (scanLimitDeg 0). The table minimum is unchanged by this. An existing ../pose-grid-torso.json
seeds the run: its exact nodes are kept and nodes scanned to a lower limit are scanned on from that limit.
Boxes are tested first against a coarse sphere cover (CUBE_COARSE) and then the fine one.
Usage: pose_cap_sweep.py bench | check [n] | <group> [pitch_lo pitch_hi]   (group: bracket, neck, torso)
Writes ../pose-grid-<group>[_<lo>_<hi>].json; check writes ../pose-grid-check.json. Group runs checkpoint every
CHECKPOINT_S seconds to $TMPDIR/pose-grid-<group>[_<lo>_<hi>].partial.json and resume from it after a stop.
"""
from __future__ import annotations

import json
import math
import os
import sys
import tempfile
import time

import numpy as np
from pathlib import Path

from jn_lib import OUT, PARTS, Checker, jdump
from nr_lib import JAW_AXIS, JAW_PIVOT, T_about, load_solid

HI = 27.0                 # contact at or beyond HI leaves the full 25 deg cap after the 2 deg margin
CONTACT_GAP = 0.2         # jn_lib.cls: contact below 0.2 mm gap
SIMPLIFY = 0.05           # mm; node scans use simplified meshes with threshold CONTACT_GAP + 2 * SIMPLIFY
SWEEP_STEP = 1.0
REFINE = 0.25
SEARCH = 10.0
E_PART, E_JAW, CUBE, CUBE_COARSE = 1.5, 1.0, 5.0, 15.0
GRID = {'neck_pitch': (-90, 60, 15), 'head_pitch': (-90, 90, 5), 'head_yaw': (-170, 170, 10), 'head_roll': (-25, 25, 5)}
GROUPS = {'bracket': ('neck_pitch', ('head_yaw', 'head_roll')),
          'neck': ('neck', ('head_pitch', 'head_yaw', 'head_roll')),
          'torso': ('trunk_base', ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll'))}
CHAIN = ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll')   # proximal to distal


def nodes(j):
    lo, hi, step = GRID[j]
    return np.arange(lo, hi + 1e-9, step, dtype=float)


def surface_points(v, f, edge, chunk=4000):
    """Vertices of a longest-edge bisection of every triangle down to edges <= edge: every surface point lies within
    edge of a returned point (each final triangle is within its longest edge of each of its vertices)."""
    v, f = np.asarray(v, float), np.asarray(f)
    out = [np.round(v, 3).astype(np.float32)]
    for s0 in range(0, len(f), chunk):
        tri = v[f[s0:s0 + chunk]]
        mids = []
        while len(tri):
            e = np.linalg.norm(tri[:, [1, 2, 0]] - tri, axis=2)          # edge k joins vertex k and k+1
            split = e.max(1) > edge
            tri, e = tri[split], e[split]
            if not len(tri):
                break
            k = e.argmax(1)
            idx = np.arange(len(tri))
            a, b, c = tri[idx, k], tri[idx, (k + 1) % 3], tri[idx, (k + 2) % 3]
            m = 0.5 * (a + b)
            mids.append(np.round(m, 3).astype(np.float32))
            tri = np.concatenate([np.stack([a, m, c], 1), np.stack([m, b, c], 1)])
        if mids:
            out.append(np.unique(np.vstack(mids), axis=0))
    return np.unique(np.vstack(out), axis=0).astype(float)


def cached_points(key, edge):
    import os
    from pathlib import Path
    path = Path(os.environ.get('TMPDIR', '/tmp')) / f'pose-cap-points-{key}-{edge}.npy'
    if path.exists():
        return np.load(path)
    pts = surface_points(*load_solid(key), edge)
    np.save(path, pts)
    return pts


class Sweep:
    def __init__(self, simplify=True, keep_full=False):
        from scipy.spatial import cKDTree
        self.ck = Checker()
        self.full = dict(self.ck.man)
        if simplify:
            self.ck.man = {k: (m.simplify(SIMPLIFY) if m.num_tri() > 5000 else m) for k, m in self.full.items()}
        self.gap = CONTACT_GAP + (2 * SIMPLIFY if simplify else 0.0)
        if not keep_full:
            self.full = None
        jv, jf = load_solid('jaw_frame')
        d = jv - JAW_PIVOT
        self.r_jaw = float(np.linalg.norm(d - np.outer(d @ JAW_AXIS, JAW_AXIS), axis=1).max())   # mm from jaw axis
        js = cached_points('jaw_frame', E_JAW)
        swept = np.vstack([js @ T[:3, :3].T + T[:3, 3] for T in
                           (T_about(JAW_PIVOT, JAW_AXIS, math.radians(a)) for a in np.arange(0.0, HI + 1e-9, SWEEP_STEP))])
        cells = np.unique(np.floor(swept / CUBE).astype(int), axis=0)
        self.centres = (cells + 0.5) * CUBE                      # head frame (q = 0)
        self.r_sphere = CUBE * math.sqrt(3) / 2 + E_JAW + self.r_jaw * math.radians(SWEEP_STEP / 2)
        coarse = np.unique(np.floor(swept / CUBE_COARSE).astype(int), axis=0)
        self.coarse = ((coarse + 0.5) * CUBE_COARSE, CUBE_COARSE * math.sqrt(3) / 2 + E_JAW + self.r_jaw * math.radians(SWEEP_STEP / 2))
        self.tree = {}
        for body, keys in PARTS.items():
            pts = np.vstack([cached_points(k, E_PART) for k in keys])
            self.tree[body] = cKDTree(pts)
            self.points = getattr(self, 'points', {}) | {body: len(pts)}
        anc = self.ck.fk.anchors()
        a = {j: anc[j][0] for j in CHAIN}
        R = {'head_roll': float(np.linalg.norm(self.centres - a['head_roll'], axis=1).max()) + self.r_sphere}
        R['head_yaw'] = float(np.linalg.norm(a['head_roll'] - a['head_yaw'])) + R['head_roll']
        R['head_pitch'] = float(np.linalg.norm(a['head_yaw'] - a['head_pitch'])) + R['head_yaw']
        R['neck_pitch'] = float(np.linalg.norm(a['head_pitch'] - a['neck_pitch'])) + R['head_pitch']
        self.R = R
        self.lb_evals = 0
        self.jaw_evals = 0

    def lower_bound(self, qdeg, body, enough=np.inf, coarse=False):
        """Lower bound of the gap between the jaw swept over 0..HI and the body's parts at pose qdeg (true geometry).
        Distances beyond `enough` are not resolved: the result is then at least `enough`. coarse uses the 15 mm cover
        (fewer, larger spheres: cheaper and looser)."""
        centres, radius = self.coarse if coarse else (self.centres, self.r_sphere)
        T = self.ck.T(qdeg, 0.0)
        M = np.linalg.inv(T[body]) @ T['jaw_soft']             # head frame -> body's q = 0 frame
        c = centres @ M[:3, :3].T + M[:3, 3]
        self.lb_evals += 1
        dist, _ = self.tree[body].query(c, k=1, distance_upper_bound=enough + radius + E_PART + 1e-6)
        return min(float(dist.min()) - radius - E_PART, enough + 1e-6)

    def clear(self, qdeg, body, need):
        """True if the jaw swept over 0..HI stays more than `need` from the body's parts at qdeg."""
        return self.lower_bound(qdeg, body, need + 1.0, coarse=True) > need or self.lower_bound(qdeg, body, need + 1.0) > need

    def jaw_gap(self, qdeg, body, jaw, man=None):
        man = man or self.ck.man
        T = self.ck.T(qdeg, jaw)
        J = man['jaw_frame'].transform(T['jaw'][:3, :].tolist())
        self.jaw_evals += 1
        best, part = SEARCH, None
        for k in PARTS[body]:
            g = float(J.min_gap(man[k].transform(T[body][:3, :].tolist()), SEARCH))
            if g < best:
                best, part = g, k
        return best, part

    def first_contact(self, qdeg, body, man=None, gap=None, hi=HI, lo=0.0):
        """First contact angle scanning the jaw from lo to hi (deg), or (None, None) when clear up to hi. A start lo > 0
        must already be known clear from 0 to lo; contact at lo is then reported as lo."""
        gap = self.gap if gap is None else gap
        a, prev = float(lo), None
        while True:
            g, part = self.jaw_gap(qdeg, body, a, man)
            if g < gap:
                if prev is None:
                    return 0.0, part
                lo, hi, hit = prev, a, part
                while hi - lo > REFINE:
                    m = 0.5 * (lo + hi)
                    gm, pm = self.jaw_gap(qdeg, body, m, man)
                    if gm < gap:
                        hi, hit = m, pm
                    else:
                        lo = m
                return round(hi, 2), hit
            if a >= hi:
                return None, None
            prev = a
            a = min(hi, a + max(REFINE, math.degrees((g - gap) / self.r_jaw)))


CHECKPOINT_S = 60.0


def _load_checkpoint(path, axes):
    try:
        d = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}, None
    if d.get('axesDeg') != {j: a.tolist() for j, a in axes.items()}:
        return {}, None
    return {tuple(k): v for k, v in d['values']}, d['stats']


def _save_checkpoint(path, axes, values, stats):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps({'axesDeg': {j: a.tolist() for j, a in axes.items()}, 'stats': stats,
                               'values': [[list(k), v] for k, v in values.items()]}))
    os.replace(tmp, path)


def known_contact():
    """{(head_pitch, head_yaw, head_roll): smallest contact (deg) of the bracket and neck grids, HI when clear}."""
    b = json.loads((OUT / 'pose-grid-bracket.json').read_text())
    n = json.loads((OUT / 'pose-grid-neck.json').read_text())
    bd = {(x['head_yaw'], x['head_roll']): x['firstContactJawDeg'] for x in b['nodes']}
    out = {}
    for x in n['nodes']:
        k = (x['head_pitch'], x['head_yaw'], x['head_roll'])
        out[k] = min([HI] + [v for v in (x['firstContactJawDeg'], bd[k[1:]]) if v is not None])
    return out


def search_group(sw, group, pitch_range=None, log=sys.stderr, ckpt=None):
    body, joints = GROUPS[group]
    axes = {j: nodes(j) for j in joints}
    if pitch_range and 'head_pitch' in axes:
        p = axes['head_pitch']
        axes['head_pitch'] = p[(p >= pitch_range[0] - 1e-9) & (p <= pitch_range[1] + 1e-9)]
    values = {}          # node tuple (degrees) -> [contact deg or None, part]
    stats = {'boxesCleared': 0, 'nodesClearedByBox': 0, 'nodesScanned': 0, 'nodesClearAtNode': 0}
    if ckpt is not None:
        done, old = _load_checkpoint(ckpt, axes)
        if old:
            values, stats = done, old
            print(group, 'resumed', len(values), 'nodes from', ckpt, file=log, flush=True)
    best, start = None, {}
    if group == 'torso':                 # bracket/neck contact per head pose, as a (pitch, yaw, roll) index array
        known = known_contact()
        hp = [axes[j] for j in joints[1:]]
        best = np.array([[[known[(float(p), float(y), float(r))] for r in hp[2]] for y in hp[1]] for p in hp[0]])
        seed = OUT / 'pose-grid-torso.json'
        if seed.exists() and pitch_range is None:      # a checkpoint, when resumed, already holds the kept nodes
            old = json.loads(seed.read_text())
            if old['axesDeg'] == {j: a.tolist() for j, a in axes.items()}:
                for n in old['nodes']:
                    key = tuple(float(n[j]) for j in joints)
                    limit = known[key[1:]]
                    s = n.get('scanLimitDeg')
                    if n['firstContactJawDeg'] is None and s is not None and s < limit - 1e-9:
                        start[key] = float(s)          # clear from 0 to s; scan on to the bracket/neck limit
                    elif key not in values:
                        values[key] = [n['firstContactJawDeg'], n['part']] + ([s] if s is not None else [])
                print(group, 'seeded', len(values), 'nodes from', seed, '; rescanning', len(start), file=log, flush=True)
    t0, last, saved = time.time(), len(values), time.time()
    stack = [tuple((0, len(axes[j]) - 1) for j in joints)]
    while stack:
        box = stack.pop()
        if values and all(tuple(float(axes[j][b[0] + i]) for j, b, i in zip(joints, box, idx)) in values
                          for idx in np.ndindex(*[b[1] - b[0] + 1 for b in box])):
            continue
        if best is not None and best[tuple(slice(b[0], b[1] + 1) for b in box[1:])].max() <= 0.0:
            for idx in np.ndindex(*[b[1] - b[0] + 1 for b in box]):
                k = tuple(float(axes[j][b[0] + i]) for j, b, i in zip(joints, box, idx))
                if k not in values:
                    values[k] = [None, None, 0.0]
                    stats['nodesSkippedKnownZero'] = stats.get('nodesSkippedKnownZero', 0) + 1
            continue
        lo = {j: axes[j][b[0]] for j, b in zip(joints, box)}
        hi = {j: axes[j][b[1]] for j, b in zip(joints, box)}
        centre = {j: 0.5 * (lo[j] + hi[j]) for j in joints}
        half = {j: math.radians(0.5 * (hi[j] - lo[j])) for j in joints}
        need = sum(sw.R[j] * half[j] for j in joints) + sw.gap
        count = int(np.prod([b[1] - b[0] + 1 for b in box]))
        if sw.clear(centre, body, need):
            stats['boxesCleared'] += 1
            stats['nodesClearedByBox'] += count
            for idx in np.ndindex(*[b[1] - b[0] + 1 for b in box]):
                values.setdefault(tuple(float(axes[j][b[0] + i]) for j, b, i in zip(joints, box, idx)), [None, None])
        elif count == 1:
            key = tuple(float(centre[j]) for j in joints)
            if best is None:
                a, part = sw.first_contact(centre, body)
                values[key] = [a, part]
            else:
                limit = float(best[tuple(b[0] for b in box[1:])])
                a, part = sw.first_contact(centre, body, hi=limit, lo=min(start.get(key, 0.0), limit))
                values[key] = [a, part] if a is not None else [None, None] + ([limit] if limit < HI else [])
            stats['nodesScanned'] += 1
            stats['nodesClearAtNode'] += a is None
        else:
            j = max((j for j, b in zip(joints, box) if b[1] > b[0]), key=lambda j: sw.R[j] * half[j])
            k = joints.index(j)
            b0, b1 = box[k]
            mid = (b0 + b1) // 2
            for sub in ((b0, mid), (mid + 1, b1)):
                nb = list(box)
                nb[k] = sub
                stack.append(tuple(nb))
        if len(values) - last >= 500:
            last = len(values)
            print(group, last, 'nodes', f'{time.time() - t0:.0f}s', sw.lb_evals, 'bounds', sw.jaw_evals, 'jaw evals',
                  file=log, flush=True)
        if ckpt is not None and time.time() - saved > CHECKPOINT_S:
            _save_checkpoint(ckpt, axes, values, stats)
            saved = time.time()
    return axes, values, stats


def check(sw, rng=np.random.default_rng(20261013), n=60):
    """Simplified-mesh scans against the full meshes, and the pre-filter against exact gaps, at n random poses and, per
    group, at n grid nodes where the sweep found contact."""
    rows = []
    poses = [({j: float(rng.uniform(*GRID[j][:2])) for j in CHAIN}, tuple(GROUPS)) for _ in range(n)]
    for group in GROUPS:
        path = OUT / f'pose-grid-{group}.json'
        if path.exists():
            hit = [x for x in json.loads(path.read_text())['nodes'] if x['firstContactJawDeg']]
            for i in rng.choice(len(hit), size=min(n, len(hit)), replace=False):
                poses.append(({j: float(hit[i].get(j, 0.0)) for j in CHAIN}, (group,)))
    for q, groups in poses:
        for group in groups:
            body = GROUPS[group][0]
            simp, _ = sw.first_contact(q, body)
            full, part = sw.first_contact(q, body, man=sw.full, gap=CONTACT_GAP)
            lb = sw.lower_bound(q, body)
            lbc = sw.lower_bound(q, body, coarse=True)
            exact = min(sw.jaw_gap(q, body, a, sw.full)[0] for a in np.arange(0.0, HI + 1e-9, 1.0))
            rows.append({'q': {j: round(v, 2) for j, v in q.items()}, 'group': group, 'simplifiedDeg': simp,
                         'fullDeg': full, 'part': part, 'lowerBoundMm': round(lb, 2), 'coarseLowerBoundMm': round(lbc, 2),
                         'exactMinGapMm': round(exact, 2)})
    bad_simp = [r for r in rows if r['fullDeg'] is not None and (r['simplifiedDeg'] is None or r['simplifiedDeg'] > r['fullDeg'] + 1e-6)]
    bad_lb = [r for r in rows if max(r['lowerBoundMm'], r['coarseLowerBoundMm']) > r['exactMinGapMm'] + 1e-6
              and r['exactMinGapMm'] < SEARCH]
    return {'rows': rows, 'simplifiedLaterThanFull': bad_simp, 'lowerBoundAboveExact': bad_lb}


def main():
    t0 = time.time()
    mode = sys.argv[1]
    sw = Sweep(keep_full=mode == 'check')
    info = {'partSamples': sw.points, 'rJawMm': round(sw.r_jaw, 2), 'sphereRadiusMm': round(sw.r_sphere, 3), 'spheres': len(sw.centres),
            'jointRadiusBoundMm': {j: round(r, 1) for j, r in sw.R.items()}, 'scanContactGapMm': sw.gap,
            'simplifyMm': SIMPLIFY, 'setupSeconds': round(time.time() - t0, 1)}
    print(info, file=sys.stderr, flush=True)
    if mode == 'bench':
        for q in ({'head_yaw': 60.0}, {'neck_pitch': -82.0, 'head_pitch': -38.0}, {'head_pitch': -45.0, 'head_yaw': 140.0},
                  {'head_pitch': 80.0, 'neck_pitch': 12.0}, {'head_pitch': 0.0}):
            for group, (body, _) in GROUPS.items():
                t = time.time()
                lb = sw.lower_bound(q, body)
                t1 = time.time()
                a, part = sw.first_contact(q, body)
                print(q, group, 'lower bound', round(lb, 1), f'{(t1 - t) * 1000:.1f} ms', 'first contact', a, part,
                      f'{(time.time() - t1) * 1000:.0f} ms', file=sys.stderr, flush=True)
        return
    if mode == 'check':
        res = check(sw, n=int(sys.argv[2]) if len(sys.argv) > 2 else 60)
        jdump({'_method': check.__doc__, **info, **res, 'elapsedSeconds': round(time.time() - t0, 1)},
              OUT / 'pose-grid-check.json')
        print('check', len(res['rows']), 'simplified later', len(res['simplifiedLaterThanFull']), 'bound above exact',
              len(res['lowerBoundAboveExact']), file=sys.stderr, flush=True)
        return
    pr = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else None
    name = f'pose-grid-{mode}' + (f'_{int(pr[0])}_{int(pr[1])}' if pr else '') + '.json'
    ckpt = Path(tempfile.gettempdir()) / name.replace('.json', '.partial.json')
    axes, values, stats = search_group(sw, mode, pr, ckpt=ckpt)
    body, joints = GROUPS[mode]
    rows = [dict(zip(joints, k), firstContactJawDeg=v[0], part=v[1], **({'scanLimitDeg': v[2]} if len(v) > 2 else {}))
            for k, v in sorted(values.items())]
    jdump({'_method': __doc__.strip(), 'group': mode, 'body': body, 'joints': joints, 'parts': PARTS[body],
           'axesDeg': {j: axes[j].tolist() for j in joints}, 'hiDeg': HI, 'contactGapMm': CONTACT_GAP, **info,
           'stats': stats, 'boundEvaluations': sw.lb_evals, 'jawEvaluations': sw.jaw_evals,
           'elapsedSeconds': round(time.time() - t0, 1), 'nodes': rows}, OUT / name)
    print(mode, stats, sw.lb_evals, sw.jaw_evals, f'{time.time() - t0:.0f}s', file=sys.stderr, flush=True)
    ckpt.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
