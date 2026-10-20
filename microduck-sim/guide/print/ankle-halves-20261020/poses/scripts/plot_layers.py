#!/usr/bin/env python3
"""Plot a native slice: first layer (model / brim / support midpoints by feature) and a side view of all support
midpoints with the part outline. Read-only.
    /tmp/microduck-cad-venv/bin/python plot_layers.py RUN_DIR COLOR MACHINE OUT.png
"""
import json, sys
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.dont_write_bytecode = True
from face_support import model_segments, support_segments, r2, load_mesh  # noqa: E402
run, color, machine, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
prep = json.loads((run / 'preparation.json').read_text()); part = prep['parts'][0]
row = next(r for r in prep['rows'] if r['color'] == color and r['machine'] == machine)
T = np.array(part['sourceToPrint'], float); T[2, 3] += part['dropToBedMm']; T[:3, 3] += np.array(row['placements'][0]['translation'], float)
g, cfg, _ = r2.native_payload(run / 'native' / f'{color}_{machine}' / 'sliced.3mf')
offset = list(map(float, cfg.get('extruder_offset', ['0x0'])[0].split('x'))) if machine == 'Bambu' else [0.0, 0.0]
segs, iface = support_segments(g, offset); msegs, mkinds = model_segments(g, offset)
m = load_mesh(part['source']['path']); m.apply_transform(T)
z1 = float(cfg['initial_layer_print_height'])
fig, ax = plt.subplots(1, 3, figsize=(18, 6))
sel = abs(msegs[:, 2] - z1) < 1e-4
kinds = sorted(set(mkinds[sel]))
for k in kinds:
    s = sel & (mkinds == k); ax[0].scatter(msegs[s, 0], msegs[s, 1], s=1, label=k)
if len(segs):
    s = abs(segs[:, 2] - z1) < 1e-4; ax[0].scatter(segs[s, 0], segs[s, 1], s=1, c='k', label='support')
ax[0].legend(fontsize=7, markerscale=5); ax[0].set_aspect('equal'); ax[0].set_title(f'first layer z={z1}')
for k, (i, j, name) in enumerate([(0, 2, 'side X-Z'), (1, 2, 'side Y-Z')]):
    v = m.vertices
    ax[k + 1].tripcolor(v[:, i], v[:, j], m.faces, facecolors=np.full(len(m.faces), 0.3), cmap='Greys', vmin=0, vmax=1, alpha=0.3, edgecolors='none')
    if len(segs):
        ax[k + 1].scatter(segs[:, i], segs[:, j], s=0.3, c=np.where(iface, 'tab:red', 'tab:orange'), alpha=0.6)
    ax[k + 1].set_aspect('equal'); ax[k + 1].set_title(name + ' (support orange, interface red)')
fig.suptitle(f"{part['key']} {part.get('poseName')} {machine}"); fig.tight_layout(); fig.savefig(out, dpi=100)
