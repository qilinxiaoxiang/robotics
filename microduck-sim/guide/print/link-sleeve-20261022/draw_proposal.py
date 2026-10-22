"""Proposal picture: section through the ankle shaft before (link + separate sleeve) and after (one-piece link), and the two
links in 3D. Writes proposal.png.
    /tmp/microduck-cad-venv/bin/python draw_proposal.py
"""
from pathlib import Path
import numpy as np, trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import section_now as S
HERE = Path(__file__).resolve().parent


def shade(ax, m, colour, offset=(0, 0, 0)):
    m = m.copy(); m.apply_translation(offset); n = m.face_normals; L = np.array([.4, -.5, .8]); L /= np.linalg.norm(L)
    k = .45 + .55 * np.clip(n @ L, 0, 1); c = np.array(matplotlib.colors.to_rgb(colour))
    ax.add_collection3d(Poly3DCollection(m.triangles, facecolors=np.clip(c[None] * k[:, None] + .08, 0, 1), linewidths=0))


ms = S.parts('right')
new = {k: v for k, v in ms.items() if k not in ('link', 'sleeve')}; new['link'] = trimesh.load(HERE / 'STL/right-link-local.stl', process=True)
fig = plt.figure(figsize=(15, 10.5))
fig.suptitle('Right ankle, passive side: black sleeve grown onto the lower-leg link (left leg the same, mirrored)', fontsize=14)
for i, (title, parts) in enumerate((('Now: link + separate black sleeve (OD 14.6, bore 10.4, 2.8 wide)', ms),
                                    ('Proposal: one-piece link, same 14.6 mm outer face, gaps under and inside the sleeve filled', new))):
    ax = fig.add_subplot(2, 2, i + 1); S.draw(ax, parts, title); ax.set_xlim(-14, 14); ax.set_ylim(-8, 6)
    ax.annotate('turns here: 14.6 mm face\nin the 15 mm pocket', xy=(7.3, 0), xytext=(9.5, -6.5), fontsize=8, arrowprops=dict(arrowstyle='->'))
old = trimesh.load(S.SIM / 'build-pack-20260913/assembly/print-parts/community-32.stl', process=True)
P2L = np.array(__import__('json').loads((HERE / 'link-check.json').read_text())['sides']['right']['printToLocal'])
sl = ms['sleeve'].copy().apply_transform(np.linalg.inv(P2L))
nw = trimesh.load(HERE / 'STL/right-link-print.stl', process=True)
for j, (title, items) in enumerate((('Now: two prints', [(old, '#3a3a3a', (0, 0, 0)), (sl, '#9a9a9a', (0, 0, 9))]),
                                     ('Proposal: one print (black), as it lies on the bed', [(nw, '#3a3a3a', (0, 0, 0))]))):
    ax = fig.add_subplot(2, 2, 3 + j, projection='3d')
    for m, c, o in items: shade(ax, m, c, o)
    ax.set_xlim(-14, 14); ax.set_ylim(-32, 32); ax.set_zlim(-2, 20); ax.view_init(30, -60); ax.set_box_aspect((28, 64, 22), zoom=1.6); ax.set_axis_off()
    ax.set_title(title, fontsize=10)
    if j == 0: ax.text(0, 23, 21, 'sleeve lifted off its boss', fontsize=8, ha='center')
fig.savefig(HERE / 'proposal.png', dpi=110, bbox_inches='tight')
