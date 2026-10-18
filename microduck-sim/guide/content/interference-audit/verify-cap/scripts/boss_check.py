"""Do the two former OpenRB front bosses block the Pi group once it moves 4.6 mm back (final pose and cap descent)?"""
import json, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from vc import *
S, prov = solids()
pi_keys = sorted(k for k in S if k == 'pi' or (k.startswith('head_pi') and 'receiving' not in k))
C16 = S['head_cap']
out = {}
for name, lo, hi in [('boss_-y', [56.8, -13.1, 141.0], [63.1, -7.4, 160.0]), ('boss_+y', [56.8, 7.4, 141.0], [63.1, 13.1, 160.0])]:
    Bc = C16 ^ box(lo, hi)
    r = {}
    for dx in (0.0, 4.6):
        hits = {}
        for k in pi_keys:
            v = overlap(tr(S[k], [-dx, 0, 0]), Bc)
            if v > 1e-3: hits[k] = round(v, 3)
        r[f'piGroupOverlapAtDx{dx}'] = hits
        # gap from boss to the PCB along x at the boss y band
        pcb = tr(S['pi'], [-dx, 0, 0]) ^ box([40, lo[1], 138], [80, hi[1], 160])
        r[f'pcbMinXInBand_dx{dx}'] = round(float(bbox(pcb)[0, 0]), 3) if not pcb.is_empty() else None
    r['bossMaxX'] = round(float(bbox(Bc)[1, 0]), 3)
    out[name] = r
print(json.dumps(out, indent=1)); json.dump(out, open(HERE / 'boss-check.json', 'w'), indent=1)
