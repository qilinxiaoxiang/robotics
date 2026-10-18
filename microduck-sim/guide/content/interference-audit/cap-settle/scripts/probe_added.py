"""Where is the cap's added rail material closest to the fixed head parts? Candidate and released V1.7, one cap at a
time. The location is found by cutting each added piece into 2 mm cells and taking the cell with the smallest exact gap.
Writes ../probe-added.json.  Usage: probe_added.py <candidate-world.stl>
"""
import json, sys, os, gc
sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import *

CAND = Path(sys.argv[1])
PARTS = ['face_panel', 'jaw_support', 'motor15', 'head_bottom']
S, prov = solids(PARTS)
C16 = load_cap(CAP_V16, CAP_V16_SHA)
out = {}


def locate(p, M, g0, cell=2.0):
    b = bbox(p); best = (99.0, None)
    xs = np.arange(b[0, 0], b[1, 0] + 1e-9, cell); ys = np.arange(b[0, 1], b[1, 1] + 1e-9, cell); zs = np.arange(b[0, 2], b[1, 2] + 1e-9, cell)
    for x in xs:
        for y in ys:
            for z in zs:
                c = p ^ box([x, y, z], [x + cell, y + cell, z + cell])
                if c.is_empty():
                    continue
                g = gap(c, M, g0 + 0.5)
                if g < best[0]:
                    best = (g, bbox(c).round(2).tolist())
    return best


for lab, path, h in [('V1.7', CAP_V17, CAP_V17_SHA), ('candidate', CAND, None)]:
    C = load_cap(path, h) if h else to_mf(trimesh.load(path, force='mesh'))
    added = C - C16
    del C; gc.collect()
    rec = []
    for p in added.decompose():
        r = {'volumeMm3': round(p.volume(), 6), 'bounds': bbox(p).round(3).tolist()}
        if p.volume() < 1e-3:
            g = gap(p, S['face_panel'], 6.0)
            r['tinyPieceGapToFacePanel'] = round(g, 3)
            rec.append(r)
            continue
        for k in PARTS:
            g = gap(p, S[k], 6.0)
            if g < 6.0:
                lg, cellb = locate(p, S[k], g)
                r[k] = {'gap': round(g, 3), 'nearestCellBounds': cellb}
        rec.append(r)
    out[lab] = rec
    print(lab, json.dumps(rec), flush=True)
    del added; gc.collect()
json.dump(out, open(OUT / 'probe-added.json', 'w'), indent=1)
