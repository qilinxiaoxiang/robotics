#!/usr/bin/env python3
"""Jaw opening at first contact for the real pickup postures, and the joint-angle margin around them.

(a) postures: median head joints per phase of the accepted simulated pickups (table = jaw-PPO training task,
    ground = ground-ball transfer, household = household pick), plus each family's extreme release/lift rows;
    jaw swept 0..40 deg (2 deg scan, 0.25 deg bisection), all parts below the head; nearest part at the training jaw
    maximum (0.32 rad = 18.33 deg) and at 40 deg, with overlap location on the jaw.
(b) neck-independent map (head-pitch bracket group + motor 11/12 and neck links): head_pitch -90..90 step 5 x
    head_yaw {-25,-15,-5,0,5,15,25,35} at roll 0, and head_roll {-25,-10,10,25} at yaw 0.
(c) torso map: neck_pitch {-90,-75,-60,-45,-30,-15,0,12,25,40,60} x head_pitch -90..90 step 5, yaw 0, roll 0.
(d) release: the head-tip release posture (neck_pitch 12, the ground/household release), head_pitch 50..90 in 1 deg
    steps at one head_yaw per run (-4, 0, 4) x head_roll 0, all parts below the head: jaw first contact; plus the rest of the head
    (jaw_neck_check HEAD_REST, jaw closed) against the same parts, to tell a jaw collision from a blocked head pose.
Usage: margin.py postures|neck|torso|release <yaw>; writes ../margin-<section>.json (release: ../margin-release-yaw<yaw>.json).
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np

from jn_lib import JOINTS, OUT, TRAIN_JAW_MAX_DEG, Checker, jdump

ALL = ('neck_pitch', 'neck', 'trunk_base')


def postures():
    z = np.load(OUT / 'postures-rows.npz')
    Q, fam, ph, tid = z['q'], z['family'], z['phase'], z['trace']
    tr = json.loads((OUT / 'postures.json').read_text())['traces']
    acc = np.array([bool(tr[k]['accepted']) for k in tid])
    out = []
    for f in ('table', 'ground', 'household'):
        for p in ('reach', 'align', 'clamp', 'lift', 'hold', 'carried', 'release'):
            m = (fam == f) & (ph == p) & acc
            if m.sum() < 10:
                continue
            med = np.median(Q[m], 0)
            out.append({'label': f'{f} {p} (median of {int(m.sum())} accepted rows)', 'family': f, 'phase': p,
                        'q': dict(zip(JOINTS, np.round(med[:4], 1).tolist())), 'simJawDeg': round(float(med[4]), 1)})
        m = (fam == f) & acc
        for j, sgn in (('head_pitch', 1), ('head_pitch', -1), ('head_yaw', 1), ('head_yaw', -1)):
            i = JOINTS.index(j)
            r = np.argmax(sgn * Q[m, i])
            row = Q[m][r]
            out.append({'label': f'{f} accepted row with {"max" if sgn > 0 else "min"} {j}', 'family': f,
                        'phase': str(ph[m][r]), 'q': dict(zip(JOINTS, np.round(row[:4], 1).tolist())),
                        'simJawDeg': round(float(row[4]), 1)})
    return out


def main():
    t0 = time.time()
    sec = sys.argv[1]
    ck = Checker()
    res = {'_method': __doc__.strip(), 'section': sec, 'trainJawMaxDeg': round(TRAIN_JAW_MAX_DEG, 2)}
    if sec == 'postures':
        res['postures'] = posture_rows(ck, t0)
    elif sec == 'neck':
        res['neckMap'] = neck_map(ck, t0)
    elif sec == 'torso':
        res['torsoMap'] = torso_map(ck, t0)
    elif sec == 'release':
        res['releaseMap'] = release_map(t0, float(sys.argv[2]))
    jdump(res, OUT / (f'margin-{sec}.json' if sec != 'release' else f'margin-release-yaw{sys.argv[2]}.json'))


def posture_rows(ck, t0):
    rows = []
    for p in postures():
        a, hit = ck.first_contact(p['q'], ALL, step=2.0)
        at = {}
        for jaw in (p['simJawDeg'], TRAIN_JAW_MAX_DEG, 40.0):
            r = ck.jaw_vs(ck.T(p['q'], jaw), ALL, detail=True)
            at[f'{jaw:.2f}'] = r[:2]
        rows.append({**p, 'firstContactJawDeg': a, 'firstContactPart': hit, 'nearestAt': at})
        print(p['label'], p['q'], 'first', a, hit and hit['part'], f'{time.time() - t0:.0f}s', file=sys.stderr, flush=True)
    return rows


def neck_map(ck, t0):
    grid = []
    for y in (-25, -15, -5, 0, 5, 15, 25, 35):
        for h in range(-90, 91, 5):
            grid.append({'head_pitch': h, 'head_yaw': y, 'head_roll': 0.0})
    for r in (-25, -10, 10, 25):
        for h in range(-90, 91, 5):
            grid.append({'head_pitch': h, 'head_yaw': 0.0, 'head_roll': r})
    nmap = []
    for g in grid:
        a, hit = ck.first_contact({'neck_pitch': 0.0, **g}, ('neck_pitch', 'neck'), step=2.0)
        nmap.append({**g, 'firstContactJawDeg': a, 'part': hit and hit['part'], 'class': hit and hit['class']})
    print('neck map', f'{time.time() - t0:.0f}s', file=sys.stderr, flush=True)
    return nmap


def torso_map(ck, t0):
    tmap = []
    for n in (-90, -75, -60, -45, -30, -15, 0, 12, 25, 40, 60):
        for h in range(-90, 91, 5):
            a, hit = ck.first_contact({'neck_pitch': n, 'head_pitch': h}, ('trunk_base',), step=2.0)
            tmap.append({'neck_pitch': n, 'head_pitch': h, 'firstContactJawDeg': a, 'part': hit and hit['part'],
                         'class': hit and hit['class']})
    print('torso map', f'{time.time() - t0:.0f}s', file=sys.stderr, flush=True)
    return tmap


def release_map(t0, yaw):
    from jn_lib import HEAD_REST, PARTS, BODY_OF
    ck = Checker(extra=HEAD_REST)
    out = []
    for y in (yaw,):
        for h in range(50, 91):
            q = {'neck_pitch': 12.0, 'head_pitch': float(h), 'head_yaw': y, 'head_roll': 0.0}
            a, hit = ck.first_contact(q, ALL, step=1.0)
            T = ck.T(q, 0.0)
            head = []
            for k in HEAD_REST:
                Hm = ck.man[k].transform(T[BODY_OF[k]][:3, :].tolist())
                for b, ks in PARTS.items():
                    if BODY_OF[k] == 'yaw_roll_motion' and b == 'neck_pitch':
                        continue      # the yaw link's own bearing seat on the bracket
                    for kb in ks:
                        g = float(Hm.min_gap(ck.man[kb].transform(T[b][:3, :].tolist()), 2.0))
                        if g < 0.2:
                            head.append({'head': k, 'part': kb, 'gapMm': round(g, 3),
                                         'overlapMm3': round(float((Hm ^ ck.man[kb].transform(T[b][:3, :].tolist())).volume()), 3)})
            out.append({**q, 'firstContactJawDeg': a, 'firstContact': hit, 'headWithoutJawJaw0': head})
        print('release yaw', y, f'{time.time() - t0:.0f}s', file=sys.stderr, flush=True)
    return out


if __name__ == '__main__':
    main()
