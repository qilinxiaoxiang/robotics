#!/usr/bin/env python3
"""Step 6: section drawings (PNG) of the worst findings, cut from the audit solids.

Each figure is a planar section of the closed audit solids (trimesh.section), filled per part; overlaps are
the exact manifold3d intersection, cut by the same plane and filled red. Cable centrelines are the viewer's
drawn centripetal Catmull-Rom curve projected onto the plane; red dots mark the deepest penetration. Writes png/*.png.
"""
from __future__ import annotations

import json

import manifold3d as m3d
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402

from cables import spline_samples  # noqa: E402
from ia_lib import HERE, decode_guide_part, from_manifold, load_guide, load_solid, to_manifold  # noqa: E402

OUT = HERE / 'png'
OUT.mkdir(exist_ok=True)
COLORS = ['#9e9e9e', '#64b5f6', '#ffb74d', '#81c784', '#ba68c8', '#4db6ac', '#f06292', '#a1887f', '#90a4ae', '#dce775']

PLANES = {  # name: (u, v) in-plane axes; normal = u x v
    'x': ((0, 1, 0), (0, 0, 1)), 'y': ((1, 0, 0), (0, 0, 1)), 'z': ((1, 0, 0), (0, 1, 0))}
LABEL = {'x': ('y (mm, left +)', 'z (mm, up +)'), 'y': ('x (mm, forward +)', 'z (mm, up +)'), 'z': ('x (mm, forward +)', 'y (mm, left +)')}


def frame(axis, c):
    u, v = (np.array(a, float) for a in PLANES[axis])
    n = np.cross(u, v)
    o = {'x': np.array([c, 0, 0]), 'y': np.array([0, c, 0]), 'z': np.array([0, 0, c])}[axis]
    F = np.eye(4)
    F[:3, 0], F[:3, 1], F[:3, 2], F[:3, 3] = u, v, n, o
    return F, n, o


def polys(v, f, axis, c, offset=(0, 0, 0)):
    m = trimesh.Trimesh(np.asarray(v) + np.asarray(offset), f, process=False)
    F, n, o = frame(axis, c)
    s = m.section(plane_origin=o, plane_normal=n)
    if s is None:
        return []
    p2, _ = s.to_planar(to_2D=np.linalg.inv(F), check=False)
    try:
        return list(p2.polygons_full)
    except Exception:
        return []


def draw(ax, pp, color, alpha=0.75, lw=0.6, ec='#333', label=None, hatch=None):
    first = True
    for p in pp:
        if p is None or p.is_empty:
            continue
        rings = [np.asarray(p.exterior.coords)] + [np.asarray(r.coords) for r in p.interiors]
        verts = np.vstack(rings)
        codes = np.concatenate([[MPath.MOVETO] + [MPath.LINETO] * (len(r) - 2) + [MPath.CLOSEPOLY] for r in rings])
        ax.add_patch(PathPatch(MPath(verts, codes), fc=color, ec=ec, lw=lw, alpha=alpha, hatch=hatch,
                               label=label if first else None))
        first = False


def proj(x, axis):
    u, v = (np.array(a, float) for a in PLANES[axis])
    return x @ u, x @ v


def figure(name, title, axis, c, parts, overlaps=(), cables=(), extra=None, xlim=None, ylim=None, note=None, legend_loc='upper right'):
    fig, ax = plt.subplots(figsize=(8, 6), dpi=130)
    for i, (label, v, f, off, style) in enumerate(parts):
        draw(ax, polys(v, f, axis, c, off), style.get('color', COLORS[i % len(COLORS)]), alpha=style.get('alpha', 0.75),
             ec=style.get('ec', '#333'), lw=style.get('lw', 0.6), label=label, hatch=style.get('hatch'))
    for label, man in overlaps:
        v, f = from_manifold(man)
        if len(f):
            draw(ax, polys(v, f, axis, c), '#e53935', alpha=0.95, ec='#b71c1c', lw=0.8, label=label)
    for label, path, r, color, bad in cables:
        x, _ = spline_samples(path)
        a, b = proj(x, axis)
        ax.plot(a, b, color=color, lw=2.2, solid_capstyle='round', label=label, zorder=5)
        if bad is not None:
            ax.scatter(*proj(np.asarray(bad), axis), s=36, c='#e53935', edgecolors='k', zorder=6)
    if extra:
        extra(ax)
    ax.set_aspect('equal')
    if xlim:
        ax.set_xlim(*xlim)
    if ylim:
        ax.set_ylim(*ylim)
    ax.set_xlabel(LABEL[axis][0])
    ax.set_ylabel(LABEL[axis][1])
    ax.set_title(title, fontsize=10)
    if note:
        fig.text(0.01, 0.01, note, fontsize=7.5, va='bottom', wrap=True)
    ax.legend(fontsize=7, loc=legend_loc, framealpha=0.85)
    ax.grid(alpha=0.25)
    fig.tight_layout(rect=(0, 0.06 if note else 0, 1, 1))
    fig.savefig(OUT / f'{name}.png')
    plt.close(fig)
    print('wrote', name)


def S(k):
    return load_solid(k)


def main():
    g = load_guide()
    cab = {c['id']: c for c in g['cables']}
    gp = {p['key']: p for p in g['parts']}

    # 1. Tray side rails against the OpenRB side ports (class a), section at the port centre x = -61.6
    tv, tf = S('openrb_tray')

    def tray_extra(ax):
        for s in (-1, 1):
            y0, y1 = sorted((s * 12.7, s * 22.7))
            ax.add_patch(plt.Rectangle((y0, -48.85), y1 - y0, 4.2, fc='none', ec='#d81b60', lw=1.4, ls='--',
                                       label='mated plug + wire exit (assumed)' if s < 0 else None))
            n0, n1 = sorted((s * 13.0, s * 15.7))
            ax.add_patch(plt.Rectangle((n0, -49.4), n1 - n0, 6.4, fc='none', ec='#2e7d32', lw=1.4, ls=':',
                                       label='proposed rail notch' if s < 0 else None))
    tray = to_manifold(tv, tf)
    ov = []
    for s in (-1, 1):
        y0, y1 = sorted((s * 12.7, s * 22.7))
        box = m3d.Manifold.cube([10.0, y1 - y0, 4.2]).translate([-64.7, y0, -48.85])
        ov.append(('plug envelope inside tray rail' if s < 0 else None, box ^ tray))
    figure('01-tray-rail-blocks-side-ports', 'Class a: tray side rails stand 0.6 mm outside both OpenRB side DXL ports (section x = -61.6)',
           'x', -61.6,
           [('OpenRB tray (V1.6)', tv, tf, (0, 0, 0), {'color': '#ffb74d'}),
            ('OpenRB-150 board', *S('openrb_board'), (0, 0, 0), {'color': '#81c784'}),
            ('power support', *S('power_support'), (0, 0, 0), {'color': '#bdbdbd', 'alpha': 0.5})],
           overlaps=[o for o in ov if o[0]] + [(None, o[1]) for o in ov if not o[0]],
           cables=[('dxl-r5 / dxl-l10 first segment (drawn)', cab['dxl-r5']['path'][:3], 1.1, '#6a3df0', None),
                   (None, cab['dxl-l10']['path'][:3], 1.1, '#6a3df0', None)],
           extra=tray_extra, xlim=(-30, 30), ylim=(-60, -36),
           note='Board side headers: x -64.7..-54.7, mouth at |y| 12.7, z -48.85..-44.65 (from the board solid). Rails: |y| 13.3..15.3, '
                'x -85.5..-58.4, z -54.3..-43.5 (print/tray/tray.py). The plug envelope beyond the mouth is an assumption (JST EH plug + wire bend).')

    # 2. Cables through junction J and the main fuse (class b), side view projection with primitives
    def prim_extra(ax):
        for k, col in (('junction_j', '#ffcc80'), ('fuse_main', '#ef9a9a')):
            v, f = S(k)
            h = trimesh.Trimesh(v, f).convex_hull
            pts = np.c_[h.vertices[:, 0], h.vertices[:, 2]]
            from scipy.spatial import ConvexHull
            hh = ConvexHull(pts)
            ax.fill(pts[hh.vertices, 0], pts[hh.vertices, 1], fc=col, ec='#555', alpha=0.6, label=f'{k} (projection)')
    bad = {'dxl-n12': [[-57.72, -4.63, -16.23], [-48.23, -6.06, -6.97]], 'uart': [[-54.8, 1.02, -17.99]], 'dxl-r5': [[-46.11, -9.99, -0.96]]}
    figure('02-cables-through-junction-and-fuse', 'Class b: dxl-n12, dxl-r5 and uart drawn through junction J and the 10 A fuse (side view, projected on y)',
           'y', 0.0, [],
           cables=[(cid, cab[cid]['path'], cab[cid].get('radius', 0.9), col, bad[cid])
                   for cid, col in (('dxl-n12', '#6a3df0'), ('dxl-r5', '#3949ab'), ('uart', '#00897b'))]
           + [('vout (carries the fuse)', cab['vout']['path'], 1.4, '#d32f2f', None)],
           extra=prim_extra, xlim=(-72, -28), ylim=(-30, 12),
           note='Red dots: deepest penetration of each finding (cables-raw.json). Junction J and the fuse are guide envelopes (build_guide_data.py).')

    # 3. Cables over the power-support top edge (class b), section y = -7.5
    pv, pf = S('power_support')
    figure('03-dxl-links-cut-power-support-edge', 'Class b: dxl-r5 / dxl-n12 tubes 0.8-0.9 mm into the power-support rear top edge (section y = -7.5)',
           'y', -7.5, [('power support', pv, pf, (0, 0, 0), {'color': '#bdbdbd'})],
           cables=[('dxl-r5', cab['dxl-r5']['path'], 1.1, '#3949ab', [[-31.13, -7.97, 33.59]]),
                   ('dxl-n12', cab['dxl-n12']['path'], 1.1, '#6a3df0', [[-31.08, -7.0, 33.51]])],
           xlim=(-50, -5), ylim=(15, 45))

    # 4. Head-bottom approach through the closed jaw (step path), section y = 0 at the worst sample
    hb = S('head_bottom')
    off = np.array([0, 0, -30.0]) * 0.2
    hbm = to_manifold(*hb).translate(list(off))
    figure('04-head-bottom-approach-through-jaw', 'Step head-bottom: lower shell rising from [0,0,-30] cuts the closed jaw (section y = 0, 20% from final)',
           'y', 0.0,
           [('head_bottom at 20% of its approach', hb[0], hb[1], off, {'color': '#fff176'}),
            ('jaw_frame', *S('jaw_frame'), (0, 0, 0), {'color': '#90caf9'}),
            ('lower_pad', *S('lower_pad'), (0, 0, 0), {'color': '#a5d6a7'})],
           overlaps=[('path overlap', hbm ^ to_manifold(*S('jaw_frame'))), (None, hbm ^ to_manifold(*S('lower_pad')))],
           xlim=(-35, 95), ylim=(85, 135))

    # 5. Cap-on group: GPIO housings dragged through the camera retainer and clamp screw (section y = 18.8)
    off = np.array([0, 0, 40.0]) * 0.775
    gpio = [k for k in gp if k.startswith('head_pi_gpio_pin_')]
    G = m3d.Manifold.batch_boolean([to_manifold(*S(k)) for k in gpio], m3d.OpType.Add).translate(list(off))
    gv, gf = from_manifold(G)
    figure('05-cap-on-gpio-through-camera', 'Step cap-on: GPIO housings on the lowering cap pass through the camera retainer and clamp screw (y = 18.8)',
           'y', 18.8,
           [('GPIO receiving housings at 77.5% of approach', gv, gf, (0, 0, 0), {'color': '#ce93d8'}),
            ('camera_retainer', *S('camera_retainer'), (0, 0, 0), {'color': '#80cbc4'}),
            ('camera_clamp_screw_3', *S('camera_clamp_screw_3'), (0, 0, 0), {'color': '#b0bec5'}),
            ('face_panel', *S('face_panel'), (0, 0, 0), {'color': '#eeeeee'}),
            ('pi (final)', *S('pi'), (0, 0, 0), {'color': '#a5d6a7', 'alpha': 0.5})],
           overlaps=[('path overlap', G ^ to_manifold(*S('camera_retainer'))), (None, G ^ to_manifold(*S('camera_clamp_screw_3')))],
           xlim=(55, 92), ylim=(105, 158), legend_loc='lower left')

    # 6. Display-mesh artifact: decimated motor14 versus its source solid at the head_bottom (z = 105.1)
    dv, df = decode_guide_part(gp['motor14'])
    figure('06-motor14-display-decimation', 'Class d: decimated motor14 display mesh enters head_bottom; the source solid does not (section z = 105.1)',
           'z', 105.1,
           [('head_bottom', *S('head_bottom'), (0, 0, 0), {'color': '#fff176'}),
            ('motor14 source solid', *S('motor14'), (0, 0, 0), {'color': '#90caf9', 'alpha': 0.6}),
            ('motor14 viewer mesh (decimated)', dv, df, (0, 0, 0), {'color': 'none', 'ec': '#d81b60', 'lw': 1.2, 'alpha': 1})],
           overlaps=[('viewer mesh overlap', to_manifold(dv, df) ^ to_manifold(*S('head_bottom')))],
           xlim=(-25, 30), ylim=(-35, 5))

    # 7. Torso base sandwiched between hip-yaw motor and yaw bracket (why no straight approach exists), y = 17.5
    figure('07-torso-base-sandwich', 'Step torso-base: base and ring sit between ID10 above and its yaw bracket below (section y = 17.5)',
           'y', 17.5,
           [('torso_base', *S('torso_base'), (0, 0, 0), {'color': '#424242'}),
            ('ring10_torso', *S('ring10_torso'), (0, 0, 0), {'color': '#ffb74d'}),
            ('motor10 (hip yaw ID10)', *S('motor10'), (0, 0, 0), {'color': '#90caf9'}),
            ('yaw bracket', *S('yaw'), (0, 0, 0), {'color': '#a5d6a7'}),
            ('motor9', *S('motor9'), (0, 0, 0), {'color': '#ce93d8', 'alpha': 0.5})],
           xlim=(-25, 30), ylim=(-45, 28))


if __name__ == '__main__':
    main()
