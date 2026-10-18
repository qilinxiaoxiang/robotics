#!/usr/bin/env python3
"""Why the integrated cap's added material overlaps head_bottom (pairwise.py scene): the V1.8 cap already overlaps
head_bottom in two 0.2 mm seat bands along its rim (z 111.1..111.3 and 112.6..112.8); closing the V1.8 notch with the
V1.5 rim continues those bands across the notch. This script measures the V1.8 overlap, the integrated overlap, and the
pieces of the difference. Writes ../seat-bands.json.
"""
import numpy as np

import int_lib as L
from check_lib import bbox
from pm_lib import load_stl_man
from scene import load_man


def main():
    hb = load_man('head_bottom')
    v18 = load_man('head_cap') ^ hb
    integ = load_stl_man(L.INTEGRATED_CAP) ^ hb
    extra = integ - v18
    out = {'_method': __doc__.strip(), 'V18CapOverlapHeadBottomMm3': v18.volume(), 'V18OverlapZRange': bbox(v18)[:, 2],
           'integratedCapOverlapHeadBottomMm3': integ.volume(), 'extraMm3': extra.volume(), 'extraBbox': bbox(extra),
           'extraPieces': [{'mm3': c.volume(), 'bbox': bbox(c)} for c in extra.decompose() if c.volume() > 1e-3]}
    L.jdump(L.rnd(out, 3), L.STUDY / 'seat-bands.json')
    print(L.rnd({k: v for k, v in out.items() if k != '_method'}, 2))


if __name__ == '__main__':
    main()
