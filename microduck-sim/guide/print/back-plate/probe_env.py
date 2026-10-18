"""Read-only probe of the environment behind the rear pack cover: shell, pack and leg extents near the converter plate envelope
(x -67..-45, |y| <= 32.05, z -44..43). Writes probe_env.json."""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'rear-pack'))
import pack_lib as P
import ia_lib
OUT = Path(__file__).resolve().parent
man = ia_lib.manifest()
env = (np.array([-75.0, -40.0, -50.0]), np.array([-40.0, 40.0, 50.0]))
res = {'envBox': env}
near = []
for k, rec in sorted(man.items()):
    lo, hi = np.array(rec['bounds'])
    if np.all(lo <= env[1]) and np.all(hi >= env[0]):
        near.append(dict(key=k, module=rec.get('module'), bounds=np.round([lo, hi], 2).tolist()))
res['partsNearEnvelope'] = near
for k in ('shell_left', 'shell_right'):
    m = P.solid_mesh(k); V = m.vertices
    row = {'bounds': np.round(m.bounds, 2).tolist()}
    # minimum x of the shell per z band and the |y| range of the material behind x -44
    sec = []
    for z0 in np.arange(-10, 46, 4.0):
        sel = V[(V[:, 2] >= z0) & (V[:, 2] < z0 + 4)]
        if len(sel) == 0:
            continue
        b = sel[sel[:, 0] < -44.0]
        sec.append(dict(z=[float(z0), float(z0 + 4)], minX=round(float(sel[:, 0].min()), 2),
                        absYbehindXm44=[round(float(np.abs(b[:, 1]).min()), 2), round(float(np.abs(b[:, 1]).max()), 2)] if len(b) else None))
    row['bandsZ'] = sec
    # exact slab test: shell material inside the plate envelope x -67..-46.9
    S = P.mesh_to_m(m)
    for nm, lo, hi in (('box_x-67_-46.9', (-67, -32.05, -36), (-46.9, 32.05, 43)), ('front_slab_x-47_-45_full', (-47, -32.05, -36), (-45, 32.05, 43))):
        bx = P.box(lo, hi); v = float((S ^ bx).volume())
        row[nm] = dict(overlapMm3=round(v, 3), gapMm=round(float(S.min_gap(bx, 5.0)), 3))
        if v > 1e-6:
            row[nm]['overlapBounds'] = np.round(P.from_m(S ^ bx).bounds, 2).tolist()
    res[k] = row
    print(k, json.dumps({kk: vv for kk, vv in row.items() if kk != 'bandsZ'}), flush=True)
for f in ('rear_pack-v18.stl', 'rear_pack.stl', 'rear_pack_cover.stl'):
    m = P.load_stl(P.WORLD / f); res[f] = np.round(m.bounds, 3).tolist()
P.jdump(res, OUT / 'probe_env.json')
print(json.dumps(near, indent=0)[:3000])
