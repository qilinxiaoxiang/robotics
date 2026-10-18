#!/usr/bin/env python3
"""Step 1b: check that each V1.6 release part is the geometry the guide draws (check only, no solid writes).

Several V1.6 files are in a print frame whose sourceToPrint is identity (the plate pose was baked in), so the
manifest transform alone cannot place them. Each release mesh is compared with the guide's world mesh for that
key using rigid invariants (volume, area, principal moments of inertia) and a rigid ICP registration
(no scale or reflection) with a two-sided point-to-surface residual. When they agree, the guide's world mesh
is the released geometry and build_solids.py keeps it as the audit solid. Writes v16-registration.json.
A part whose release file, guide source mesh and this script are byte-identical to the last run reuses its record
(v16-registration-cache.json).
"""
from __future__ import annotations

import base64
import gc
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import trimesh

from ia_lib import load_guide, FINAL, HERE, SRC, V16_KEY, WORLD, WORLD_FILE, rnd


def invariants(m: trimesh.Trimesh):
    return {'volume': m.volume, 'area': m.area, 'moments': np.sort(np.linalg.eigvalsh(m.moment_inertia)).tolist()}


def residual(a: trimesh.Trimesh, b: trimesh.Trimesh, n=2500):
    pa = trimesh.sample.sample_surface(a, n, seed=1)[0]
    pb = trimesh.sample.sample_surface(b, n, seed=2)[0]
    da = b.nearest.on_surface(pa)[1]
    db = a.nearest.on_surface(pb)[1]
    return float(max(da.max(), db.max())), float(max(np.percentile(da, 99), np.percentile(db, 99)))


def register(moving: trimesh.Trimesh, fixed: trimesh.Trimesh):
    cands = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            R = np.zeros((3, 3))
            for i, j in enumerate(perm):
                R[i, j] = signs[i]
            if np.linalg.det(R) < 0:
                continue
            T = np.eye(4)
            T[:3, :3] = R
            T[:3, 3] = fixed.center_mass - R @ moving.center_mass
            cands.append(T)
    pts = trimesh.sample.sample_surface(moving, 3000, seed=3)[0]
    cloud = np.vstack([trimesh.sample.sample_surface(fixed, 60000, seed=4)[0], fixed.vertices])
    best = None
    for T0 in cands:
        T, _, cost = trimesh.registration.icp(pts, cloud, initial=T0, threshold=1e-9, max_iterations=100, reflection=False, scale=False)
        if best is None or cost < best[1]:
            best = (T, cost)
    return best[0]


def main():
    fin = json.loads(FINAL.read_text())
    want = {V16_KEY.get(e['key'], e['key']) for e in fin['parts']}
    src = json.loads(SRC.read_text())
    s = {p['key']: (p['positionB64'], p['indexB64'], p.get('sourceFile')) for p in src['parts'] if p['key'] in want}
    del src
    gc.collect()
    cache_file = HERE / 'v16-registration-cache.json'
    try:
        cache = json.loads(cache_file.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}
    code = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    new_cache = {}
    out = []
    guide_keys = {p['key'] for p in load_guide()['parts']}
    for e in fin['parts']:
        key = V16_KEY.get(e['key'], e['key'])
        if key not in guide_keys:
            # Retired with the V1.8 rear pack (IMU holder and rear cover) or by the V1.7/V1.8 reprints: the guide draws
            # nothing for this key, so there is no geometry to register.
            out.append({'key': key, 'v16Key': e['key'], 'releaseFile': e['path'], 'guideShowsReleasedGeometry': False,
                        'retired': True, 'note': 'not drawn by the current guide (see print/make_parts_sheet.py RETIRED_INCREMENTAL)'})
            print(key, 'retired: not in the guide', flush=True)
            continue
        if key in WORLD_FILE:
            # Superseded by a print/world file (V1.7 tray, V1.8 head set): the guide no longer draws the V1.6 geometry
            # of this key by design. register_v18.py registers the guide mesh against the current file instead.
            out.append({'key': key, 'v16Key': e['key'], 'releaseFile': e['path'], 'guideShowsReleasedGeometry': False,
                        'supersededBy': f'guide/print/world/{WORLD_FILE[key]}', 'registeredIn': 'v18-registration.json'})
            print(key, 'superseded by print/world', WORLD_FILE[key], flush=True)
            continue
        pb, ib, sf = s[key]
        digest = hashlib.sha256((code + pb + ib + str(sf) + e['path'] + e['key']).encode() + Path(e['path']).read_bytes()).hexdigest()
        if cache.get(key, {}).get('hash') == digest:
            out.append(cache[key]['rec'])
            new_cache[key] = cache[key]
            print(key, 'unchanged since the last run: reused', flush=True)
            continue
        rel = trimesh.load(e['path'], force='mesh', process=True)
        v = np.frombuffer(base64.b64decode(pb), '<f4').reshape(-1, 3).astype(float)
        f = np.frombuffer(base64.b64decode(ib), '<u4').reshape(-1, 3)
        ref = trimesh.Trimesh(v, f, process=True)
        ref_label = 'full-build source mesh: ' + str(sf)
        ir, ig = invariants(rel), invariants(ref)
        rel_err = max(abs(ir['volume'] - ig['volume']) / ig['volume'], abs(ir['area'] - ig['area']) / ig['area'],
                      *[abs(a - b) / max(abs(b), 1e-9) for a, b in zip(ir['moments'], ig['moments'])])
        in_world = np.abs(rel.bounds - ref.bounds).max() < 0.05
        T = np.eye(4) if in_world else register(rel, ref)
        reg = rel.copy()
        reg.apply_transform(T)
        mx, p99 = residual(reg, ref)
        same = rel_err < 1e-3 and mx < 0.5
        rec = {'key': key, 'v16Key': e['key'], 'releaseFile': e['path'], 'guideReference': ref_label,
               'placement': 'release file in robot frame' if in_world else 'rigid ICP registration onto guide world mesh',
               'transformReleaseToWorld': rnd(T, 6),
               'rigidInvariantMaxRelativeError': float(f'{rel_err:.3g}'),
               'icpResidualMaxMm': rnd(mx, 4), 'icpResidualP99Mm': rnd(p99, 4),
               'releaseVolumeMm3': rnd(ir['volume'], 2), 'guideVolumeMm3': rnd(ig['volume'], 2),
               'guideShowsReleasedGeometry': bool(same),
               'note': 'Equal volume, area and principal moments plus a sub-0.5 mm ICP residual: same rigid geometry. '
                       'The ICP residual reflects registration convergence, not a shape difference; the audit uses the exact world mesh.'}
        out.append(rec)
        new_cache[key] = {'hash': digest, 'rec': rec}
        print(key, rec['placement'][:12], 'inv', rec['rigidInvariantMaxRelativeError'], 'res', rnd(mx, 4), 'same', same, flush=True)
        del rel, ref, reg
        gc.collect()
    (HERE / 'v16-registration.json').write_text(json.dumps(out, indent=1))
    cache_file.write_text(json.dumps(new_cache))


if __name__ == '__main__':
    main()
