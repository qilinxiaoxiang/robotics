#!/usr/bin/env python3
"""Plot swept sections (sweep_sections.py JSON) in world coordinates with correct holes (even-odd), with optional
rectangles/circles, and report per-part occupancy inside a world box. Pure 2D post-processing (shapely).
Usage: sweep_view.py JSON OUT.png --axes x,y  (world axes for plot horizontal/vertical)
"""
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union


def eo(contours):
    g = Polygon()
    for p in contours:
        if len(p) >= 3:
            g = g.symmetric_difference(Polygon(p).buffer(0))
    return g


def load(path):
    d = json.load(open(path))
    o, e1, e2, n = (np.array(d[k]) for k in ('origin', 'e1', 'e2', 'n'))
    return d, o, e1, e2, n


def to_world(d, pts, h):
    o, e1, e2, n = (np.array(d[k]) for k in ('origin', 'e1', 'e2', 'n'))
    pts = np.asarray(pts)
    return o + pts[:, :1] * e1 + pts[:, 1:2] * e2 + h * n


if __name__ == '__main__':
    path, out = sys.argv[1], sys.argv[2]
    ax_h, ax_v = (sys.argv[3] if len(sys.argv) > 3 else 'x,y').split(',')
    lim = json.loads(sys.argv[4]) if len(sys.argv) > 4 else None
    shapes = json.loads(sys.argv[5]) if len(sys.argv) > 5 else []
    d = json.load(open(path))
    lv = d['levels']
    ix = {'x': 0, 'y': 1, 'z': 2}
    ncol = 5
    nrow = (len(lv) + ncol - 1) // ncol
    fig, axs = plt.subplots(nrow, ncol, figsize=(5 * ncol, 5.6 * nrow), squeeze=False)
    for ax, h in zip(axs.ravel(), lv):
        for dest, col in (('moving', (0.4, 0.6, 1)), ('static', (0.3, 0.3, 0.3))):
            g = eo(d['polygons'][f'{h}:{dest}'])
            geoms = [g] if g.geom_type == 'Polygon' else list(getattr(g, 'geoms', []))
            for G in geoms:
                if G.is_empty:
                    continue
                for ring, fc in [(G.exterior, col)] + [(r, 'white') for r in G.interiors]:
                    W = to_world(d, np.asarray(ring.coords), h)
                    ax.fill(W[:, ix[ax_h]], W[:, ix[ax_v]], color=fc, alpha=0.65 if fc != 'white' else 1.0, lw=0.3, ec='k')
        for s in shapes:
            if s[0] == 'rect':
                ax.add_patch(plt.Rectangle((s[1], s[2]), s[3], s[4], fill=False, color=s[5] if len(s) > 5 else 'g', lw=1.2))
            elif s[0] == 'circle':
                ax.add_patch(plt.Circle((s[1], s[2]), s[3], fill=False, ls='--', color='r'))
            elif s[0] == 'point':
                ax.plot(s[1], s[2], 'm+', ms=8)
        if lim:
            ax.set_xlim(*lim[0])
            ax.set_ylim(*lim[1])
        ax.set_aspect('equal')
        ax.grid(alpha=.4)
        ax.tick_params(labelsize=6)
        ax.set_title(f"n {h}  (world {ax_h} right, {ax_v} up)", fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=55)
