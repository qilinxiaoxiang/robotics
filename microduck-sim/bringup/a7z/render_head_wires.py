"""To-scale picture of the head wire run for A7Z-PINS.html: robot's left side view and top view of the head, neck and V2 saddle
at HOME (guide-data.json part meshes), with the wire segments drawn and measured: component -> breadboard on the camera
back and breadboard -> gather point (right-angle runs, as head_wire_lengths.py measures them), gather point -> head exit, exit -> front wall top (straight, HOME and the trained-range worst pose from
head-sweep-v2.json, the pickup bend's farthest pose), wall top -> pin 12. Writes img/head_wires.png.   ~/.venvs/microduck-cad/bin/python render_head_wires.py"""
import base64, json, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
G = json.loads((HERE.parents[1] / 'guide' / 'data' / 'guide-data.json').read_text())
SW = json.loads((HERE / 'head-sweep-v2.json').read_text())
PINS = json.loads((HERE.parents[1] / 'guide' / 'print' / 'a7z-saddle' / 'build' / 'pins.json').read_text())['pinTop']
PARTS = {p['key']: p for p in G['parts']}
CAB = {c['id']: c for c in G['cables']}
GP, EXIT, WALL = [11.5, 19.5, 132.0], SW['exit'], SW['splice']
WORST = SW['pickup']['maxStraightExitPt']
PLRC = {'font.family': ['PingFang SC', 'Heiti SC', 'Arial Unicode MS'], 'font.size': 9}
plt.rcParams.update(PLRC)

LAYERS = [  # key, fill, alpha (drawn in this order)
    ('saddle_body', '#e8c9b8', 0.55), ('saddle_lid', '#e8c9b8', 0.55), ('torso_base', '#cccccc', 0.5),
    ('motor12', '#9a9a9a', 0.8), ('motor11', '#9a9a9a', 0.8), ('neck_pitch', '#b0b0b0', 0.8), ('motor13', '#9a9a9a', 0.8),
    ('motor14', '#9a9a9a', 0.6), ('motor15', '#9a9a9a', 0.6), ('head_yaw_link', '#b0b0b0', 0.6),
    ('head_bottom', '#eadfc0', 0.35), ('head_cap', '#f2f2f2', 0.35),
    ('sd_a7z_pcb', '#2e7d32', 0.9), ('sd_heatsink_6530b', '#888888', 0.7), ('sd_dupont_housings', '#222222', 0.9), ('camera_u20cam', '#2e7d32', 0.9),
    ('amplifier', '#1565c0', 0.9), ('mic_left', '#333333', 0.9), ('touch_xiao', '#333333', 0.9),
]
PX = 4.0  # raster px per mm


def mesh(key):
    p = PARTS[key]
    v = np.frombuffer(base64.b64decode(p['positionB64']), dtype=np.float32).reshape(-1, 3)
    i = np.frombuffer(base64.b64decode(p['indexB64']), dtype=np.uint32).reshape(-1, 3)
    return v, i


def length(p):
    return sum(math.dist(p[k], p[k + 1]) for k in range(len(p) - 1))


def upto(cid, pt):
    p = CAB[cid]['path']
    k = min(range(len(p)), key=lambda j: math.dist(p[j], pt))
    return p[:k + 1]


def tail(pin):
    x, y, z = PINS[str(pin)]
    return [WALL, [WALL[0], y, WALL[2]], [x, y, 65.5], [x, y, z]]


HW = json.loads((HERE / 'head-wire-lengths.json').read_text())
BT = HW['breadboard']['plugTail']   # where the wires leave the plugs behind the breadboard on the camera back
BOX = HW['breadboard']['box']      # the breadboard itself, [[x, y, z] min, max]


def square(a, b):
    """Wall-following right-angle run a -> b (x, then y, then z), the way head_wire_lengths.py measures it."""
    return [a, [b[0], a[1], a[2]], [b[0], b[1], a[2]], b]


SEG = [  # label, points, colour, style
    ('功放 BCLK → 面包板', square(CAB['amp-bclk']['path'][0], BT), '#ef6c00', '-'),
    ('右耳 → 面包板', square(CAB['mic-r']['path'][0], BT), '#c2185b', '-'),
    ('触摸板 3V3 → 面包板', square(CAB['touch-pin17']['path'][0], BT), '#d32f2f', '-'),
    ('面包板 → 集线点', square(BT, GP), '#6d4c41', '-'),
    ('集线点 → 出线口', [GP, [10.0, 18.5, 124.0], [10.0, 18.5, 110.0], EXIT], '#000000', '-'),
    ('出线口 → 前墙顶（头朝前）', [EXIT, WALL], '#1565c0', '-'),
    ('前墙顶 → 12 号针', tail(12), '#1565c0', '-'),
]


def draw(ax, axes, depth, sign, title, xlim, ylim):
    x0, x1 = xlim; y0, y1 = ylim
    W, H = int((x1 - x0) * PX), int((y1 - y0) * PX)
    for key, col, al in LAYERS:
        if key not in PARTS:
            continue
        v, tri = mesh(key)
        uv = np.stack([(v[:, axes[0]] - x0) * PX, (y1 - v[:, axes[1]]) * PX], 1)
        im = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(im)
        for t in tri:
            dr.polygon([tuple(uv[j]) for j in t], fill=255)
        m = np.asarray(im) > 0
        rgba = np.zeros((H, W, 4)); rgba[m] = list(matplotlib.colors.to_rgb(col)) + [al]
        ax.imshow(rgba, extent=(x0, x1, y0, y1), interpolation='nearest', zorder=1)
        ax.contour(np.linspace(x0, x1, W), np.linspace(y1, y0, H), m.astype(float), levels=[0.5], colors=['#777777'], linewidths=0.4, zorder=2)
    for lab, pts, col, st in SEG:
        a = np.array(pts)
        ax.plot(a[:, axes[0]], a[:, axes[1]], st, color=col, lw=2.2, zorder=5, solid_capstyle='round')
    lo, hi = BOX
    ax.add_patch(matplotlib.patches.Rectangle((lo[axes[0]], lo[axes[1]]), hi[axes[0]] - lo[axes[0]], hi[axes[1]] - lo[axes[1]],
                                              fc='#ffb300', ec='black', lw=1, zorder=4))
    w = np.array([WORST, WALL])
    ax.plot(w[:, axes[0]], w[:, axes[1]], '--', color='#1565c0', lw=1.6, zorder=5)
    for pt, lab in ((BT, '面包板插头尾'), (GP, '集线点'), (EXIT, '出线口'), (WALL, '前墙顶'), (WORST, '低头叼东西最远时\n的出线口')):
        ax.plot(pt[axes[0]], pt[axes[1]], 'o', color='white', mec='black', ms=6, zorder=6)
        ax.annotate(lab, (pt[axes[0]], pt[axes[1]]), xytext=(6, 4), textcoords='offset points', fontsize=8, zorder=7,
                    bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.85))
    ax.plot([x0 + 6, x0 + 56], [y0 + 6, y0 + 6], color='black', lw=3); ax.text(x0 + 31, y0 + 9, '50 mm', ha='center', fontsize=8)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_title(title, fontsize=10)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)


fig, axs = plt.subplots(1, 2, figsize=(13, 6.2), gridspec_kw=dict(width_ratios=[1.25, 1]))
draw(axs[0], (0, 2), 1, 1, '从机器人左边看（头朝右）', (-50, 120), (20, 165))
draw(axs[1], (0, 1), 2, 1, '从上往下看（头朝右，机器人左边在上）', (-50, 120), (-50, 50))
lines = [f'{lab}：{length(p):.0f} mm' for lab, p, *_ in SEG] + [f'出线口 → 前墙顶（低头叼东西最远）：{SW["pickup"]["maxStraightMm"]:.0f} mm']
fig.text(0.01, 0.01, '   '.join(lines[:4]) + '\n' + '   '.join(lines[4:]), fontsize=8.5, va='bottom')
fig.tight_layout(rect=(0, 0.07, 1, 0.96))
out = HERE / 'img' / 'head_wires.png'
fig.savefig(out, dpi=150); print(out); print('\n'.join(lines))
