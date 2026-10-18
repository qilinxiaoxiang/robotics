#!/usr/bin/env python3
"""Which plug housings and wire groups pass the narrowest sections of the final in-head route A3.

Sections: the exact cross-sections route_exact.py cut at the lowest points of the clearance profile of the two A3
corridors ('A3-slot-to-clip', 'A3-clip-over-top-plus-y'): the plane perpendicular to the route cut through every solid of
the integrated head at every jaw (0..40 deg) and roll (-25..+25 deg) pose at once (so the free region is the space left
in the worst pose), rasterised at 0.05 mm. Same test as neck-route/connector_fit.py: a housing is threaded end first, so
its cross-section rectangle (plus 0.1 mm all round) must fit inside the free component that holds the route at some
position and angle (5 deg steps, FFT correlation); a round group of diameter d fits when the distance raster reaches d/2.
Housing outlines: Dupont from the 2.54 mm pitch (nominal); JST outlines are nominal catalogue sizes (inference, check
against the datasheet of the part bought). Writes ../connector-fit-A3.json.
"""
import json

import numpy as np
from scipy.signal import fftconvolve

import int_lib as L

RES, CLEAR = 0.05, 0.1
HOUSINGS = {
    'dupont-1pin (2.54 x 2.54)': (2.54, 2.54),
    'dupont-1x4 (10.16 x 2.54)': (10.16, 2.54),
    'dupont-2x4 (10.16 x 5.08)': (10.16, 5.08),
    'jst-ph-4 housing (9.9 x 4.5, nominal, inference)': (9.9, 4.5),
    'jst-ph-8 housing (17.9 x 4.5, nominal, inference)': (17.9, 4.5),
}
GROUPS = {'round bundle 6.7 mm (V1.8)': 6.7, 'eight wires as a flat group two deep (3.4 mm)': 3.4,
          'one 22 AWG silicone wire 1.7 mm': 1.7}
ANGLES = np.arange(0.0, 180.0, 5.0)


def rect_kernel(w, h, ang):
    a = np.radians(ang)
    hw, hh = w / 2 + CLEAR, h / 2 + CLEAR
    R = int(np.ceil(np.hypot(hw, hh) / RES)) + 1
    u = np.arange(-R, R + 1) * RES
    X, Y = np.meshgrid(u, u, indexing='ij')
    xr = X * np.cos(a) + Y * np.sin(a)
    yr = -X * np.sin(a) + Y * np.cos(a)
    return ((np.abs(xr) <= hw) & (np.abs(yr) <= hh)).astype(np.float32)


def fits(comp, w, h):
    free = comp.astype(np.float32)
    for ang in ANGLES:
        k = rect_kernel(w, h, ang)
        if (fftconvolve(free, k[::-1, ::-1], mode='same') >= k.sum() - 0.5).any():
            return float(ang)
    return None


def main():
    out = {'_method': __doc__.strip(), 'sections': []}
    for scen in ('A3-slot-to-clip', 'A3-clip-over-top-plus-y'):
        meta = json.loads((L.STUDY / f'route-exact-{scen}.json').read_text())['sections']
        for i, m in enumerate(meta, 1):
            p = L.SCRATCH / f'route-sec-{scen}-{i}.npz'
            if not p.exists():
                continue
            z = np.load(p)
            comp, D = z['comp'].astype(bool), z['D']
            Dm = np.where(comp, D, 0.0)
            rec = {'corridor': scen, 'atMm': m['atMm'], 'point': m['point'], 'boundedBy': m['boundedBy'],
                   'inscribedRadiusMm': round(float(Dm.max()), 3),
                   'housingsThatFit': {h: fits(comp, *wh) is not None for h, wh in HOUSINGS.items()},
                   'groupsThatFit': {g: bool(Dm.max() >= d / 2) for g, d in GROUPS.items()}}
            out['sections'].append(rec)
            print(scen, m['atMm'], rec['inscribedRadiusMm'], [h.split(' ')[0] for h, ok in rec['housingsThatFit'].items() if ok], flush=True)
    out['allSectionsPass'] = {h: all(r['housingsThatFit'][h] for r in out['sections']) for h in HOUSINGS}
    L.jdump(out, L.STUDY / 'connector-fit-A3.json')
    print(out['allSectionsPass'])


if __name__ == '__main__':
    main()
