"""Render the antenna placement views for A7Z-ANTENNA.html from the CAD-checked A7Z head geometry.

Run with the CAD venv (trimesh + matplotlib):
    /tmp/microduck-cad-venv/bin/python render_cad_views.py

Inputs (robot frame, mm, x forward, y left, z up): ../../guide/print/a7z-head/head_cap_a7z-world.stl,
clip_cap_a7z-world.stl and a7z_parts/*.stl, plus the board frame w(s, d, h) from build_a7z_head.py for the 2 x 20
header (not exported as a part, drawn here as an illustration: 2.5 mm base, pins 8.5 mm above the PCB).
Outputs: img/cad_below.png, img/cad_side.png, img/cad_ipex.png with numbered markers drawn in:
1 antenna, 2 antenna cable end, 3 IPEX socket (plug on it), 4 header pin 1.
Simple orthographic painter's renderer: every triangle is projected, sorted far to near and filled with flat shading.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.collections import PolyCollection

HERE = Path(__file__).resolve().parent
CAD = HERE.parent.parent / 'guide' / 'print' / 'a7z-head'
IMG = HERE / 'img'
IMG.mkdir(exist_ok=True)
sys.path.insert(0, str(CAD))
import build_a7z_head as B  # noqa: E402  (module-level only defines the board frame; main() is guarded)

P = CAD / 'a7z_parts'
load = lambda p: trimesh.load(p, force='mesh')

COL = {
    'cap': '#f2f2ef', 'clip': '#9ecae1', 'pcb': '#2e7d32', 'comp': '#5f6b73', 'ant': '#ef8a17', 'coax': '#263238',
    'plug': '#d4a017', 'sock': '#b0bec5', 'hbase': '#202020', 'pin': '#c9a227', 'pin1': '#ffd600', 'pin2': '#e53935',
}


def header():
    """2 x 20 header on the A7Z, board frame: pin 1 at s = 8.37, odd pins on the inner row (d = 4.77), even on the
    edge row (d = 2.23), pitch 2.54 along s."""
    base = B.obox(8.37 - 1.27, 8.37 + 19 * 2.54 + 1.27, 2.23 - 1.27, 4.77 + 1.27, B.T, B.T + 2.5)
    pins, p1, p2 = [], None, None
    for k in range(20):
        for d, odd in ((4.77, True), (2.23, False)):
            s = 8.37 + k * 2.54
            m = B.obox(s - 0.32, s + 0.32, d - 0.32, d + 0.32, B.T, B.T + 8.5)
            n = 2 * k + (1 if odd else 2)
            if n == 1:
                p1 = m
            elif n == 2:
                p2 = m
            else:
                pins.append(m)
    return base, trimesh.util.concatenate(pins), p1, p2


def scene():
    cap = load(CAD / 'head_cap_a7z-world.stl')
    clip = load(CAD / 'clip_cap_a7z-world.stl')
    comps = trimesh.util.concatenate([load(P / f'{k}.stl') for k in (
        'wifi_module_fcu760k', 'soc_a733', 'ram', 'pmic_area', 'micro_hdmi', 'usb_c_otg_dp', 'usb_c_power',
        'fan_connector', 'csi_connector', 'microsd_socket', 'microsd_card', 'pcie_fpc', 'uboot_button', 'underside_smd')])
    base, pins, p1, p2 = header()
    return {
        'cap': cap, 'clip': clip, 'pcb': load(P / 'a7z_pcb.stl'), 'comp': comps,
        'ant': load(P / 'antenna_ac019.stl'), 'coax': load(P / 'antenna_coax.stl'),
        'plug': load(P / 'ipex_plug.stl'), 'sock': load(P / 'ipex_socket.stl'),
        'hbase': base, 'pin': pins, 'pin1': p1, 'pin2': p2,
    }


# Marker targets (robot frame)
PIN1_TIP = B.w(8.37, 4.77, B.T + 8.5)
PIN1_MID = B.w(8.37, 4.77, B.T + 5.0)
TARGET = {
    1: np.array([70.0, -4.0, 152.6]),          # antenna sheet, middle of its length
    2: np.array([70.4, 19.6, 151.6]),          # antenna cable end (+Y), where the coax joins
    3: B.w(2.0, 14.9, B.T + 1.2),              # IPEX socket under the plug
    4: PIN1_MID,                               # header pin 1
}


FONT = matplotlib.font_manager.FontProperties(fname='/System/Library/Fonts/Hiragino Sans GB.ttc')


def render(name, f, u, keep, xlim, ylim, marks, px=1400, light=None, labels=()):
    """f: view direction (camera looks along f); u: image up. keep: dict part -> face mask function or None."""
    f = np.asarray(f, float); f /= np.linalg.norm(f)
    u = np.asarray(u, float); u -= (u @ f) * f; u /= np.linalg.norm(u)
    r = np.cross(f, u)
    L = np.asarray(light if light is not None else -f + 0.35 * u, float); L /= np.linalg.norm(L)
    polys, cols, depth = [], [], []
    S = scene()
    for key, m in S.items():
        if key not in keep:
            continue
        tri = m.triangles
        cen = tri.mean(axis=1)
        mask = keep[key](cen) if keep[key] is not None else np.ones(len(tri), bool)
        tri = tri[mask]
        nrm = m.face_normals[mask]
        base = np.array(matplotlib.colors.to_rgb(COL[key]))
        lam = np.abs(nrm @ L)
        shade = 0.42 + 0.58 * lam
        c = np.clip(base[None, :] * shade[:, None], 0, 1)
        P2 = np.stack([tri @ r, tri @ u], axis=-1)
        polys.extend(P2)
        cols.extend(c)
        dz = (tri @ f).max(axis=1)
        if key in ('ant', 'coax', 'plug', 'pin1'):
            dz = dz - 0.15                      # thin parts lying on a surface: draw them over it
        depth.extend(dz)
    order = np.argsort(-np.asarray(depth))
    polys = [polys[i] for i in order]
    cols = np.asarray(cols)[order]
    w_mm, h_mm = xlim[1] - xlim[0], ylim[1] - ylim[0]
    fig = plt.figure(figsize=(px / 100, px / 100 * h_mm / w_mm), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors=cols, linewidths=0.25, antialiased=True))
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect('equal'); ax.axis('off')
    fig.patch.set_facecolor('white')
    rad = 0.032 * w_mm
    for n, m in marks.items():
        dx, dy = m[:2]
        t = np.asarray(m[2], float) if len(m) > 2 else TARGET[n]
        tx, ty = t @ r, t @ u
        cx, cy = tx + dx, ty + dy
        ax.plot([tx, cx], [ty, cy], color='#0d47a1', lw=3.2, solid_capstyle='round', zorder=5)
        ax.add_patch(plt.Circle((tx, ty), rad * 0.22, color='#0d47a1', zorder=6))
        ax.add_patch(plt.Circle((cx, cy), rad, color='#1565c0', ec='white', lw=3, zorder=7))
        ax.text(cx, cy, str(n), color='white', ha='center', va='center', fontsize=px / 40, fontweight='bold', zorder=8)
    for (fx, fy, text, ha) in labels:               # fx, fy: fractions of the image
        ax.text(xlim[0] + fx * w_mm, ylim[0] + fy * h_mm, text, fontproperties=FONT, fontsize=px / 50, ha=ha,
                va='center', color='#212121', zorder=9,
                bbox=dict(boxstyle='round,pad=0.35', fc='white', ec='#9e9e9e', lw=1.5))
    out = IMG / f'{name}.png'
    fig.savefig(out, dpi=100, facecolor='white')
    plt.close(fig)
    print(out, 'r =', r.round(3), 'u =', u.round(3))


ALL = {k: None for k in ('clip', 'pcb', 'comp', 'ant', 'coax', 'plug', 'sock', 'hbase', 'pin', 'pin1', 'pin2')}

# View 1: the cap upside down in your hands, looking into it (camera below, looking up). Image up = robot front (+X),
# image right = robot left (+Y).
render('cad_below', f=(0, 0, 1), u=(1, 0, 0),
       keep={**ALL, 'cap': lambda c: c[:, 2] > 118.0},
       xlim=(-46, 46), ylim=(44, 96),
       marks={1: (-10, 12), 2: (12, 12), 3: (-9, -8)},
       labels=((0.5, 0.95, '↑ 脸（机器人前方）', 'center'), (0.985, 0.62, '机器人左边 →', 'right'),
               (0.015, 0.62, '← 机器人右边', 'left')))

# View 2: from the robot's left (+Y), the left half of the cap cut away. Image left = robot front (+X), up = +Z.
render('cad_side', f=(0, -1, 0), u=(0, 0, 1),
       keep={**ALL, 'cap': lambda c: c[:, 1] < 0.0},
       xlim=(-98, -36), ylim=(104, 162),
       marks={1: (-12, 4, (74.6, -4.0, 153.4)), 2: (9, 7), 3: (-12, -4), 4: (-10, -8)},
       labels=((0.03, 0.06, '← 脸（机器人前方）', 'left'), (0.97, 0.06, '后脑勺 →', 'right')))

# View 3: close-up of the IPEX end, from in front, left and a little below; front of the cap and its left side cut away.
f3 = np.array([-1.0, -0.75, 0.35])
render('cad_ipex', f=f3, u=(0, 0, 1),
       keep={**ALL, 'cap': lambda c: (c[:, 0] < 50.0) | ((c[:, 2] > 147.0) & (c[:, 1] < 26.0))},
       xlim=(-50, 2), ylim=(117, 171), px=1200,
       marks={1: (-6, 5, (70.0, 5.0, 152.6)), 2: (6, 5), 3: (7, -3), 4: (6, -6)},
       labels=((0.03, 0.05, '从前面偏左、稍低处看', 'left'),))
