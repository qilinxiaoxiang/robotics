"""Why the gather-point-to-pin piece is as long as it is: the robot's left side view of the head, neck and V2 saddle at four
head poses (head-pose-frames.json: HOME, head yaw 80, the pickup bend's lowest pose and its farthest pose), with the pin 12 wire drawn as gather point -> exit (inside the head) -> straight to the
front wall top -> pin, and its length. Writes img/head_poses.png.   ~/.venvs/microduck-cad/bin/python render_head_poses.py"""
import json, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw
import render_head_wires as R

HERE = Path(__file__).resolve().parent
PF = json.loads((HERE / 'head-pose-frames.json').read_text())
BODY = {'motor11': 'neck', 'neck_link_a': 'neck', 'neck_link_b': 'neck', 'neck_pitch': 'neck_pitch', 'motor13': 'neck_pitch',
        'neck_pitch_ring': 'neck_pitch', 'head_yaw_link': 'yaw_roll_motion', 'motor14': 'yaw_roll_motion'}
HEAD = ('head_bottom', 'head_cap', 'motor15', 'amplifier', 'mic_left', 'touch_xiao', 'face_panel', 'eye_trim', 'jaw_support', 'jaw_frame')
LAYERS = [('saddle_body', '#e8c9b8', 0.6), ('torso_base', '#cccccc', 0.5), ('motor12', '#9a9a9a', 0.85),
          ('motor11', '#9a9a9a', 0.85), ('neck_link_a', '#b0b0b0', 0.85), ('neck_link_b', '#b0b0b0', 0.85),
          ('neck_pitch', '#b0b0b0', 0.85), ('motor13', '#9a9a9a', 0.85), ('head_yaw_link', '#b0b0b0', 0.7), ('motor14', '#9a9a9a', 0.7),
          ('head_bottom', '#eadfc0', 0.45), ('head_cap', '#f2f2f2', 0.45), ('motor15', '#9a9a9a', 0.6),
          ('sd_a7z_pcb', '#2e7d32', 0.9), ('sd_dupont_housings', '#222222', 0.9), ('amplifier', '#1565c0', 0.9), ('mic_left', '#333333', 0.9)]
PX, XL, ZL = 3.0, (-55, 185), (-30, 175)
PIN = 12
TITLES = {'home': '头朝前站着（平时）', 'yaw80': '头转 80°（走路时头能转到的）',
          'gp_low': '低头叼东西：最低的时候（脖子 -79°，头 -17°）', 'gp_max': '低头叼东西：起身时脖子到 -90° 限位（最远）'}


def carry(T, pts):
    T = np.array(T); p = np.c_[np.asarray(pts, float), np.ones(len(pts))]
    return (p @ T.T)[:, :3]


def panel(ax, key):
    P = PF['poses'][key]
    W, H = int((XL[1] - XL[0]) * PX), int((ZL[1] - ZL[0]) * PX)
    for k, col, al in LAYERS:
        if k not in R.PARTS:
            continue
        v, tri = R.mesh(k)
        b = 'jaw_soft' if k in HEAD else BODY.get(k)
        if b:
            v = carry(P['carry'][b], v)
        uv = np.stack([(v[:, 0] - XL[0]) * PX, (ZL[1] - v[:, 2]) * PX], 1)
        im = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(im)
        for t in tri:
            dr.polygon([tuple(uv[j]) for j in t], fill=255)
        msk = np.asarray(im) > 0
        rgba = np.zeros((H, W, 4)); rgba[msk] = list(matplotlib.colors.to_rgb(col)) + [al]
        ax.imshow(rgba, extent=(*XL, *ZL), interpolation='nearest', zorder=1)
        ax.contour(np.linspace(*XL, W), np.linspace(ZL[1], ZL[0], H), msk.astype(float), levels=[0.5], colors=['#777777'], linewidths=0.4, zorder=2)
    inside = carry(P['carry']['jaw_soft'], [R.GP, [10.0, 18.5, 124.0], [10.0, 18.5, 110.0], R.EXIT])
    tl = np.array(R.tail(PIN))
    a_in, a_out, a_tail = R.length(inside.tolist()), P['straightMm'], R.length(tl.tolist())
    ax.plot(inside[:, 0], inside[:, 2], color='black', lw=2.4, zorder=5)
    ax.plot([inside[-1, 0], tl[0, 0]], [inside[-1, 2], tl[0, 2]], color='#d32f2f', lw=2.6, zorder=5)
    ax.plot(tl[:, 0], tl[:, 2], color='#1565c0', lw=2.4, zorder=5)
    for pt, lab in ((inside[0], '集线点'), (inside[-1], '出线口'), (tl[0], '前墙顶')):
        ax.plot(pt[0], pt[2], 'o', color='white', mec='black', ms=5, zorder=6)
        ax.annotate(lab, (pt[0], pt[2]), xytext=(5, 3), textcoords='offset points', fontsize=8, zorder=7,
                    bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.85))
    tot = a_in + a_out + a_tail
    ax.text(XL[0] + 3, ZL[1] - 4, f'集线点→出线口 {a_in:.0f}（黑）\n出线口→前墙顶 {a_out:.0f}（红）\n前墙顶→12 号针 {a_tail:.0f}（蓝）\n合计 {tot:.0f} mm',
            va='top', fontsize=8.5, bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='#bbbbbb'))
    ax.plot([XL[1] - 58, XL[1] - 8], [ZL[0] + 5, ZL[0] + 5], color='black', lw=3); ax.text(XL[1] - 33, ZL[0] + 8, '50 mm', ha='center', fontsize=8)
    ax.set_xlim(*XL); ax.set_ylim(*ZL); ax.set_aspect('equal'); ax.set_title(TITLES[key], fontsize=10)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)


fig, axs = plt.subplots(2, 2, figsize=(12, 11.5))
for ax, key in zip(axs.ravel(), ('home', 'yaw80', 'gp_low', 'gp_max')):
    panel(ax, key)
fig.suptitle('从机器人左边看（头朝右，按躯干摆正画），12 号针那根线：集线点到排针', fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.97))
out = HERE / 'img' / 'head_poses.png'; fig.savefig(out, dpi=140); print(out)
