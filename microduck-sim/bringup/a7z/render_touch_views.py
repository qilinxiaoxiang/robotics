"""Render the touch-pad views for A7Z-TOUCH.html from the guide's touch geometry.

Run with the CAD venv (trimesh + matplotlib):
    /tmp/microduck-cad-venv/bin/python render_touch_views.py

Inputs (robot frame, mm, x forward, y left, z up): ../../guide/print/world/head_cap.stl, speaker.stl,
speaker_retainer.stl, amplifier.stl, antenna.stl, touch_pad_*.stl, touch_xiao.stl, touch_xiao_tape.stl, and the nine
lead routes in ../../guide/extension-20261015-touch/touch_routes.json. The A7Z is left out: the pads go in before it.
Outputs: img/touch_below.png (cap upside down, looking into it) and img/touch_side.png (from the robot's right,
right half of the cap cut away, showing the XIAO on the inner left wall).
Same painter's renderer as render_cad_views.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.collections import PolyCollection

HERE = Path(__file__).resolve().parent
WORLD = HERE.parent.parent / 'guide' / 'print' / 'world'
TOUCH = HERE.parent.parent / 'guide' / 'extension-20261015-touch'
IMG = HERE / 'img'
IMG.mkdir(exist_ok=True)
load = lambda n: trimesh.load(WORLD / f'{n}.stl', force='mesh')

PADS = ['l1', 'r1', 'l2', 'r2', 'm']
COL = {'cap': '#f2f2ef', 'speaker': '#455a64', 'speaker_retainer': '#90a4ae', 'amplifier': '#7b5ea7',
       'antenna': '#ef8a17', 'touch_xiao': '#1565c0', 'touch_xiao_tape': '#fdd835', 'pad': '#c77b30'}
LEAD = '#8d4a12'
FONT = matplotlib.font_manager.FontProperties(fname='/System/Library/Fonts/Hiragino Sans GB.ttc')
ROUTES = json.loads((TOUCH / 'touch_routes.json').read_text())['routes']


def scene():
    s = {k: load(k) for k in ('head_cap', 'speaker', 'speaker_retainer', 'amplifier', 'antenna', 'touch_xiao',
                              'touch_xiao_tape')}
    s['cap'] = s.pop('head_cap')
    for p in PADS:
        s[f'pad_{p}'] = load(f'touch_pad_{p}')
    return s


def colour(key):
    return COL['pad'] if key.startswith('pad_') else COL[key]


def render(name, f, u, keep, xlim, ylim, labels, notes=(), px=1400):
    f = np.asarray(f, float); f /= np.linalg.norm(f)
    u = np.asarray(u, float); u -= (u @ f) * f; u /= np.linalg.norm(u)
    r = np.cross(f, u)
    L = -f + 0.35 * u; L /= np.linalg.norm(L)
    polys, cols, depth = [], [], []
    for key, m in scene().items():
        if key not in keep:
            continue
        tri = m.triangles
        mask = keep[key](tri.mean(axis=1)) if keep[key] is not None else np.ones(len(tri), bool)
        tri, nrm = tri[mask], m.face_normals[mask]
        base = np.array(matplotlib.colors.to_rgb(colour(key)))
        c = np.clip(base[None, :] * (0.42 + 0.58 * np.abs(nrm @ L))[:, None], 0, 1)
        polys.extend(np.stack([tri @ r, tri @ u], axis=-1))
        cols.extend(c)
        dz = (tri @ f).max(axis=1)
        if key.startswith('pad_') or key == 'antenna':
            dz = dz - 0.3                        # thin tape on the cap wall: draw it over the wall
        depth.extend(dz)
    order = np.argsort(-np.asarray(depth))
    polys = [polys[i] for i in order]
    cols = np.asarray(cols)[order]
    w_mm, h_mm = xlim[1] - xlim[0], ylim[1] - ylim[0]
    fig = plt.figure(figsize=(px / 100, px / 100 * h_mm / w_mm), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors=cols, linewidths=0.25, antialiased=True))
    for k, pts in ROUTES.items():                 # the five pad leads, drawn over everything; the four A7Z leads come
        if 'pad' not in k:                        # later (after the A7Z is on its rails) and are left out
            continue
        p = np.asarray(pts, float)
        ax.plot(p @ r, p @ u, color=LEAD, lw=3.0, solid_capstyle='round', zorder=4)
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect('equal'); ax.axis('off')
    fig.patch.set_facecolor('white')
    for text, at, fill in labels:                 # at: robot-frame point the label sits on
        t = np.asarray(at, float)
        ax.text(t @ r, t @ u, text, fontproperties=FONT, fontsize=px / 42, ha='center', va='center', color='white',
                fontweight='bold', zorder=9, bbox=dict(boxstyle='round,pad=0.3', fc=fill, ec='white', lw=2))
    for (fx, fy, text, ha) in notes:
        ax.text(xlim[0] + fx * w_mm, ylim[0] + fy * h_mm, text, fontproperties=FONT, fontsize=px / 52, ha=ha,
                va='center', color='#212121', zorder=9,
                bbox=dict(boxstyle='round,pad=0.35', fc='white', ec='#9e9e9e', lw=1.5))
    out = IMG / f'{name}.png'
    fig.savefig(out, dpi=100, facecolor='white')
    plt.close(fig)
    print(out, 'r =', r.round(3), 'u =', u.round(3))


def centre(key):
    return load(key).bounds.mean(axis=0)


ALL = {k: None for k in ('speaker', 'speaker_retainer', 'amplifier', 'antenna', 'touch_xiao', 'touch_xiao_tape',
                         *[f'pad_{p}' for p in PADS])}
NAMES = {'l1': 'L1', 'r1': 'R1', 'l2': 'L2', 'r2': 'R2', 'm': 'M'}
PAD_LABELS = [(NAMES[p], centre(f'touch_pad_{p}'), '#8d4a12') for p in PADS]

# View 1: cap upside down in your hands, looking into it. Image up = robot front (+X), image right = robot left (+Y).
render('touch_below', f=(0, 0, 1), u=(1, 0, 0), keep={**ALL, 'cap': lambda c: c[:, 2] > 118.0},
       xlim=(-46, 46), ylim=(-36, 96),
       labels=PAD_LABELS + [('XIAO', centre('touch_xiao'), '#1565c0'), ('喇叭', centre('speaker'), '#455a64'),
                            ('功放', centre('amplifier'), '#7b5ea7'), ('天线', centre('antenna'), '#ef8a17')],
       notes=((0.5, 0.975, '↑ 脸（机器人前方）', 'center'), (0.985, 0.5, '机器人左边 →', 'right'),
              (0.015, 0.5, '← 机器人右边', 'left'), (0.5, 0.025, '↓ 后脑勺', 'center')))

# View 2: from the robot's right (-Y), the right half of the cap cut away: the XIAO on the inner left wall.
render('touch_side', f=(0, 1, 0), u=(0, 0, 1), keep={**ALL, 'cap': lambda c: c[:, 1] > 0.0},
       xlim=(-40, 96), ylim=(104, 162),
       labels=[(NAMES[p], centre(f'touch_pad_{p}'), '#8d4a12') for p in ('l1', 'l2', 'm')]
       + [('XIAO', centre('touch_xiao'), '#1565c0')],
       notes=((0.985, 0.06, '脸（机器人前方）→', 'right'), (0.015, 0.06, '← 后脑勺', 'left')))
