"""Which head-region parts differ between the extracted guide-data snapshot and the current guide/data/guide-data.json?"""
import base64, json, hashlib, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
G = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/data/guide-data.json')
old = np.load(HERE / 'guide-head.npz')
okeys = sorted({k[:-3] for k in old.files})
d = json.loads(G.read_text())
cur = {p['key']: p for p in d['parts']}
out = {'currentSha256': hashlib.sha256(G.read_bytes()).hexdigest(), 'changed': {}, 'missingNow': [], 'same': 0}
LO = np.array([-45.0, -60.0, 95.0]); HI = np.array([105.0, 60.0, 170.0])
for k in okeys:
    if k not in cur: out['missingNow'].append(k); continue
    v = np.frombuffer(base64.b64decode(cur[k]['positionB64']), '<f4').reshape(-1, 3).astype(np.float64)
    ov = old[k + '__v']
    if v.shape == ov.shape and np.allclose(v, ov, atol=1e-6): out['same'] += 1; continue
    out['changed'][k] = {'oldBounds': [ov.min(0).round(3).tolist(), ov.max(0).round(3).tolist()], 'newBounds': [v.min(0).round(3).tolist(), v.max(0).round(3).tolist()],
                         'meanShift': (v.mean(0) - ov.mean(0)).round(3).tolist() if v.shape == ov.shape else None}
new_in_region = []
for k, p in cur.items():
    if k in okeys: continue
    v = np.frombuffer(base64.b64decode(p['positionB64']), '<f4').reshape(-1, 3)
    if not (np.any(v.max(0) < LO) or np.any(v.min(0) > HI)): new_in_region.append(k)
out['newInHeadRegion'] = new_in_region
print(json.dumps(out, indent=1)); json.dump(out, open(HERE / 'guide-drift.json', 'w'), indent=1)
