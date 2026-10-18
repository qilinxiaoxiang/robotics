#!/usr/bin/env python3
"""Step 1c: check that each print/world part is the geometry the guide draws (check only, no solid writes).

register_v16.py proves the unchanged parts against the V1.6 release files. The keys in ia_lib.WORLD_FILE (the
V1.7 notched tray and trimmed OpenRB board, and the V1.8 head set: cap, face panel, eye trim, lower head shell and
the turned camera) are superseded by print/world files, so this script compares the guide's display mesh for each
of those keys with its print/world file by the same method: rigid invariants (volume, area, principal moments of
inertia) and, when the bounds differ, a rigid ICP registration (no scale or reflection) with a two-sided
point-to-surface residual. It also records the file sha256 against print/world/v18-sources.json, so the audited
geometry is tied to the V1.8 build outputs. Writes v18-registration.json.
"""
from __future__ import annotations

import gc
import hashlib
import json

import numpy as np
import trimesh

from ia_lib import HERE, WORLD, WORLD_FILE, decode_guide_part, load_guide, rnd
from register_v16 import invariants, register, residual


def main():
    guide = load_guide()
    gparts = {p['key']: p for p in guide['parts']}
    src_path = WORLD / 'v18-sources.json'
    sources = json.loads(src_path.read_text())['files'] if src_path.exists() else {}
    out = []
    for key, name in WORLD_FILE.items():
        path = WORLD / name
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        rel = trimesh.load(path, force='mesh', process=True)
        gv, gf = decode_guide_part(gparts[key])
        ref = trimesh.Trimesh(gv, gf, process=True)
        ir, ig = invariants(rel), invariants(ref)
        rel_err = max(abs(ir['volume'] - ig['volume']) / ig['volume'], abs(ir['area'] - ig['area']) / ig['area'],
                      *[abs(a - b) / max(abs(b), 1e-9) for a, b in zip(ir['moments'], ig['moments'])])
        in_world = np.abs(rel.bounds - ref.bounds).max() < 0.05
        T = np.eye(4) if in_world else register(rel, ref)
        reg = rel.copy()
        reg.apply_transform(T)
        mx, p99 = residual(reg, ref)
        decimated = len(gf) < len(rel.faces) * 0.9
        same = rel_err < 1e-3 and mx < 0.5
        rec = {'key': key, 'worldFile': f'guide/print/world/{name}', 'sha256': sha,
               'v18Source': ({'sourceFile': sources[name]['sourceFile'], 'sha256': sources[name]['sha256'],
                              'fileMatchesSource': sources[name]['sha256'] == sha} if name in sources else None),
               'guideReference': 'guide-data.json display mesh (' + guide.get('revision', '?') + ')',
               'placement': 'file in robot frame (bounds equal)' if in_world else 'rigid ICP registration onto guide display mesh',
               'transformFileToGuide': rnd(T, 6),
               'rigidInvariantMaxRelativeError': float(f'{rel_err:.3g}'),
               'icpResidualMaxMm': rnd(mx, 4), 'icpResidualP99Mm': rnd(p99, 4),
               'fileVolumeMm3': rnd(ir['volume'], 2), 'guideVolumeMm3': rnd(ig['volume'], 2),
               'fileTriangles': int(len(rel.faces)), 'guideTriangles': int(len(gf)),
               'guideShowsWorldFile': bool(same),
               'note': ('Guide display mesh is decimated by build_guide_data.py; the audit solid is the full file '
                        '(solids-report.json displayVsSolid gives the deviation).' if decimated and not same else
                        'Equal volume, area and principal moments plus a sub-0.5 mm ICP residual: same rigid geometry. '
                        'build_solids.py uses the file itself as the audit solid.')}
        out.append(rec)
        print(key, rec['placement'][:12], 'inv', rec['rigidInvariantMaxRelativeError'], 'res', rnd(mx, 4), 'same', same, flush=True)
        del rel, ref, reg
        gc.collect()
    (HERE / 'v18-registration.json').write_text(json.dumps({'guideRevision': guide.get('revision'), 'parts': out}, indent=1))
    print(json.dumps({'parts': len(out), 'same': sum(r['guideShowsWorldFile'] for r in out),
                      'notSame': [r['key'] for r in out if not r['guideShowsWorldFile']]}))


if __name__ == '__main__':
    main()
