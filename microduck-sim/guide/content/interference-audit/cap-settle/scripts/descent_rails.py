"""Cap-on descent clearance of the added rail material only (pieces of C - C_V1.6 with volume >= 0.001 mm3), for the
released V1.7 cap and the candidate, one cap at a time. The boolean difference also leaves zero-volume surface slivers
on the unchanged shell (re-exported vertices differ in the last digits); those are counted and excluded here.
Sampled every 0.25 mm over h = 0..40; gap is 1-Lipschitz in a translation, so the true minimum is at most 0.125 mm below
the sampled one.  Usage: descent_rails.py <candidate-world.stl>.  Writes ../descent-rails.json.
"""
import json, sys, os, gc
sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import *

CAND = Path(sys.argv[1])
SEARCH = 6.0
S, prov = solids(FIXED)
FX = [k for k in FIXED if k in S]
FB = {k: bbox(S[k]) for k in FX}
C16 = load_cap(CAP_V16, CAP_V16_SHA)
out = {'method': __doc__.strip(), 'stepMm': 0.25, 'searchMm': SEARCH, 'caps': {}}


def near(M, s):
    hb = bbox(M)
    return [k for k in FX if np.linalg.norm(np.maximum(0, np.maximum(hb[0] - FB[k][1], FB[k][0] - hb[1]))) < s]


for lab, path, h0 in [('V1.7', CAP_V17, CAP_V17_SHA), ('candidate', CAND, None)]:
    C = load_cap(path, h0) if h0 else to_mf(trimesh.load(path, force='mesh'))
    added = C - C16
    del C; gc.collect()
    pieces = added.decompose()
    rails = [p for p in pieces if p.volume() >= 1e-3]
    slivers = [p for p in pieces if p.volume() < 1e-3]
    rec = {'railPieces': len(rails), 'railVolumeMm3': round(sum(p.volume() for p in rails), 3),
           'sliverPieces': len(slivers), 'sliverVolumeMm3': round(sum(p.volume() for p in slivers), 6), 'rails': []}
    for p in rails:
        base = {k: overlap(p, S[k]) for k in FX}
        per = {}; worst = (0.0, None, None)
        for h in np.arange(0.0, 40.0 + 1e-9, 0.25):
            Mh = tr(p, [0, 0, float(h)])
            for k in near(Mh, SEARCH):
                ov = overlap(Mh, S[k]) - base.get(k, 0.0)
                if ov > worst[0]:
                    worst = (ov, float(h), k)
                g = gap(Mh, S[k], SEARCH)
                if g < per.get(k, (SEARCH, None))[0]:
                    per[k] = (g, float(h))
        r = {'volumeMm3': round(p.volume(), 3), 'bounds': bbox(p).round(3).tolist(),
             'minGapPerPart': {k: {'gapMm': round(v[0], 3), 'atHeightMm': v[1]} for k, v in sorted(per.items(), key=lambda kv: kv[1][0])},
             'maxExcessOverlapMm3': round(worst[0], 5), 'excessAt': worst[1:]}
        rec['rails'].append(r)
        print(lab, json.dumps(r), flush=True)
    out['caps'][lab] = rec
    del added, pieces, rails, slivers; gc.collect()
json.dump(out, open(OUT / 'descent-rails.json', 'w'), indent=1)
