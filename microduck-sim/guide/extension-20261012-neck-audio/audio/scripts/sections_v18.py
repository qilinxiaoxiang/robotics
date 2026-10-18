#!/usr/bin/env python3
"""Section drawings of the V1.8 head (no audio) to find free volume. Writes ../png/v18-sections-*.png.
Usage: sections_v18.py [extra.stl ...]  (extra robot-frame solids drawn in red, e.g. study parts)."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh

from scene import HEAD_KEYS_FIXED, STUDY, load_tm, manifest, pi_group_keys

COL = {'head_cap': '#d97706', 'head_bottom': '#ca8a04', 'face_panel': '#64748b', 'eye_trim': '#64748b',
       'camera_board': '#16a34a', 'motor15': '#1e293b', 'jaw_support': '#7c3aed', 'jaw_frame': '#a855f7',
       'mouth_sliding_ring': '#7c3aed'}


def draw(ax, m, plane_o, plane_n, axes, color, lw=0.8):
    s = m.section(plane_origin=plane_o, plane_normal=plane_n)
    if s is None:
        return
    for e in s.entities:
        p = s.vertices[e.points]
        ax.plot(p[:, axes[0]], p[:, axes[1]], color=color, lw=lw)


def main():
    man = manifest()
    keys = HEAD_KEYS_FIXED + ['head_cap', 'jaw_frame'] + pi_group_keys(man)
    meshes = {k: load_tm(k) for k in keys}
    extra = [trimesh.load(p, force='mesh') for p in sys.argv[1:]]
    out = STUDY / 'png'
    out.mkdir(exist_ok=True)
    jobs = [('z', z) for z in (122, 128, 132, 136, 140, 144, 148)] + [('x', x) for x in (-20, 0, 10, 25, 40, 50, 66, 72)] + \
           [('y', y) for y in (-36, -28, -20, 20, 28, 36)]
    for ax_name, val in jobs:
        i = 'xyz'.index(ax_name)
        n = np.eye(3)[i]
        o = n * val
        axes = [j for j in range(3) if j != i]
        fig, ax = plt.subplots(figsize=(9, 6))
        for k, m in meshes.items():
            c = COL.get(k, '#0ea5e9' if k.startswith('head_pi') or k == 'pi' else '#94a3b8')
            if k.endswith('_receiving'):
                c = '#dc2626'
            draw(ax, m, o, n, axes, c)
        for m in extra:
            draw(ax, m, o, n, axes, '#e11d48', 1.4)
        ax.set_aspect('equal')
        ax.grid(True, lw=0.3)
        ax.set_xlabel('xyz'[axes[0]] + ' mm')
        ax.set_ylabel('xyz'[axes[1]] + ' mm')
        ax.set_title(f'V1.8 head section {ax_name} = {val} mm (orange cap, yellow lower shell, blue Pi, red housings, '
                     f'purple jaw, black motor15)', fontsize=8)
        fig.tight_layout()
        tag = sys.argv[1:] and 'study' or 'v18'
        fig.savefig(out / f'{tag}-section-{ax_name}{val:+d}.png', dpi=110)
        plt.close(fig)
        print(ax_name, val, flush=True)


if __name__ == '__main__':
    main()
