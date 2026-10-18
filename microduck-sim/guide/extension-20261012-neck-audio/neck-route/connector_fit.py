#!/usr/bin/env python3
"""Which plug housings and wire groups can be threaded through the narrow passages, at rest and at a threading pose.

Uses the exact sections of sections.py (same planes, same 0.05 mm raster, existing cables as obstacles). A housing is
threaded end first, so its cross-section (a rectangle perpendicular to the wire) must fit inside the free passage at
some position and angle: the free component is tested against the rectangle (plus 0.1 mm clearance all round) rotated in
5 deg steps (FFT correlation: every rectangle pixel must be free). A round group of diameter d fits when the distance
raster reaches d/2. Each passage is checked at q = 0 and at every head roll in sections.ROLLS; the threading pose is the
roll that gives the most room (servos are back-drivable by hand with the power off), the running condition is the worst
roll inside the policy range.
Housing outlines: Dupont from the 2.54 mm pitch (nominal); JST outlines are nominal catalogue sizes quoted from memory
(inference) and must be checked against the datasheet of the part actually bought.
Writes connector-fit.json.
"""
import sys
import time

import numpy as np
from scipy.signal import fftconvolve

sys.path.insert(0, __import__('os').path.dirname(__file__))
import sections as S  # noqa: E402  (loads the solids once)
from nr_lib import HERE, jdump, rnd  # noqa: E402

CLEAR = 0.1
HOUSINGS = {
    'dupont-1pin (2.54 x 2.54)': (2.54, 2.54),
    'dupont-1x2 (5.08 x 2.54)': (5.08, 2.54),
    'dupont-1x4 (10.16 x 2.54)': (10.16, 2.54),
    'dupont-1x5 (12.7 x 2.54)': (12.7, 2.54),
    'dupont-2x4 (10.16 x 5.08)': (10.16, 5.08),
    'dupont-2x5 (12.7 x 5.08)': (12.7, 5.08),
    'jst-sh-4 housing (6.0 x 2.95, nominal, inference)': (6.0, 2.95),
    'jst-ph-4 housing (9.9 x 4.5, nominal, inference)': (9.9, 4.5),
}
GROUPS = {'round bundle 6.7 mm (V1.8)': 6.7, 'four 22-26 AWG wires twisted, about 4.1 mm': 4.1,
          'one 22 AWG silicone wire 1.7 mm': 1.7}
PASSAGES = ['slot-minus-y-z129', 'chan-minus-y-z106', 'chan-minus-y-z108', 'chan-minus-y-z110', 'gap-plus-y-z127',
            'gap-plus-y-z115', 'pi-top-minus-y-x61', 'pi-top-plus-y-x61']
ANGLES = np.arange(0.0, 180.0, 5.0)


def rect_kernel(w, h, ang):
    a = np.radians(ang)
    hw, hh = w / 2 + CLEAR, h / 2 + CLEAR
    R = int(np.ceil(np.hypot(hw, hh) / S.RES)) + 1
    u = np.arange(-R, R + 1) * S.RES
    X, Y = np.meshgrid(u, u, indexing='ij')
    xr = X * np.cos(a) + Y * np.sin(a)
    yr = -X * np.sin(a) + Y * np.cos(a)
    return ((np.abs(xr) <= hw) & (np.abs(yr) <= hh)).astype(np.float32)


def fits(comp, w, h):
    free = comp.astype(np.float32)
    best = None
    for ang in ANGLES:
        k = rect_kernel(w, h, ang)
        c = fftconvolve(free, k[::-1, ::-1], mode='same')
        if (c >= k.sum() - 0.5).any():
            return float(ang)
    return best


def evaluate(name, q):
    r, D, info = S.section(name, q, True)
    if info is None:
        return {'radiusMm': 0.0, 'housings': {h: False for h in HOUSINGS}, 'groups': {g: False for g in GROUPS}}
    comp = info[2]
    res = {'radiusMm': r['radiusMm'], 'housings': {}, 'groups': {}}
    for hname, (w, h) in HOUSINGS.items():
        a = fits(comp, w, h)
        res['housings'][hname] = a is not None
    Dm = np.where(comp, D, 0)
    for gname, d in GROUPS.items():
        res['groups'][gname] = bool(Dm.max() >= d / 2)
    return res


def main():
    t0 = time.time()
    out = {'_method': __doc__.strip(), 'clearanceMm': CLEAR, 'passages': {}}
    for name in PASSAGES:
        rows = []
        for roll in S.ROLLS:
            q = {'head_roll': np.radians(roll)} if roll else {}
            e = evaluate(name, q)
            e['rollDeg'] = roll
            e['inPolicyRange'] = bool(-21.4 <= roll <= 9.9)
            rows.append(e)
        pol = [r for r in rows if r['inPolicyRange']]
        q0 = next(r for r in rows if r['rollDeg'] == 0.0)
        best = max(rows, key=lambda r: r['radiusMm'])
        worst = min(pol, key=lambda r: r['radiusMm'])
        out['passages'][name] = {
            'label': S.SECTIONS[name][3],
            'atQ0': q0,
            'threadingPose': {'rollDeg': best['rollDeg'], **{k: best[k] for k in ('radiusMm', 'housings', 'groups')}},
            'worstPolicyRoll': {'rollDeg': worst['rollDeg'], **{k: worst[k] for k in ('radiusMm', 'housings', 'groups')}},
            'housingFitsAtSomeRoll': {h: any(r['housings'][h] for r in rows) for h in HOUSINGS},
            'groupFitsAtEveryPolicyRoll': {g: all(r['groups'][g] for r in pol) for g in GROUPS},
            'rows': [{'rollDeg': r['rollDeg'], 'radiusMm': r['radiusMm'],
                      'housingsThatFit': [h for h in HOUSINGS if r['housings'][h]]} for r in rows],
        }
        print(name, 'q0 r', q0['radiusMm'], 'fits', [h.split(' ')[0] for h in HOUSINGS if q0['housings'][h]],
              '| best roll', best['rollDeg'], best['radiusMm'], f'{time.time() - t0:.0f}s', flush=True)
        jdump(out, HERE / 'connector-fit.json')


if __name__ == '__main__':
    main()
