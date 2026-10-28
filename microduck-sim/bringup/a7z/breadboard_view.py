# Draw img/breadboard_camera_back.png: the mini breadboard on the camera back, from the robot's left and from behind (guide CAD).
# Run with the CAD venv:  ~/.venvs/microduck-cad/bin/python breadboard_view.py
import base64, json, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
plt.rcParams.update({'font.family': ['PingFang SC', 'Heiti SC', 'Arial Unicode MS'], 'font.size': 10})
G = json.load(open('/Users/xiangzheng/code/robotics/microduck-sim/guide/data/guide-data.json'))
P = {p['key']: p for p in G['parts']}
def vt(k):
    p = P[k]
    v = np.frombuffer(base64.b64decode(p['positionB64']), dtype=np.float32).reshape(-1, 3)
    i = np.frombuffer(base64.b64decode(p['indexB64']), dtype=np.uint32).reshape(-1, 3)
    return v, i
LAY = [('head_bottom', '#eadfc0', .35), ('head_cap', '#f2f2f2', .35), ('jaw_support', '#9e9e9e', .7), ('motor15', '#7a7a7a', .8),
       ('face_panel', '#ffffff', .6), ('camera_u20cam', '#2e7d32', .9), ('camera_cable_stub', '#37474f', .9),
       ('touch_xiao', '#333333', .9), ('amplifier', '#1565c0', .9), ('speaker', '#555555', .8), ('mic_left', '#c2185b', .9)]
fig, axs = plt.subplots(1, 2, figsize=(13, 6.2), gridspec_kw={'width_ratios': [1.25, 1]})
back = 63.4; bx0 = back - 12.3
for ax, (a, b), title in ((axs[0], (0, 2), '从机器人左边看（头朝右）'), (axs[1], (1, 2), '从后往前看摄像头背面（机器人左边在图左）')):
    for k, c, al in LAY:
        if k not in P: continue
        v, i = vt(k)
        x = v[:, a] if a == 0 else -v[:, a]
        if a == 1: x = -x * -1  # robot +y to the left: plot -y? keep +y on the left by negating
        X = v[:, a] if a == 0 else -v[:, 1]
        Y = v[:, b]
        if a == 1:
            m = v[:, 0] > 40   # only parts near the camera for the rear view
            keep = m[i].all(1)
            i = i[keep]
        ax.tripcolor(X, Y, i, np.zeros(len(i)), cmap=matplotlib.colors.ListedColormap([c]), alpha=al, edgecolors='none')
    ax.set_title(title); ax.set_aspect('equal')
# side view: board (landscape) and plug housings of all 5 rows
s = axs[0]
s.add_patch(Rectangle((bx0, 131), 12.3, 15, fc='#ffb300', ec='k', lw=1.2, alpha=.95))
s.add_patch(Rectangle((bx0 - 16, 132.15), 16, 12.7, fc='#111111', ec='k', lw=1, alpha=.8))
s.annotate('迷你面包板横着贴\n20 宽 × 15 高 × 12 厚', (bx0 + 6, 131), (70, 98), arrowprops=dict(arrowstyle='->'), fontsize=9)
s.annotate('杜邦公头往后插（5 排都能插）\n离下巴支架、XIAO 至少 1.8 mm', (bx0 - 8, 144.9), (5, 160), arrowprops=dict(arrowstyle='->'), fontsize=9)
s.set_xlim(-5, 100); s.set_ylim(95, 172); s.plot([10, 30], [100, 100], 'k', lw=2); s.text(20, 101.5, '20 mm', ha='center', fontsize=8)
r = axs[1]
r.add_patch(Rectangle((2.0, 131), 20, 15, fc='#ffb300', ec='k', lw=1.2, alpha=.9))
for i in range(5):
    for j in range(5):
        zz, yy = 138.5 + (2 - i) * 2.54, 12.0 + (j - 2) * 2.54
        r.add_patch(Circle((yy, zz), .55, fc='k'))
r.add_patch(Rectangle((-10.61, 142.0), 8.5, 3.5, fc='#eeeeee', ec='k', lw=1))
r.text(-6.4, 148.5, '摄像头插头', ha='center', fontsize=9)
r.text(12, 127.5, '面包板（插头右边，横放）', ha='center', fontsize=9)
r.text(12, 125, '25 个孔都能插', ha='center', fontsize=8)
r.set_xlim(-24, 28); r.set_ylim(110, 152)
for ax in axs: ax.set_xticks([]); ax.set_yticks([])
plt.tight_layout()
out = '/Users/xiangzheng/code/robotics/microduck-sim/bringup/a7z/img/breadboard_camera_back.png'
plt.savefig(out, dpi=150); print(out)
