"""Static spacing between the Pi (carried by the cap rails) and the cap itself, for the printed V1.6, the released V1.7
and the candidate, so inherited spacings can be told apart from new ones. Each Pi part is moved with its seat
([0,0,0], [-4.6,0,0], [-DX,0,DZ]) and measured against the whole cap, the rail zone (|y| >= 25.3) and the rest.
These parts never move relative to the cap, so the 2 mm descent criterion does not apply; the numbers are stack-ups.
Usage: DX=3.3 DZ=2.0 static_pi.py <candidate-world.stl>.  Writes ../static-pi.json.
"""
import json, sys, os, gc
sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import *

DX = float(os.environ.get('DX', 3.3)); DZ = float(os.environ.get('DZ', 2.0))
CAND = Path(sys.argv[1])
S, prov = solids(None)
pi_keys = sorted(k for k in S if k == 'pi' or (k.startswith('head_pi') and 'receiving' not in k and 'header_pin' not in k))
out = {'method': __doc__.strip(), 'caps': {}}
BIG = 200.0
for lab, path, h0, sh in [('V1.6', CAP_V16, CAP_V16_SHA, [0, 0, 0]), ('V1.7', CAP_V17, CAP_V17_SHA, [-4.6, 0, 0]),
                          ('candidate', CAND, None, [-DX, 0, DZ])]:
    C = load_cap(path, h0) if h0 else to_mf(trimesh.load(path, force='mesh'))
    zone = union([box([-BIG, 25.3, -BIG], [BIG, BIG, BIG]), box([-BIG, -BIG, -BIG], [BIG, -25.3, BIG])])
    rails = C ^ zone; rest = C - zone
    rec = {}
    for k in pi_keys:
        M = tr(S[k], sh)
        g = gap(M, C, 6.0)
        if g >= 6.0:
            continue
        rec[k] = {'cap': round(g, 3), 'railZone': round(gap(M, rails, 6.0), 3), 'rest': round(gap(M, rest, 6.0), 3),
                  'overlapMm3': round(overlap(M, C), 4)}
    out['caps'][lab] = {'seatShift': sh, 'parts': dict(sorted(rec.items(), key=lambda kv: kv[1]['cap']))}
    print(lab, json.dumps(out['caps'][lab]), flush=True)
    del C, rails, rest; gc.collect()
json.dump(out, open(OUT / 'static-pi.json', 'w'), indent=1)
