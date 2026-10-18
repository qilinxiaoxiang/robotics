#!/usr/bin/env python3
"""Does a V1.9 addition change the runtime jaw pose-cap table (guide/firmware/pi/jaw_pose_caps.json)?

The phase 1 runtime caps the jaw at min(25 deg, first CAD contact - 2 deg) for the head pose, with the first contact
read from jaw_pose_caps.json (null = clear to 27 deg). That table was built from the V1.8 parts by
extension-20261012-neck-audio/jaw-neck-check/scripts/pose_cap_sweep.py, whose part groups hold the printed parts and
servo cases only (no screw heads, no cables). The V1.9 lower clips, their raised screw heads and the neck bundle sit on
bodies the open jaw can reach:
  bracket group (neck_pitch body; depends on head_yaw and head_roll):
    clip      clip_bracket_v19 + the S11-horn-040 head raised 2.0 mm by its tab;
    bundle    the wire group (tube of radius groupRadiusMm, route-v19.json) between the bracket clip ties and the
              bracket guide, route points 6..8 (fixed on neck_pitch);
    span      the free span from the bracket guide (point 8, neck_pitch) to the head slot guide (point 9, jaw_soft),
              taut straight tube rebuilt for each head pose;
    v18heads  reference only: the eight V1.8 S11 horn screw heads (S11-horn-033..040, 4.0 x 1.5 mm) at their V1.8
              seats, which the V1.8 table does not model either;
  torso group (trunk_base body; depends on all four joints):
    clip      clip_torso_v19 + the S12-horn-025 head raised 2.0 mm;
    bundle    the wire group from the pack notch to the torso guide, route points 0..5 (fixed on trunk_base);
    v18heads  reference only: the eight V1.8 S12 horn screw heads (S12-horn-025..032).
The head clip, cap clip, retainer, amplifier and resistor ride on the head (jaw_soft); their contact with the jaw
depends on the jaw angle alone and is covered by scene_check.py. The free span from the torso guide (point 5) to the
bracket clip (point 6) changes with neck and head pitch; route_motion_v19.py covers it.

pose_cap_sweep.Sweep is reused unchanged (same jaw sphere cover and lower bound; contact = gap below 0.2 mm plus twice
the 0.05 mm jaw simplification, bisected to 0.25 deg), with its part lists replaced. Each category is scanned on its
own at every grid node of the table, from 0 up to the table value at that node (27 when null); a contact below it is a
new restriction (it would lower the cap there).
  bracket group: one scan per (head_yaw, head_roll) up to the largest table value over neck_pitch and head_pitch; a
                 contact then lowers every node of that (yaw, roll) whose table value is larger.
  torso group:   box search over the four-joint grid as pose_cap_sweep.search_group (a box is clear when the sphere
                 cover lower bound for all torso categories exceeds the joint motion bound plus the contact threshold);
                 each remaining node is scanned per category up to its own table value.
For each new contact the overlap region at 2 deg past contact is located (bounding box centre, body frame at q = 0).
Usage: jaw_cap_v19.py [bracket|torso|all]   Writes ../checks/jaw-cap-v19.json (merged per group).
"""
from __future__ import annotations

import json
import math
import sys
import time

import manifold3d as m3
import numpy as np

import ext_lib as E

JNC = E.EXT / 'jaw-neck-check' / 'scripts'
sys.path.insert(0, str(JNC))
import jn_lib  # noqa: E402
import pose_cap_sweep as PCS  # noqa: E402

TABLE = E.GUIDE / 'firmware' / 'pi' / 'jaw_pose_caps.json'
JOINTS = ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll')
CATS = {'neck_pitch': {'clip': ['clip_bracket_v19', 'raised_head_S11-horn-040'], 'bundle': ['bundle_np'],
                       'v18heads': [f'v18_head_S11-horn-0{i}' for i in range(33, 41)]},
        'trunk_base': {'clip': ['clip_torso_v19', 'raised_head_S12-horn-025'], 'bundle': ['bundle_tb'],
                       'v18heads': [f'v18_head_S12-horn-0{i:02d}' for i in range(25, 33)]}}
REFERENCE = ('v18heads',)


def tube(pts, r):
    P = [np.asarray(p, float) for p in pts]
    s = [m3.Manifold.sphere(r, 32).translate(p) for p in P]
    return m3.Manifold.batch_boolean([m3.Manifold.batch_hull([a, b]) for a, b in zip(s[:-1], s[1:])], m3.OpType.Add)


def head(F, sid, lift):
    r = F[sid]
    c, ax = np.array(r['center'], float), np.array(r['axis'], float)
    ax /= np.linalg.norm(ax)
    return E.cyl(c - lift * ax, -ax, r['headHeightMm'], r['headDiameterMm'] / 2, 48)


def parts():
    F = E.fasteners()
    rt = json.loads((E.OUT / 'route-v19.json').read_text())['routes'][0]
    pts, rad = rt['points'], rt['groupRadiusMm']
    S = {'clip_bracket_v19': E.stl_man(E.PARTS['clip_bracket_v19']), 'clip_torso_v19': E.stl_man(E.PARTS['clip_torso_v19']),
         'raised_head_S11-horn-040': head(F, 'S11-horn-040', 2.0), 'raised_head_S12-horn-025': head(F, 'S12-horn-025', 2.0),
         'bundle_np': tube([p[:3] for p in pts[6:9]], rad), 'bundle_tb': tube([p[:3] for p in pts[0:6]], rad)}
    assert all(p[3] == 'neck_pitch' for p in pts[6:9]) and all(p[3] == 'trunk_base' for p in pts[0:6])
    for i in range(33, 41):
        S[f'v18_head_S11-horn-0{i}'] = head(F, f'S11-horn-0{i}', 0.0)
    for i in range(25, 33):
        S[f'v18_head_S12-horn-0{i:02d}'] = head(F, f'S12-horn-0{i:02d}', 0.0)
    return S, pts, rad


def patch(S):
    mesh = {}
    for k, M in S.items():
        t = E.tm(M)
        mesh[k] = (np.asarray(t.vertices, float), np.asarray(t.faces))
    orig_load, orig_points = PCS.load_solid, PCS.cached_points

    def load(k):
        return mesh[k] if k in mesh else orig_load(k)

    def points(k, edge):
        return PCS.surface_points(*mesh[k], edge) if k in mesh else orig_points(k, edge)

    jn_lib.load_solid = load
    PCS.load_solid = load
    PCS.cached_points = points
    jn_lib.PARTS.clear()
    jn_lib.PARTS.update({b: [k for ks in c.values() for k in ks] for b, c in CATS.items()})


def table():
    d = json.loads(TABLE.read_text())
    axes = {j: np.array([a0 + i * st for i in range(n)]) for j, (a0, st, n) in d['axes_deg'].items()}
    t = np.array([[[[PCS.HI if v is None else v for v in r] for r in y] for y in p] for p in d['first_contact_deg']], float)
    return axes, t, E.sha(TABLE)


class Scanner:
    def __init__(self, sw):
        self.sw = sw
        self.all = {b: list(v) for b, v in jn_lib.PARTS.items()}

    def first(self, q, body, keys, hi):
        jn_lib.PARTS[body] = keys
        try:
            return self.sw.first_contact(q, body, hi=hi)
        finally:
            if body in self.all:
                jn_lib.PARTS[body] = self.all[body]
            else:
                del jn_lib.PARTS[body]

    def locate(self, q, body, keys, a):
        sw = self.sw
        T = sw.ck.T(q, min(a + 2.0, 40.0))
        J = sw.ck.man['jaw_frame'].transform(T['jaw'][:3, :].tolist())
        Tb = np.linalg.inv(T[body])
        out = []
        for k in keys:
            X = J ^ sw.ck.man[k].transform(T[body][:3, :].tolist())
            if X.volume() > 1e-4:
                X = X.transform(Tb[:3, :].tolist())
                lo, hi = np.array(E.bbox(X))
                out.append({'part': k, 'overlapMm3': round(X.volume(), 3), 'centre': np.round((lo + hi) / 2, 2).tolist(),
                            'size': np.round(hi - lo, 2).tolist()})
        return out


def bracket(sc, axes, t, pts, rad):
    sw = sc.sw
    cats = dict(CATS['neck_pitch'], span=['span_P8_P9'])
    res = {c: {'newContacts': [], 'tableNodesLowered': 0} for c in cats}
    comb = np.full(t.shape, np.inf)
    lim = t.max(axis=(0, 1))
    p8, p9 = np.array(pts[8][:3], float), np.array(pts[9][:3], float)
    for iy, y in enumerate(axes['head_yaw']):
        for ir, r in enumerate(axes['head_roll']):
            L = float(lim[iy, ir])
            if L <= 0:
                continue
            q = {'head_yaw': float(y), 'head_roll': float(r)}
            T = sw.ck.T(q, 0.0)
            p9n = (np.linalg.inv(T['neck_pitch']) @ T['jaw_soft'] @ np.r_[p9, 1.0])[:3]
            sw.ck.man['span_P8_P9'] = tube([p8, p9n], rad)
            near = not sw.clear(q, 'neck_pitch', sw.gap)
            for c, keys in cats.items():
                if c != 'span' and not near:
                    continue
                a, part = sc.first(q, 'neck_pitch', keys, L)
                if a is None:
                    continue
                sub = t[:, :, iy, ir]
                n = int((sub > a + 1e-9).sum())
                if c not in REFERENCE:
                    comb[:, :, iy, ir] = np.minimum(comb[:, :, iy, ir], a)
                res[c]['tableNodesLowered'] += n
                res[c]['newContacts'].append({'head_yaw': float(y), 'head_roll': float(r), 'firstContactDeg': a,
                                              'part': part, 'largestTableDeg': L, 'tableNodesLowered': n,
                                              'at': sc.locate(q, 'neck_pitch', keys, a)})
                print('bracket', c, y, r, 'contact', a, part, 'table max', L, 'nodes lowered', n, flush=True)
    return res, comb


def torso(sc, axes, t):
    sw = sc.sw
    cats = CATS['trunk_base']
    res = {c: {'newContacts': [], 'tableNodesLowered': 0} for c in cats}
    stats = {'boxesCleared': 0, 'nodesClearedByBox': 0, 'nodesScanned': 0, 'nodesSkippedClosed': 0}
    comb = np.full(t.shape, np.inf)
    n = [len(axes[j]) for j in JOINTS]
    stack = [tuple((0, k - 1) for k in n)]
    t0 = time.time()
    while stack:
        box = stack.pop()
        sl = tuple(slice(b0, b1 + 1) for b0, b1 in box)
        count = int(np.prod([b1 - b0 + 1 for b0, b1 in box]))
        if t[sl].max() <= 0.0:
            stats['nodesSkippedClosed'] += count
            continue
        lo = {j: axes[j][b0] for j, (b0, _) in zip(JOINTS, box)}
        hi = {j: axes[j][b1] for j, (_, b1) in zip(JOINTS, box)}
        c = {j: 0.5 * (lo[j] + hi[j]) for j in JOINTS}
        half = {j: math.radians(0.5 * (hi[j] - lo[j])) for j in JOINTS}
        need = sum(sw.R[j] * half[j] for j in JOINTS) + sw.gap
        if sw.clear(c, 'trunk_base', need):
            stats['boxesCleared'] += 1
            stats['nodesClearedByBox'] += count
            continue
        if count == 1:
            idx = tuple(b0 for b0, _ in box)
            L = float(t[idx])
            stats['nodesScanned'] += 1
            for cat, keys in cats.items():
                a, part = sc.first(c, 'trunk_base', keys, L)
                if a is None:
                    continue
                if cat not in REFERENCE:
                    comb[idx] = min(comb[idx], a)
                res[cat]['tableNodesLowered'] += 1
                res[cat]['newContacts'].append({**{j: float(c[j]) for j in JOINTS}, 'firstContactDeg': a, 'part': part,
                                                'tableDeg': L, 'at': sc.locate(c, 'trunk_base', keys, a)})
                print('torso', cat, [c[j] for j in JOINTS], 'contact', a, part, 'table', L, flush=True)
            continue
        j = max((j for j, (b0, b1) in zip(JOINTS, box) if b1 > b0), key=lambda j: sw.R[j] * half[j])
        k = JOINTS.index(j)
        b0, b1 = box[k]
        m = (b0 + b1) // 2
        for s in ((b0, m), (m + 1, b1)):
            nb = list(box)
            nb[k] = s
            stack.append(tuple(nb))
        if time.time() - t0 > 60 and stats['nodesScanned'] % 200 == 0:
            print('torso progress', stats, f'{time.time() - t0:.0f}s', flush=True)
    stats['seconds'] = round(time.time() - t0, 1)
    return res, comb, stats


def summarize(t, comb):
    lowered = comb < t - 1e-9
    new = np.where(lowered, comb, t)
    cap = np.minimum(25.0, new - 2.0)
    old = np.minimum(25.0, t - 2.0)
    return {'tableNodesLowered': int(lowered.sum()),
            'lowestNewContactDeg': float(comb[lowered].min()) if lowered.any() else None,
            'capNodesBelow18_33Deg': {'v18': int((old < 18.33).sum()), 'v19': int((cap < 18.33).sum())},
            'capNodesHeldClosed': {'v18': int((old < 5.0).sum()), 'v19': int((cap < 5.0).sum())}}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'
    S, pts, rad = parts()
    patch(S)
    del S
    axes, t, tsha = table()
    sw = PCS.Sweep(simplify=True)
    sc = Scanner(sw)
    out_path = E.OUT / 'checks' / 'jaw-cap-v19.json'
    out = json.loads(out_path.read_text()) if out_path.exists() else {}
    out = {k: v for k, v in out.items() if k in ('bracket', 'torso', 'spans')}
    out.update({'_method': __doc__.strip(), 'table': str(TABLE), 'tableSha256': tsha, 'categories': CATS,
                'referenceCategories': list(REFERENCE), 'groupRadiusMm': rad,
                'contactRule': {'gapMm': sw.gap, 'refineDeg': PCS.REFINE, 'clearToDeg': PCS.HI},
                'clipSha256': {k: E.sha(E.PARTS[k]) for k in ('clip_torso_v19', 'clip_bracket_v19')},
                'routeSha256': E.sha(E.OUT / 'route-v19.json')})
    combs = {}
    for g in (('bracket', 'torso') if mode == 'all' else (mode,)):
        t0 = time.time()
        if g == 'bracket':
            res, comb = bracket(sc, axes, t, pts, rad)
            stats = {}
        else:
            res, comb, stats = torso(sc, axes, t)
        np.save(E.SCRATCH / f'jaw-cap-v19-{g}-comb.npy', comb)
        combs[g] = comb
        out[g] = {'categories': res, **stats, 'summaryNewParts': summarize(t, comb),
                  'elapsedSeconds': round(time.time() - t0, 1)}
        print(g, {c: r['tableNodesLowered'] for c, r in res.items()}, out[g]['summaryNewParts'], flush=True)
    allc = [np.load(E.SCRATCH / f'jaw-cap-v19-{g}-comb.npy') for g in ('bracket', 'torso', 'spans')
            if (E.SCRATCH / f'jaw-cap-v19-{g}-comb.npy').exists()]
    if allc:
        out['summaryAll'] = summarize(t, np.minimum.reduce(allc))
        print('all', out['summaryAll'], flush=True)
    E.jdump(out, out_path)


if __name__ == '__main__':
    main()
