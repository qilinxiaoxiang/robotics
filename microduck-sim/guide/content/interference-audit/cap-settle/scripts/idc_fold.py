"""IDC ribbon exit variants on the chosen seat: ribbon leaving the inner-row (key) side and running up the board,
versus ribbon leaving the board-edge side and folded straight back over the socket top.

Fold-over model (flexible, 1 mm criterion): the ribbon (1.0 mm) leaves the edge-side face 5.1 mm above the mating face,
bulges up to 1.5 mm beyond that face while turning, and lies flat on the socket top (one 1.0 mm layer over the whole
socket), then leaves over the inner-row side up the board (same band as the key-side exit).
Env CASES="dx:dz,..." HS="9.27,10.6".  Writes ../idc-fold.json.
"""
import json, sys, os, time, resource
sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import *

T0 = time.time()
def prog(msg):
    print(f'[{time.time()-T0:7.1f}s {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20:5.0f}MiB] {msg}', flush=True)

CASES = [tuple(float(v) for v in c.split(':')) for c in os.environ.get('CASES', '3.3:2.0,4.6:0').split(',')]
HS = [float(h) for h in os.environ.get('HS', '9.27,10.6').split(',')]
EVEN_C, ODD_C = 0.5 * sum(T_LOW), 0.5 * sum(T_HIGH)
S, prov = solids(FIXED)
FX = [k for k in FIXED if k in S]
FB = {k: bbox(S[k]) for k in FX}


def per_part(pieces, search=8.0):
    Hs = [sweep(Pc) for Pc in pieces]; out = {}
    for k in FX:
        best = search
        for H in Hs:
            hb = bbox(H); dd = np.maximum(0, np.maximum(hb[0] - FB[k][1], FB[k][0] - hb[1]))
            if np.linalg.norm(dd) < best:
                best = min(best, gap(H, S[k], best))
        if best < search:
            out[k] = round(best, 3)
    return dict(sorted(out.items(), key=lambda kv: kv[1]))


out = {'cases': {}}
for dx, dz in CASES:
    d = [-dx, 0, dz]; rec = {}
    for H in HS:
        top = S_BASE_TOP + H
        bulge = local_hull((S_BASE_TOP + 5.1, top + 1.0), (-26.0, 26.0), (EVEN_C - 1.85 - 1.5, EVEN_C - 1.85), d)
        layer = local_hull((top, top + 1.0), (-26.0, 26.0), (EVEN_C - 1.85 - 1.5, ODD_C + 3.35), d)
        rise = local_hull((top - 2.0, top + 1.0), (-26.0, 26.0), (ODD_C + 3.35, ODD_C + 1.85 + 14.0), d)
        rec[str(H)] = {'foldBulgeBelowEdgeFace': per_part([bulge]), 'layerOverSocketTop': per_part([layer]),
                       'riseUpTheBoard': per_part([rise])}
        prog(f'dx{dx} dz{dz} H{H}: ' + json.dumps({k: next(iter(v.items()), None) for k, v in rec[str(H)].items()}))
    out['cases'][f'dx{dx}-dz{dz}'] = rec
json.dump(rnd(out, 3), open(OUT / 'idc-fold.json', 'w'), indent=1)
prog('done')
