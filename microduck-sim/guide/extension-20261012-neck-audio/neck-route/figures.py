#!/usr/bin/env python3
"""Figures for the README (png/): exact sections of the narrowest places, the route overlay and the channel profile.
Inputs: SCRATCH/sec-*-q0.npz (sections.py), SCRATCH/occ-nonotch-cables.npz (occ.py cables), route-candidates.json,
sections.json, corridors.json, disconnect.json (if present). Draws only; every number shown comes from those files.
"""
import json
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Patch, Rectangle  # noqa: E402

sys.path.insert(0, __import__('os').path.dirname(__file__))
from nr_lib import HERE, SCRATCH  # noqa: E402

OUT = HERE / 'png'
OUT.mkdir(exist_ok=True)
CMAP = plt.get_cmap('tab20')


def section_panel(ax, name, title):
    d = np.load(SCRATCH / f'sec-{name}-q0.npz', allow_pickle=True)
    L, lo, res, comp, names = d['L'], d['lo'], float(d['res']), d['comp'], list(d['names'])
    D = d['D']
    n = L.shape[0]
    ext = [lo[0], lo[0] + res * (n - 1), lo[1], lo[1] + res * (n - 1)]
    rgb = np.ones(L.shape + (3,))
    rgb[comp] = (0.86, 0.95, 0.86)
    handles = [Patch(color=(0.86, 0.95, 0.86), label='free passage')]
    for k, i in enumerate([i for i in np.unique(L) if i > 0]):
        col = CMAP(k % 20)[:3]
        rgb[L == i] = col
        handles.append(Patch(color=col, label=str(names[i])))
    ax.imshow(np.transpose(rgb, (1, 0, 2)), origin='lower', extent=ext, interpolation='nearest')
    Dm = np.where(comp, D, 0)
    k = np.unravel_index(np.argmax(Dm), Dm.shape)
    c = lo + res * np.array(k)
    r = float(Dm[k])
    ax.add_patch(Circle(c, r, fill=False, ec='k', lw=1.5))
    ax.add_patch(Circle(c, 3.35, fill=False, ec='red', lw=1.2, ls='--'))
    ax.text(c[0], c[1] + r + 0.6, f'largest circle {2 * r:.2f} mm', ha='center', fontsize=8)
    ax.text(c[0], c[1] - 3.35 - 1.2, 'V1.8 bundle 6.7 mm (red)', ha='center', fontsize=8, color='red')
    ax.set_title(title, fontsize=9)
    ax.set_xlabel('x (mm)' if 'z' in name else 'y (mm)')
    ax.set_ylabel('y (mm)' if 'z' in name else 'z (mm)')
    ax.legend(handles=handles, fontsize=6, loc='upper right', framealpha=0.85)
    ax.grid(alpha=0.3)


def fig_sections():
    specs = [('slot-minus-y-z129', 'Narrowest point of route A: -y slot at z 129.1\n(yaw link | jaw support), head at rest'),
             ('chan-minus-y-z108', 'Route A lower channel at z 108\n(ID13 | lower-shell collar)'),
             ('gap-plus-y-z127', 'Route B: +y gap at z 127.3\n(yaw link | jaw servo ID15, servo cable inside)')]
    fig, axs = plt.subplots(1, 3, figsize=(17, 6))
    for ax, (n, t) in zip(axs, specs):
        section_panel(ax, n, t)
    fig.suptitle('Exact sections (manifold slice, 0.05 mm raster), robot frame mm, existing servo cables as obstacles', fontsize=10)
    plt.tight_layout()
    fig.savefig(OUT / 'narrowest-sections.png', dpi=110)
    plt.close(fig)


def fig_routes():
    occ = np.load(SCRATCH / 'occ-nonotch-cables.npz')
    O, lo, p = occ['occ'] > 0, occ['lo'], float(occ['pitch'])
    spec = json.loads((HERE / 'route-candidates.json').read_text())
    sec = json.loads((HERE / 'sections.json').read_text())['sections']
    dc = json.loads((HERE / 'disconnect.json').read_text()).get('chosen') if (HERE / 'disconnect.json').exists() else None
    cols = {'current-external': 'tab:gray', 'A-minus-y-channel': 'tab:red', 'B-plus-y-gap': 'tab:blue'}
    fig, axs = plt.subplots(1, 2, figsize=(15, 8))
    views = [(axs[0], (0, 2), 1, 'Side view from -y (x forward, z up); silhouette of every part with y < 0'),
             (axs[1], (1, 2), 0, 'Rear view (y left, z up); silhouette of every part')]
    for ax, (a, b), drop, title in views:
        M = O.copy()
        if drop == 1:
            ny = int(round((0 - lo[1]) / p))
            M = M[:, :ny, :]
        sil = M.any(axis=drop)
        ext = [lo[a], lo[a] + p * (sil.shape[0] - 1), lo[b], lo[b] + p * (sil.shape[1] - 1)]
        ax.imshow(sil.T, origin='lower', extent=ext, cmap='Greys', alpha=0.35, interpolation='nearest')
        for r in spec['routes']:
            P = np.array([q[:3] for q in r['points']], float)
            ax.plot(P[:, a], P[:, b], '-o', ms=3, lw=2, color=cols.get(r['name'], 'k'), label=r['name'])
        for nm, mk in (('slot-minus-y-z129', 'r*'), ('gap-plus-y-z127', 'b*')):
            c = sec[nm]['q0']['withExistingCables']['centreHeadFrame']
            ax.plot(c[a], c[b], mk, ms=14)
            ax.annotate(f"{nm}: {sec[nm]['q0']['withExistingCables']['diameterMm']} mm", (c[a], c[b]), xytext=(8, 8),
                        textcoords='offset points', fontsize=8)
        if dc:
            bl, sz = np.array(dc['minCornerQ0']), np.array(dc['sizeMm'])
            ax.add_patch(Rectangle((bl[a], bl[b]), sz[a], sz[b], fill=False, ec='tab:green', lw=2, label='inline disconnect envelope'))
        ax.set_xlim(-45, 85) if a == 0 else ax.set_xlim(-50, 50)
        ax.set_ylim(25, 160)
        ax.set_aspect('equal')
        ax.set_title(title, fontsize=9)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc='lower right')
    plt.tight_layout()
    fig.savefig(OUT / 'route-overlay.png', dpi=100)
    plt.close(fig)


def fig_profile():
    sec = json.loads((HERE / 'sections.json').read_text())['sections']
    fig, ax = plt.subplots(figsize=(8, 5))
    for prefix, extra, col, lab in (('chan-minus-y-z', ['slot-minus-y-z129'], 'tab:red', 'route A, -y channel'),
                                    ('gap-plus-y-z', ['gap-plus-y-z115', 'gap-plus-y-z127'], 'tab:blue', 'route B, +y gap')):
        names = sorted([k for k in sec if k.startswith(prefix)] + extra, key=lambda k: float(sec[k]['plane'].split('=')[1]))
        z = [float(sec[k]['plane'].split('=')[1]) for k in names]
        w = [2 * sec[k]['q0']['withExistingCables']['radiusMm'] for k in names]
        wp = [2 * sec[k]['minWithCablesPolicyMm'] for k in names]
        ax.plot(w, z, '-o', color=col, label=f'{lab}: head at rest')
        ax.plot(wp, z, '--', color=col, alpha=0.6, label=f'{lab}: worst head roll in the policy range')
    ax.axvline(6.7, color='k', ls=':', label='V1.8 round bundle 6.7 mm')
    ax.axvline(2.54 * np.sqrt(2), color='gray', ls=':', label='1-pin Dupont housing diagonal 3.59 mm')
    ax.set_xlabel('largest free circle diameter in the section (mm), existing servo cables counted')
    ax.set_ylabel('section height z (mm, robot frame at rest)')
    ax.set_xlim(0, 25)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7)
    ax.set_title('Passage width up the two routes into the head (sections clipped to an 18 mm window)', fontsize=9)
    plt.tight_layout()
    fig.savefig(OUT / 'channel-profile.png', dpi=110)
    plt.close(fig)


if __name__ == '__main__':
    fig_sections()
    fig_routes()
    fig_profile()
    print('written', sorted(x.name for x in OUT.iterdir()))
