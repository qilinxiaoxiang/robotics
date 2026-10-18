"""Final pose: moved Pi group and GPIO housing envelopes against every head part, the speaker parts, the amplifier and the candidate cap."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from vc import *
S, prov = solids()
DX = 4.6
movers = sorted(k for k in S if k == 'pi' or k.startswith('head_pi'))
cand = to_mf(load_stl(Path(os.environ.get('CAND', ROOT / 'guide/print/candidates/head-cap-pi-shift/head_cap-pi-shift-world.stl'))))
others = {k: S[k] for k in S if k not in movers and k != 'head_cap'}
others['head_cap (candidate)'] = cand
out = {}
for label, d, capkey in [('V1.6', 0.0, 'head_cap'), ('candidate', DX, 'head_cap (candidate)')]:
    obs = dict(others)
    if label == 'V1.6':
        obs.pop('head_cap (candidate)'); obs['head_cap'] = S['head_cap']
    hits = {}
    for m in movers:
        M = tr(S[m], [-d, 0, 0])
        for k, O in obs.items():
            v = overlap(M, O)
            if v > 1e-3: hits[f'{m} x {k}'] = round(v, 3)
    out[label] = hits
out['obstaclesChecked'] = sorted(others)
print(json.dumps({k: v for k, v in out.items() if k != 'obstaclesChecked'}, indent=1)); json.dump(out, open(HERE / 'final-pose.json', 'w'), indent=1)
