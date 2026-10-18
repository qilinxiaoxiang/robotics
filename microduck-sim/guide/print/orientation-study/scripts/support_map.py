#!/usr/bin/env python3
"""Plot where a native slice puts support: support toolpath midpoints over the part, top and side views, plus the
part's faces that touch support (within 0.6 mm above a support toolpath) shaded red.

    run_bounded_cad.py ... -- /tmp/microduck-cad-venv/bin/python scripts/support_map.py RUN_DIR COLOR MACHINE OUT.png [OUT.json]

Read-only on the slice. OUT.json lists the support-touched face area by face orientation (down / side / up).
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / 'scripts'))
sys.dont_write_bytecode = True
from orientation_check import load_mesh  # noqa: E402
from seat_support import support_segments, rp  # noqa: E402


def main():
    run, color, machine, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
    prep = json.loads((run / 'preparation.json').read_text())
    part = prep['parts'][0]
    row = next(r for r in prep['rows'] if r['color'] == color and r['machine'] == machine)
    T = np.array(part['sourceToPrint'], float)
    T[2, 3] += part['dropToBedMm']
    T[:3, 3] += np.array(row['placements'][0]['translation'], float)
    g, cfg, _ = rp.native_payload(run / 'native' / f'{color}_{machine}' / 'sliced.3mf')
    offset = list(map(float, cfg.get('extruder_offset', ['0x0'])[0].split('x'))) if machine == 'Bambu' else [0.0, 0.0]
    segs, iface = support_segments(g, offset)
    m = load_mesh(part['source']['path'])
    m.apply_transform(T)
    # Faces touched by support: face centre within 0.6 mm above (and 1.5 mm laterally of) an interface/support point.
    touched = np.zeros(len(m.faces), bool)
    if len(segs):
        tree = cKDTree(segs[:, :2])
        c = m.triangles_center
        for i, near in enumerate(tree.query_ball_point(c[:, :2], r=1.0)):
            if near:
                dz = c[i, 2] - segs[near, 2]
                touched[i] = np.any((dz >= -0.05) & (dz <= 0.6))
    nz = m.face_normals[:, 2]
    a = m.area_faces
    summary = dict(machine=machine, supportTouchedFaceMm2=dict(
        down=round(float(a[touched & (nz < -0.7)].sum()), 1), side=round(float(a[touched & (abs(nz) <= 0.7)].sum()), 1),
        up=round(float(a[touched & (nz > 0.7)].sum()), 1)), supportToolpathMm=round(float(segs[:, 3].sum()) if len(segs) else 0, 1))
    fig, ax = plt.subplots(1, 3, figsize=(15, 5))
    v = m.vertices
    for k, (i, j, name) in enumerate([(0, 1, 'top view X-Y'), (0, 2, 'side view X-Z'), (1, 2, 'side view Y-Z')]):
        tri = m.faces
        ax[k].tripcolor(v[:, i], v[:, j], tri, facecolors=np.where(touched, 1.0, 0.25), cmap='Greys', vmin=0, vmax=1.6,
                        edgecolors='none', alpha=0.35)
        if len(segs):
            ax[k].scatter(segs[:, i], segs[:, j], s=0.3, c=np.where(iface, 'tab:red', 'tab:orange'), alpha=0.5)
        hit = m.triangles_center[touched]
        ax[k].scatter(hit[:, i], hit[:, j], s=0.5, c='tab:blue', alpha=0.6)
        ax[k].set_aspect('equal')
        ax[k].set_title(name)
    fig.suptitle(f"{run.parent.parent.name}/{run.parent.name} {machine}: support toolpaths (orange; interface red); "
                 f"part faces resting on support (blue)")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    if len(sys.argv) > 5:
        Path(sys.argv[5]).write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
