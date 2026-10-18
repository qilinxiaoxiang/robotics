"""Every guide cable against the V1.9 pack body, with the V1.8 body as baseline (cables.py test, pack only). Writes check_v19_cables.json.

Each cable in guide-data.json is sampled as cables.py does (drawn centripetal Catmull-Rom spline and raw polyline, <= 0.25 mm);
tube penetration depth = radius + signed distance into the body; a run deeper than 0.1 mm is a finding, at an end if it starts or
stops within 8 mm of a cable end (cable_fix.END_MM). Only the pack body changed, so the other solids keep the guide audit result
(cables.py 2026-10-13: 22 cables, 10 findings, all terminal ends, zero mid-route).
"""
import sys, json
from pathlib import Path
import numpy as np
import trimesh
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'rear-pack'))
import pack_lib as P  # noqa: E402
from cables import THRESH, arclen, polyline_samples, runs, spline_samples  # noqa: E402  (interference-audit on sys.path via pack_lib)

END_MM = 8.0
G = HERE.parent.parent
data = json.load(open(G / 'data' / 'guide-data.json'))
bodies = {'V1.9': P.load_stl(HERE / 'rear_pack-world.stl'), 'V1.8': P.load_stl(HERE.parent / 'rear-pack' / 'rear_pack-world.stl')}
res = {'cables': {}, 'midRouteFindings': {'V1.9': [], 'V1.8': []}}
for c in data['cables']:
    r = float(c.get('radius') or 0.9)
    path = np.array(c['path'], float)
    row = {'radius': r}
    for tag, mesh in bodies.items():
        lo, hi = mesh.bounds[0] - r - 3.0, mesh.bounds[1] + r + 3.0
        out = {'minClearanceMm': None, 'findings': []}
        best = None
        for mode, (x, seg) in (('drawn-spline', spline_samples(path)), ('polyline', polyline_samples(path))):
            near = np.all((x >= lo) & (x <= hi), axis=1)
            if not near.any():
                continue
            sd = np.full(len(x), -np.inf)
            idx = np.flatnonzero(near)
            for q in range(0, len(idx), 256):
                sd[idx[q:q + 256]] = trimesh.proximity.signed_distance(mesh, x[idx[q:q + 256]])
            depth = sd + r
            k = int(np.argmax(depth))
            if mode == 'drawn-spline':
                best = dict(minClearanceMm=round(float(-depth[k]), 3), at=np.round(x[k], 2).tolist())
            s = arclen(x)
            for i, j in runs(depth > THRESH):
                kk = i + int(np.argmax(depth[i:j + 1]))
                f = dict(mode=mode, segments=sorted({int(v) for v in seg[i:j + 1]}), depthMm=round(float(depth[kk]), 3),
                         deepestPoint=np.round(x[kk], 2).tolist(),
                         atEnd='start' if s[i] < END_MM else ('end' if s[-1] - s[j] < END_MM else None))
                out['findings'].append(f)
                if f['atEnd'] is None:
                    res['midRouteFindings'][tag].append(dict(cable=c['id'], **f))
        if best:
            out.update(best)
        row[tag] = out
    res['cables'][c['id']] = row
changed = {}
for cid, row in res['cables'].items():
    a, b = row['V1.8'].get('minClearanceMm'), row['V1.9'].get('minClearanceMm')
    if a is not None and b is not None and abs(a - b) > 1e-3:
        changed[cid] = dict(V18=a, V19=b, at=row['V1.9'].get('at'))
res['clearanceChanged'] = changed
res['summary'] = {tag: dict(cablesNearPack=sum(1 for r in res['cables'].values() if r[tag].get('minClearanceMm') is not None),
                            findings=sum(len(r[tag]['findings']) for r in res['cables'].values()),
                            midRoute=len(res['midRouteFindings'][tag])) for tag in bodies}
json.dump(res, open(HERE / 'check_v19_cables.json', 'w'), indent=1)
print(json.dumps(res['summary']), json.dumps(changed), json.dumps(res['midRouteFindings']))
