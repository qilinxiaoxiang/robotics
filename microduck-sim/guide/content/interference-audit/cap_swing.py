#!/usr/bin/env python3
"""Cap-on as a hooked swing: the populated cap (Pi, header and plugged housing included) is lowered while tilted
rear-up by theta0 about a y-parallel axis at (px, pz), then swung closed to theta = 0 about that axis.

Positive theta lifts the rear of the cap and moves parts below the axis rearward, so the plugged housing passes
behind the camera stack and reaches its final place moving forward. Stage 1: tilted, [0, 0, 40] -> 0 (41 samples).
Stage 2: theta0 -> 0 (41 samples). Obstacles are the parts present at cap-on; a collision is excess over the
final-pose overlap > 0.5 mm^3 with local thickness > 0.1 mm. Writes cap-swing.json.
Usage: cap_swing.py px,pz,theta0 [...]
"""
from __future__ import annotations

import json
import sys

import manifold3d as m3d
import numpy as np

from ia_lib import HERE, from_manifold, load_guide, manifest, rnd
from pairs import local_thickness
from steps_audit import Solids, physical_state, resolve
from whatif import rot_y


def main():
    cands = [tuple(float(x) for x in a.split(',')) for a in sys.argv[1:]]
    g = load_guide()
    man = manifest()
    steps, mods = resolve(g)
    phys = physical_state(steps, mods)
    by = {s['id']: s for s in steps}
    S = Solids(cap=90)
    cap_all = by['cap-on']['add']
    present = [k for k in set(phys['cap-on']['installedBefore']) - set(cap_all) if k in man]
    M = m3d.Manifold.batch_boolean([S.get(k) for k in cap_all], m3d.OpType.Add)
    mb = np.array(M.bounding_box()).reshape(2, 3)
    p = HERE / 'cap-swing.json'
    prev = json.loads(p.read_text()) if p.exists() else []
    for px, pz, th0 in cands:
        def pose(th, t):
            return M.transform(rot_y(th, [px, 0.0, pz])).translate(list(t))
        poses = [(th0, [0, 0, float(z)]) for z in np.linspace(40, 0, 41)] + [(float(th), [0, 0, 0]) for th in np.linspace(th0, 0, 41)]
        hits = {}
        for k in present:
            O = S.get(k)
            ob = np.array(O.bounding_box()).reshape(2, 3)
            if np.any(ob[0] > mb[1] + 60) or np.any(ob[1] < mb[0] - 60):
                continue
            f0 = (M ^ O).volume()
            worst = (0.0, None)
            for th, t in poses:
                ex = (pose(th, t) ^ O).volume() - f0
                if ex > worst[0]:
                    worst = (ex, (th, t))
            if worst[0] > 0.5:
                v, f = from_manifold(pose(*worst[1]) ^ O)
                th_ = local_thickness(v, f, n=200)[0] if len(f) else 0
                if th_ > 0.1:
                    hits[k] = {'excessMm3': rnd(worst[0], 2), 'atThetaDeg': rnd(worst[1][0], 2), 'atOffset': worst[1][1],
                               'thicknessMm': rnd(th_, 3), 'centroid': rnd(v.mean(0), 1)}
        rec = {'pivotXZ': [px, pz], 'theta0Deg': th0, 'clean': not hits, 'collisions': hits}
        print(json.dumps({'pivot': [px, pz], 'theta0': th0, 'clean': not hits, 'hits': {k: v['excessMm3'] for k, v in hits.items()}}), flush=True)
        prev = [r for r in prev if not (r['pivotXZ'] == [px, pz] and r['theta0Deg'] == th0)] + [rec]
        p.write_text(json.dumps(prev, indent=1))


if __name__ == '__main__':
    main()
