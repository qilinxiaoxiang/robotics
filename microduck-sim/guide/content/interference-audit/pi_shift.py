#!/usr/bin/env python3
"""Candidate head_cap change for the cap-on collision: seat the Pi further back on the cap.

When the populated cap is lowered, the plugged 2x20 housing (GPIO receiving envelopes, front at x 78.97) passes
through the camera stack (clamp screws from x 74.88). This script moves the Pi, its header and the housing by dx
along x, moves the cap's two Pi rails and two upper posts by the same dx (cap minus the features plus the moved
features), and checks (1) final-pose overlap of the moved Pi group and the moved features with every other part,
(2) that the moved features stay inside the cap's convex hull, and (3) the cap descent [0, 0, 40] -> 0 of the whole
modified cap group through the parts present at cap-on (41 samples, excess > 0.5 mm^3 and thickness > 0.1 mm).
Writes pi-shift.json. Usage: pi_shift.py [dx[:clipx] ...] (default -4.6 -5.0); clipx trims the moved rails and posts
to x >= clipx (keeps the rail rear face clear of jaw_support and motor15). Also reports the rear limit those two
parts set inside the +y rail window.
"""
from __future__ import annotations

import json
import sys

import manifold3d as m3d
import numpy as np

from ia_lib import HERE, from_manifold, load_guide, manifest, rnd
from pairs import local_thickness
from steps_audit import Solids, physical_state, resolve


def box(lo, hi):
    lo, hi = np.array(lo, float), np.array(hi, float)
    return m3d.Manifold.cube(list(hi - lo)).translate(list(lo))


RAILS = [([55.0, 25.5, 114.0], [62.5, 32.5, 144.0]), ([55.0, -32.5, 114.0], [62.5, -25.5, 144.0])]
POSTS = [([57.5, 7.5, 141.5], [62.5, 13.0, 145.0]), ([57.5, -13.0, 141.5], [62.5, -7.5, 145.0])]


def main():
    specs = [(float(a.split(':')[0]), float(a.split(':')[1]) if ':' in a else None) for a in sys.argv[1:]] or [(-4.6, None), (-5.0, None)]
    g = load_guide()
    man = manifest()
    steps, mods = resolve(g)
    phys = physical_state(steps, mods)
    by = {s['id']: s for s in steps}
    S = Solids(cap=90)
    cap_all = by['cap-on']['add']
    gpio = [k for k in cap_all if k.startswith('head_pi_gpio_pin_')]
    pig = set(by['pi']['add'] + gpio)
    cap = S.get('head_cap')
    feat = m3d.Manifold.batch_boolean([cap ^ box(lo, hi) for lo, hi in RAILS + POSTS], m3d.OpType.Add)
    fb = np.array(feat.bounding_box()).reshape(2, 3)
    present = [k for k in set(phys['cap-on']['installedBefore']) - set(cap_all) if k in man]
    hull = cap.hull()
    win = box([40.0, 25.5, 114.0], [62.5, 32.5, 150.0])
    limits = {}
    for k in ('jaw_support', 'motor15', 'jaw_frame'):
        w = S.get(k) ^ win
        if w.volume() > 0:
            limits[k] = rnd(np.array(w.bounding_box()).reshape(2, 3), 2)
    out = {'rearPartsInPlusYRailWindow': limits, 'featureBounds': rnd(fb, 2), 'featureVolumeMm3': rnd(feat.volume(), 1), 'railBoxes': RAILS, 'postBoxes': POSTS,
           'movers': len(cap_all), 'presentAtCapOn': len(present), 'candidates': []}
    for dx, clip in specs:
        d = [dx, 0.0, 0.0]
        moved = feat.translate(d)
        if clip is not None:
            moved = moved ^ box([clip, -40.0, 100.0], [70.0, 40.0, 160.0])
        cap2 = (cap - feat) + moved
        sol = {k: (S.get(k).translate(d) if k in pig else (cap2 if k == 'head_cap' else S.get(k))) for k in cap_all}
        # (1) final pose: moved Pi group and moved features against every other part
        fin = {}
        for k in man:
            if k in pig:
                continue
            O = sol.get(k, S.get(k)) if k != 'head_cap' else cap2
            ob = np.array(man[k]['bounds'])
            for name, A in (('piGroup', None), ('movedRailsPosts', moved)):
                if name == 'piGroup':
                    for p in pig:
                        pb = np.array(man[p]['bounds']) + np.array(d)
                        if np.any(pb[0] > ob[1] + 0.2) or np.any(pb[1] < ob[0] - 0.2):
                            continue
                        v = (sol[p] ^ O).volume() - (S.get(p) ^ S.get(k)).volume()
                        if v > 0.05:
                            fin.setdefault(k, {}).setdefault('piGroupNewMm3', 0.0)
                            fin[k]['piGroupNewMm3'] = rnd(fin[k]['piGroupNewMm3'] + v, 2)
                elif k != 'head_cap':
                    mb = np.array(moved.bounding_box()).reshape(2, 3)
                    if np.any(mb[0] > ob[1] + 0.2) or np.any(mb[1] < ob[0] - 0.2):
                        continue
                    O2 = O.translate(d) if k in pig else O
                    v = (moved ^ O2).volume()
                    if v > 0.05:
                        fin.setdefault(k, {})['movedFeatureMm3'] = rnd(v, 2)
        # Pi group against the moved rails (should equal the original Pi/rail contact)
        piU = m3d.Manifold.batch_boolean([sol[p] for p in pig], m3d.OpType.Add)
        pi_vs_cap2 = (piU ^ cap2).volume()
        pi0_vs_cap = (m3d.Manifold.batch_boolean([S.get(p) for p in pig], m3d.OpType.Add) ^ cap).volume()
        # (3) descent of the modified cap group
        M = m3d.Manifold.batch_boolean(list(sol.values()), m3d.OpType.Add)
        mb = np.array(M.bounding_box()).reshape(2, 3)
        hits = {}
        for k in present:
            O = S.get(k)
            ob = np.array(O.bounding_box()).reshape(2, 3)
            if np.any(ob[0] > mb[1] + np.array([0.2, 0.2, 40.2])) or np.any(ob[1] < mb[0] - 0.2):
                continue
            f0 = (M ^ O).volume()
            worst = (0.0, None)
            for z in np.linspace(40, 0, 41):
                ex = (M.translate([0, 0, float(z)]) ^ O).volume() - f0
                if ex > worst[0]:
                    worst = (ex, float(z))
            if worst[0] > 0.5:
                v, f = from_manifold(M.translate([0, 0, worst[1]]) ^ O)
                th = local_thickness(v, f, n=200)[0] if len(f) else 0
                if th > 0.1:
                    hits[k] = {'excessMm3': rnd(worst[0], 2), 'atZ': worst[1], 'thicknessMm': rnd(th, 3)}
        # clearance between the housing front and the camera stack after the shift (x gap in the shared y-z window)
        rec = {'dx': dx, 'clipX': clip, 'movedFeatureVolumeMm3': rnd(moved.volume(), 1), 'finalPoseNewOverlap': fin, 'piGroupVsModifiedCapMm3': rnd(pi_vs_cap2, 2),
               'piGroupVsOriginalCapMm3': rnd(pi0_vs_cap, 2), 'movedFeatureOutsideCapHullMm3': rnd((moved - hull).volume(), 2),
               'descentCollisions': hits, 'descentClean': not hits, 'capVolumeChangeMm3': rnd(cap2.volume() - cap.volume(), 2)}
        out['candidates'].append(rec)
        print(json.dumps(rec), flush=True)
    print(json.dumps({'rearPartsInPlusYRailWindow': limits}))
    (HERE / 'pi-shift.json').write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
