#!/usr/bin/env python3
"""Raised screw heads at the four clip screws: does the head, lifted by the clip tab, still clear the parts around the
seat? Exact manifold3d gaps of the head solid (fasteners.json diameter, and the ISO 7045 pan-head size as a larger
check: M2 dk 4.0 k 1.6, M2.5 dk 5.0 k 1.75) lifted by TAB along the outward normal, plus the tab disc itself, against
every cached part within 15 mm (static parts of the same body; other bodies at q = 0).
Usage: seat_check.py [tab_mm]  -> SCRATCH/seat-check.json
"""
import json
import sys

import numpy as np

import ext_lib as E

TAB = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
SITES = ['S12-horn-025', 'S11-horn-040', 'H-jaw_support-03', 'E-pi-04']
ISO = {2.0: (4.0, 1.6), 2.5: (5.0, 1.75)}


def main():
    F = E.fasteners()
    man = E.ia_lib.manifest()
    out = {}
    for sid in SITES:
        r = F[sid]
        c, ax = np.array(r['center']), np.array(r['axis'], float)
        ax /= np.linalg.norm(ax)
        rec = {}
        keys = [k for k, m in man.items()
                if np.linalg.norm(np.maximum(0, np.maximum(np.array(m['bounds'])[0] - c, c - np.array(m['bounds'])[1]))) < 15]
        solids = {k: (E.stl_man(E.PARTS['head_cap_v19']) if k == 'head_cap' else E.load_man(k)) for k in keys}
        for label, (hd, hh) in (('fasteners', (r['headDiameterMm'], r['headHeightMm'])), ('iso7045', ISO[r['diameterMm']])):
            head = E.cyl(c - (TAB + hh) * ax, ax, hh, hd / 2, 64)
            res = {}
            for k, M in solids.items():
                ov = (head ^ M).volume()
                g = float(head.min_gap(M, 10))
                res[k] = {'overlapMm3': round(ov, 4), 'gapMm': round(g, 3)}
            rec[f'head_{label}_d{hd}_h{hh}'] = dict(sorted(res.items(), key=lambda kv: kv[1]['gapMm']))
        # free radius of a tab disc on the seat plane: largest r (0.1 steps) with no overlap with anything but the screw
        for rr in np.arange(2.0, 6.01, 0.2):
            disc = E.cyl(c - TAB * ax, ax, TAB - 0.02, rr, 96)
            hit = {k: round((disc ^ M).volume(), 4) for k, M in solids.items() if (disc ^ M).volume() > 1e-4}
            if hit:
                rec['tabDiscFirstHit'] = {'radiusMm': round(float(rr), 2), 'hits': hit}
                break
        out[sid] = rec
        print(sid, json.dumps(rec)[:1500], flush=True)
    E.jdump(out, E.SCRATCH / f'seat-check-tab{TAB}.json')


if __name__ == '__main__':
    main()
