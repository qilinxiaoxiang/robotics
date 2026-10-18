#!/usr/bin/env python3
"""Section drawings of the V1.8 rails and the study options, with every neighbour.

usage: render_options.py V18|A|B   -> ../png/<opt>-sections.png
Orange = cap (option), blue = separate option parts, grey = neighbours (head solids, yaw body over roll +-25, jaw
0..40, Pi group with 13 housings, cable tubes, audio layout), red dots = cap faces that point down in the print pose at
less than 30 deg from the print horizontal (support candidates), green dashed = neck-route keep-outs.
"""
from __future__ import annotations

import json
import sys

import manifold3d as m3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh

from neighbourhood import draw, obstacles
from pm_lib import CAP_V18, SCREWS, SOURCE_TO_PRINT, STUDY, Head, corridor_keepouts, load_stl_man

S = STUDY / 'study-solids'


def main(opt):
    if opt == 'V18':
        cap_path, parts = CAP_V18, {}
    else:
        cfg = json.loads((STUDY / f'{opt}-parts.json').read_text())
        cap_path = S / cfg['cap']
        parts = {k: load_stl_man(S / v) for k, v in cfg['parts'].items() if not k.startswith('cap_added')}
    cap = load_stl_man(cap_path)
    tm = trimesh.load(cap_path, force='mesh')
    R = SOURCE_TO_PRINT[:3, :3]
    n = tm.face_normals @ R.T
    th = np.degrees(np.arccos(np.clip(-n[:, 2], -1, 1)))
    ov = tm.triangles_center[(n[:, 2] < 0) & (th < 30)]
    H = Head(cap_override=cap)
    ob = obstacles(H)
    union = m3.Manifold.batch_boolean(list(ob.values()), m3.OpType.Add)
    keep = corridor_keepouts()
    fig, axs = plt.subplots(3, 4, figsize=(19, 15))
    planes = [('z', 120.0), ('z', 132.0), ('z', 141.0)]
    for col, sgn in enumerate((-1, 1)):
        for row, (_, z) in enumerate(planes):
            a = axs[row, col]
            draw(a, cap, [0, 0, 1], z, None, color='#d97706', lw=1.1)
            draw(a, union, [0, 0, 1], z, None, color='#64748b', lw=0.5)
            for P in parts.values():
                draw(a, P, [0, 0, 1], z, None, color='#2563eb', lw=1.1)
            for K in keep.values():
                draw(a, K, [0, 0, 1], z, None, color='#16a34a', lw=0.8, ls='--')
            m = np.abs(ov[:, 2] - z) < 0.6
            a.scatter(ov[m, 0], ov[m, 1], s=3, color='#dc2626')
            for c in SCREWS.values():
                if np.sign(c[1]) == sgn:
                    a.plot(c[0], c[1], 'kx')
            a.set_xlim(40, 66); a.set_ylim(sorted((sgn * 20, sgn * 44))); a.set_aspect('equal'); a.grid(lw=0.3)
            a.set_title(f'{opt}: plan z = {z:.0f} ({"-y" if sgn < 0 else "+y"} rail)', fontsize=8)
        for row, y in enumerate((29.0, 31.5, 33.5)):
            a = axs[row, 2 + col]
            yy = sgn * y
            draw(a, cap, [0, 1, 0], yy, None, color='#d97706', lw=1.1)
            draw(a, union, [0, 1, 0], yy, None, color='#64748b', lw=0.5)
            for P in parts.values():
                draw(a, P, [0, 1, 0], yy, None, color='#2563eb', lw=1.1)
            m = np.abs(ov[:, 1] - yy) < 0.6
            a.scatter(ov[m, 0], ov[m, 2], s=3, color='#dc2626')
            for c in SCREWS.values():
                if np.sign(c[1]) == sgn:
                    a.plot(c[0], c[2], 'kx')
            a.set_xlim(40, 66); a.set_ylim(110, 152); a.set_aspect('equal'); a.grid(lw=0.3)
            a.set_title(f'{opt}: side section y = {yy:+.1f}', fontsize=8)
    fig.suptitle(f'{opt}: orange cap, blue separate parts, grey neighbours (roll/jaw swept, Pi + housings, cables, audio), '
                 'red = print-down faces < 30 deg (support candidates), green dashed = neck-route keep-outs, x = Pi screws',
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(STUDY / f'png/{opt}-sections.png', dpi=95)
    plt.close(fig)


if __name__ == '__main__':
    main(sys.argv[1])
