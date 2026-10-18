"""Which fixed head parts the unchanged cap shell overlaps in the seated pose (the 63.03 mm3 baseline shared by the
printed V1.6 and the candidate). Usage: shell_overlap.py <candidate-world.stl>.  Writes ../shell-overlap.json."""
import json, sys, os, gc
sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import *
S, prov = solids(FIXED)
out = {}
for lab, path, h0 in [('V1.6', CAP_V16, CAP_V16_SHA), ('candidate', Path(sys.argv[1]), None)]:
    C = load_cap(path, h0) if h0 else to_mf(trimesh.load(path, force='mesh'))
    rec = {}
    for k, M in S.items():
        I = C ^ M
        if not I.is_empty() and I.volume() > 1e-3:
            rec[k] = {'overlapMm3': round(I.volume(), 3), 'bounds': bbox(I).round(2).tolist()}
    out[lab] = rec; print(lab, json.dumps(rec), flush=True)
    del C; gc.collect()
json.dump(out, open(OUT / 'shell-overlap.json', 'w'), indent=1)
