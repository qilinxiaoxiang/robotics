"""Locate support extrusions inside a review box and report which model faces they reach (print frame of the owner part)."""
import sys, json, re, numpy as np, trimesh; sys.dont_write_bytecode = True; sys.path.insert(0, 'scripts')
import review_native_v16 as V, release_pipeline as r
color, machine, key, boxname = sys.argv[1:5]
prep = r.read('run/preparation.json'); B = V.boxes(prep, color)[boxname]
row = next(x for x in prep['rows'] if x['color'] == color and x['machine'] == machine); t = np.array(next(p['translation'] for p in row['placements'] if p['key'] == key))
part = next(p for p in prep['parts'] if p['key'] == key)
g, cfg, _ = r.native_payload(f'run/native/{color}_{machine}/sliced.3mf')
off = list(map(float, cfg.get('extruder_offset', ['0x0'])[0].split('x'))) if machine == 'Bambu' else [0., 0.]
xyz = [0., 0., 0.]; kind = ''; pts = []
for line in g.decode().splitlines():
    if line.startswith(('; FEATURE:', ';TYPE:')): kind = line.split(':', 1)[1].strip().lower()
    if not re.match(r'^G[0123] ', line): continue
    v = {k: float(q) for k, q in re.findall(r'([XYZE])([-+]?\d*\.?\d+)', line.split(';')[0])}
    end = [v.get(k, xyz[i]) for i, k in enumerate('XYZ')]
    if v.get('E', 0) > 0 and 'support' in kind:
        for f in np.linspace(0, 1, 5):
            p = [xyz[0] + f * (end[0] - xyz[0]) + off[0], xyz[1] + f * (end[1] - xyz[1]) + off[1], end[2]]
            if all(B[0][i] <= p[i] <= B[1][i] for i in range(3)): pts.append(p + [kind])
    xyz = end
P = np.array([p[:3] for p in pts], float); kinds = sorted(set(p[3] for p in pts))
mesh = trimesh.load(part['source']['path'], force='mesh'); T = np.array(part['sourceToPrint']); T[2, 3] += part['dropToBedMm']; mesh.apply_transform(T); mesh.apply_translation(t)
print('support points', len(P), 'kinds', kinds)
print('xyz range', P.min(0).round(2).tolist(), P.max(0).round(2).tolist())
# top contacts: highest support point per 1 mm xy cell, nearest face above it
cells = {}
for p in P:
    k = (round(p[0]), round(p[1]))
    if k not in cells or p[2] > cells[k][2]: cells[k] = p
tops = np.array(list(cells.values()))
ray_o = tops + [0, 0, 0.05]; loc, idx_ray, idx_tri = mesh.ray.intersects_location(ray_o, np.tile([0, 0, 1.0], (len(tops), 1)), multiple_hits=False)
nz = mesh.face_normals[idx_tri][:, 2]; gap = loc[:, 2] - tops[idx_ray][:, 2]
slope = np.degrees(np.arcsin(np.clip(-nz, -1, 1)))
print('top cells', len(tops), 'hit faces', len(idx_tri))
order = np.argsort(tops[idx_ray][:, 2])
inv = np.linalg.inv(T)
Ws = None
try:
    W = np.array(json.load(open('evidence/cap-notch-report-snapshot.json'))['worldToPrint']['matrix4x4']); Ws = np.linalg.inv(W)
except Exception: pass
rows = []
for i in order:
    pp = loc[i] - t; pw = (Ws @ np.r_[pp, 1])[:3] if Ws is not None and key == 'head_cap' else pp
    rows.append(dict(supportTop=tops[idx_ray[i]].round(2).tolist(), faceZ=round(float(loc[i][2]), 2), gap=round(float(gap[i]), 2), faceOverhangFromHorizontalDeg=round(90 - float(slope[i]), 1), faceWorld=np.round(pw, 2).tolist()))
for x in rows[:: max(1, len(rows) // 25)]: print(x)
json.dump(rows, open(f'review/{color}_{machine}-{boxname}-support-contacts.json', 'w'), indent=1)
