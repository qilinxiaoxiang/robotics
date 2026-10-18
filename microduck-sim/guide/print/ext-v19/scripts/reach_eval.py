#!/usr/bin/env python3
"""Smallest jaw angle (over all head yaw/roll nodes of the bracket group) at which the jaw comes within the contact
gap of a solid fixed on the neck_pitch body, from the reach field of jaw_reach_v19.py (saved as
$EXT19_SCRATCH/jaw-reach-minA.npy). The field is eroded with a ball of radius DELTA (jaw_reach_v19.py), so the value is
a lower bound of the true first-contact angle (conservative by up to about 1.5 mm of jaw travel).
Usage: reach_eval.py name=path.stl ... | name=tube:x,y,z;x,y,z;...:r
Prints, per solid, the smallest reach angle and where it occurs.
"""
from __future__ import annotations

import math
import sys

import numpy as np
from scipy.ndimage import minimum_filter

import ext_lib as E
import jaw_reach_v19 as JR

sys.path.insert(0, str(E.EXT / 'jaw-neck-check' / 'scripts'))
import pose_cap_sweep as PCS  # noqa: E402


def tube(pts, r):
    import manifold3d as m3
    P = [np.array(p, float) for p in pts]
    caps = [m3.Manifold.batch_hull([m3.Manifold.sphere(r, 32).translate(a), m3.Manifold.sphere(r, 32).translate(b)])
            for a, b in zip(P[:-1], P[1:])]
    return m3.Manifold.batch_boolean(caps, m3.OpType.Add)


def main():
    minA = np.load(E.SCRATCH / 'jaw-reach-minA.npy')
    r_jaw = 61.3
    delta = 0.3 + JR.E_JAW + r_jaw * math.radians(JR.STEP / 2) + JR.VOX * math.sqrt(3) / 2
    k = int(math.ceil(delta / JR.VOX))
    g = np.arange(-k, k + 1)
    ball = (g[:, None, None] ** 2 + g[None, :, None] ** 2 + g[None, None, :] ** 2) * JR.VOX ** 2 <= delta ** 2
    field = minimum_filter(minA, footprint=ball, mode='constant', cval=99.0)
    for arg in sys.argv[1:]:
        name, spec = arg.split('=', 1)
        if spec.startswith('tube:'):
            _, pts, r = spec.split(':')
            M = tube([[float(c) for c in p.split(',')] for p in pts.split(';')], float(r))
        else:
            M = E.stl_man(spec)
        t = E.tm(M)
        P = PCS.surface_points(np.asarray(t.vertices), np.asarray(t.faces), 0.25)
        ins = np.all((P >= JR.LO) & (P < JR.HI_BOX), axis=1)
        idx = np.floor((P[ins] - JR.LO) / JR.VOX).astype(int)
        a = field[idx[:, 0], idx[:, 1], idx[:, 2]]
        i = int(np.argmin(a))
        order = np.argsort(a)[:2000]
        print(name, 'min reach angle', round(float(a[i]), 2), 'at', np.round(P[ins][i], 2).tolist(),
              'points outside field', int((~ins).sum()), '| 10th pct', round(float(np.percentile(a, 10)), 2),
              '| z range of points reached below 27:',
              (np.round(P[ins][a < 27][:, 2].min(), 1), np.round(P[ins][a < 27][:, 2].max(), 1)) if (a < 27).any() else None,
              flush=True)


if __name__ == '__main__':
    main()
