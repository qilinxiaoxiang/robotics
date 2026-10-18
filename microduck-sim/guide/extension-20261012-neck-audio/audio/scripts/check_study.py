#!/usr/bin/env python3
"""Exact checks of the recommended audio study solids (build_study.py) against the V1.8 head.

Head = V1.8 solids with head_cap replaced by the study cap (head_cap_extension). For every study solid: static overlap
and gap against all head-fixed solids and the Pi group, head-roll sweep, jaw sweep, cap-on descent (every audio part is
cap-mounted), cable-centreline clearance, plus the pairwise contacts between the study parts themselves.
Intended contacts (listed in INTENDED) are reported but do not fail. Writes ../study-checks.json.
"""
from __future__ import annotations

import itertools
import json

import manifold3d as m3
import numpy as np
import trimesh

from check_lib import FIXED, Head, bbox, cable_clearance, man_from_tm
from scene import STUDY

S = STUDY / 'study-solids'
PARTS = ['speaker', 'speaker_leads_envelope', 'speaker_retainer', 'speaker_screws_envelope', 'amplifier',
         'amp_housings', 'amp_screws_envelope', 'pi_housing_pin04', 'pi_housing_pin12', 'pi_housing_pin14',
         'pi_housing_pin35', 'pi_housing_pin40']
# (a, b): reason. Screw envelopes are Ø2.0 shanks in Ø1.7 pilots (thread engagement) and heads on their seat.
INTENDED = {
    ('speaker_screws_envelope', 'head_cap'): 'screw thread in the collar boss pilot (Ø2.0 shank in Ø1.7 pilot)',
    ('speaker_screws_envelope', 'speaker_retainer'): 'screw shank through the Ø2.4 retainer hole; head seats on retainer',
    ('amp_screws_envelope', 'head_cap'): 'screw thread in the amp post pilot',
    ('amp_screws_envelope', 'amplifier'): 'screw shank through the Ø2.5 board hole; head seats on the board',
    ('speaker_retainer', 'head_cap'): 'retainer seated on the two collar bosses (face contact)',
    ('amplifier', 'head_cap'): 'board top seated on the two amp posts (face contact)',
    ('amp_housings', 'amplifier'): 'housings seated against the right-angle header body (face contact)',
    ('speaker_leads_envelope', 'speaker_retainer'): 'lead envelope passes the retainer notch',
}


def intended(a, b):
    return INTENDED.get((a, b)) or INTENDED.get((b, a))


def main():
    cap_ext = man_from_tm(trimesh.load(S / 'head_cap_extension-world.stl', force='mesh'))
    H = Head(cap_override=cap_ext)
    M = {k: man_from_tm(trimesh.load(S / f'{k}-world.stl', force='mesh')) for k in PARTS}
    added = man_from_tm(trimesh.load(S / 'cap_added_material-world.stl', force='mesh'))
    res = {'parts': {}, 'pairs': [], 'failures': []}
    for k, Mk in M.items():
        st = H.static(k, Mk)
        for r in st:
            r['intended'] = intended(k, r['with'])
            if r['overlapMm3'] > 1e-3 and not r['intended'] and not (k.startswith('pi_housing') and r['with'].startswith('head_pi')):
                res['failures'].append({'part': k, **r})
        rec = {'static': st[:8], 'roll': H.roll_sweep(Mk, 1.0), 'jaw': H.jaw_sweep(Mk, 1.0),
               'descentWithCap': H.descent(Mk, 0.5), 'cables': cable_clearance(Mk)}
        if rec['roll']['overlapMm3'] > 0 or rec['jaw']['overlapMm3'] > 0:
            res['failures'].append({'part': k, 'sweep': True, 'roll': rec['roll'], 'jaw': rec['jaw']})
        for o, d in rec['descentWithCap'].items():
            if d['excessMm3'] > 0.5:
                res['failures'].append({'part': k, 'descent': o, **d})
        res['parts'][k] = rec
        print(k, 'static', [(r['with'], r['overlapMm3'], r['gapMm']) for r in st[:3]], 'roll', rec['roll'], 'jaw',
              rec['jaw']['gapMm'], 'descent', rec['descentWithCap'], 'cables', rec['cables'], flush=True)
    # Pi-end housings against the Pi group: the pin they sit on is an intended engagement; neighbours must not overlap.
    for k in [p for p in PARTS if p.startswith('pi_housing')]:
        pin = 'head_pi_zero_w_header_pin_' + k[-2:]
        for r in res['parts'][k]['static']:
            if r['with'].startswith('head_pi') and r['overlapMm3'] > 1e-3 and r['with'] != pin:
                res['failures'].append({'part': k, **r, 'note': 'overlaps a Pi-group solid other than its own pin'})
    # Cap added material against everything that is not the cap (it is cap material).
    st = H.static('cap_added_material', added, skip=('head_cap',))
    rec = {'static': st[:8], 'roll': H.roll_sweep(added, 1.0), 'jaw': H.jaw_sweep(added, 1.0),
           'descentWithCap': H.descent(added, 0.5), 'cables': cable_clearance(added)}
    res['parts']['cap_added_material'] = rec
    for r in st:
        if r['overlapMm3'] > 1e-3:
            res['failures'].append({'part': 'cap_added_material', **r})
    if rec['roll']['overlapMm3'] > 0 or rec['jaw']['overlapMm3'] > 0:
        res['failures'].append({'part': 'cap_added_material', 'sweep': True})
    print('cap_added_material', [(r['with'], r['overlapMm3'], r['gapMm']) for r in st[:3]], rec['roll'], rec['descentWithCap'])
    # Pairwise between study parts.
    for a, b in itertools.combinations(PARTS, 2):
        A, B = M[a], M[b]
        Ab, Bb = bbox(A), bbox(B)
        if np.any(Ab[0] - 6 > Bb[1]) or np.any(Bb[0] - 6 > Ab[1]):
            continue
        ov = (A ^ B).volume()
        g = float(A.min_gap(B, 6))
        row = {'a': a, 'b': b, 'overlapMm3': round(ov, 4), 'gapMm': round(g, 3), 'intended': intended(a, b)}
        res['pairs'].append(row)
        if ov > 1e-3 and not row['intended']:
            res['failures'].append(row)
    # Exterior: the extension cap may differ from the V1.8 cap only inside the head cavity and at the grille holes.
    v18 = H.get('head_cap') if H.cap_override is None else man_from_tm(trimesh.load(
        STUDY.parents[1] / 'print/world/head_cap.stl', force='mesh'))
    hull = m3.Manifold.batch_hull([v18])
    pieces = sorted((hull - v18).decompose(), key=lambda m: -m.volume())
    outside_grooves = m3.Manifold.batch_boolean(pieces[1:], m3.OpType.Add) if len(pieces) > 1 else m3.Manifold()
    res['exterior'] = {'addedMaterialInExteriorGroovesMm3': round((added ^ outside_grooves).volume(), 4),
                       'addedMaterialOutsideHullMm3': round((added - hull).volume(), 4),
                       'removedMaterialMm3': round((v18 - cap_ext).volume(), 3),
                       'note': 'removed material = the grille holes (see study-build.json grille)'}
    # Blind-pilot skin: material left between each pilot tip and the outer cap surface, along the screw axis.
    b = json.loads((STUDY / 'study-build.json').read_text())
    f = b['speakerFrame']
    c0, v, n = (np.array(f[k]) for k in ('originFrontFaceCentre', 'v_short', 'n_front'))
    P = b['parameters']
    cap_tm = trimesh.load(S / 'head_cap_extension-world.stl', force='mesh')
    tips = [('speaker boss ' + ('+y' if s_ > 0 else '-y'), c0 + s_ * P['BOSS_V'] * v + (-2.5 + P['PILOT_DEPTH']) * n, n) for s_ in (-1, 1)]
    tips += [(f'amp post {i}', np.array([hx, hy, P['AMP_PCB_TOP_Z'] + 5.5]), np.array([0, 0, 1.0]))
             for i, (hx, hy) in enumerate(b['amplifier']['holesXY'])]
    skins = {}
    for name, p, ax in tips:
        loc, _, _ = cap_tm.ray.intersects_location([p], [ax])
        dd = sorted(float((q - p) @ ax) for q in loc if (q - p) @ ax > 0)
        skins[name] = {'tip': np.round(p, 2).tolist(), 'skinToOuterSurfaceMm': round(dd[-1], 2) if dd else None}
        if not dd or dd[-1] < 0.8:
            res['failures'].append({'pilot': name, 'skin': skins[name]})
    res['pilotSkin'] = skins
    print('pilot skin', skins)
    res['ok'] = not res['failures']
    (STUDY / 'study-checks.json').write_text(json.dumps(res, indent=1, default=float))
    print('FAILURES', json.dumps(res['failures'], default=float)[:3000])
    print('exterior', res['exterior'])


if __name__ == '__main__':
    main()
