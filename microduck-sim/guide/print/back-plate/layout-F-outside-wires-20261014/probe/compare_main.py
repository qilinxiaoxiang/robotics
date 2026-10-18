import json, numpy as np, trimesh
from pathlib import Path
H = Path(__file__).resolve().parent.parent; LF = H.parent / 'layout-F'; OPT = H.parent / 'layout-F-ear-20261014' / 'options'
out = {}
for a, b in ((H / 'frame_hidden_noP1-world.stl', LF / 'rear_frame-world.stl'), (OPT / 'lid_hidden-world.stl', LF / 'rear_lid-world.stl')):
    A = trimesh.load(str(a), force='mesh'); B = trimesh.load(str(b), force='mesh')
    pa, _ = trimesh.sample.sample_surface(A, 60000, seed=1); pb, _ = trimesh.sample.sample_surface(B, 60000, seed=1)
    _, dab, _ = trimesh.proximity.closest_point(B, pa); _, dba, _ = trimesh.proximity.closest_point(A, pb)
    out[f'{a.name} vs layout-F/{b.name}'] = dict(volA=round(float(A.volume), 1), volB=round(float(B.volume), 1), maxSurfDevMm=round(float(max(dab.max(), dba.max())), 3))
(H / 'probe' / 'compare_main.json').write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
