#!/usr/bin/env python3
"""Three orthographic views of each local-frame STL (faces shaded by normal direction) and the hole/boss list from
orientation_check.detect_holes, to name the functional faces in local coordinates. Read-only.
    /tmp/microduck-cad-venv/bin/python render_local.py
"""
import json, sys
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = Path(__file__).resolve().parent; OUT = HERE.parent / 'renders'
STUDY = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/orientation-study')
sys.path.insert(0, str(STUDY)); sys.dont_write_bytecode = True
from orientation_check import load_mesh, detect_holes  # noqa: E402
l2p = json.loads((HERE.parent / 'local-to-printstl.json').read_text())
holes_out = {}
for key in ['left_base', 'left_cheek', 'right_cheek', 'left_sleeve']:
    m = load_mesh(l2p[key]['localStl'])
    fig, ax = plt.subplots(1, 3, figsize=(18, 6))
    v = m.vertices; n = m.face_normals
    for k, (i, j, name, nd) in enumerate([(0, 1, 'top: X right, Y up (seen from +Z)', 2), (0, 2, 'front: X right, Z up (seen from -Y)', 1), (1, 2, 'side: Y right, Z up (seen from +X)', 0)]):
        # shade by the component of the normal toward the viewer; draw back faces lighter
        col = n[:, nd] if nd != 1 else -n[:, nd]
        order = np.argsort(v[m.faces][:, :, nd].mean(1) * (1 if nd != 1 else -1))
        ax[k].tripcolor(v[:, i], v[:, j], m.faces[order], facecolors=col[order], cmap='coolwarm', vmin=-1, vmax=1, edgecolors='k', linewidth=0.05)
        ax[k].set_aspect('equal'); ax[k].set_title(f'{key} {name}'); ax[k].grid(True, alpha=0.3)
        ax[k].set_xticks(np.arange(np.floor(v[:, i].min() / 5) * 5, v[:, i].max() + 5, 5)); ax[k].set_yticks(np.arange(np.floor(v[:, j].min() / 5) * 5, v[:, j].max() + 5, 5))
    fig.tight_layout(); fig.savefig(OUT / f'{key}-local.png', dpi=110); plt.close(fig)
    rows = []
    for h in detect_holes(m):
        rows.append(dict(kind=h['kind'], diameterMm=round(2 * h['r'], 2), axis=np.round(h['axis'], 3).tolist(),
                         ends=[dict(centre=np.round(e['centre'], 2).tolist(), normal=np.round(e['normal'], 2).tolist(), facetAreaMm2=round(e['facetArea'], 1)) for e in h['ends']]))
    holes_out[key] = rows
    print(key); [print('  ', json.dumps(r)) for r in rows]
(OUT / 'holes-local.json').write_text(json.dumps(holes_out, indent=1) + '\n')
