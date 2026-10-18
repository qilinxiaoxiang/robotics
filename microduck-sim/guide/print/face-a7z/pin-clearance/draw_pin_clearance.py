"""Pin clearance figure: how much room each A7Z header pin has in front of its Dupont plug, against the Radxa
Camera 13M 214 in the A7Z face. Side section (one pin column) and front view (all 40 pins).
Robot frame mm: x forward, y left, z up. Run with the CAD venv python."""
import sys, numpy as np, trimesh, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon, FancyArrowPatch
from pathlib import Path
HERE = Path(__file__).resolve().parent
GUIDE = HERE.parents[2]
sys.path.insert(0, str(GUIDE / 'content' / 'interference-audit'))
import ia_lib as L
plt.rcParams['font.family'] = ['Hiragino Sans GB', 'Heiti TC']

def M(k):
    v, f = L.load_solid(k); return trimesh.Trimesh(v, f, process=False)

AX = np.array([0.984808, 0.0, -0.173648])            # header pin axis
PERP = np.array([0.173648, 0.0, 0.984808])
PLUG = 14.25                                          # Dupont housing length from the header base top
CAM_PCB = dict(x=(76.2, 77.8), y=(-16.09, 15.91), z=(115.11, 147.11))
SCREWS = [(-14.09, 117.11), (13.91, 117.11), (-14.09, 145.11), (13.91, 145.11)]
HEAD_R, HEAD_X = 1.9, (74.6, 76.2)
COMP = dict(y=(2.4, 15.2), z=(134.3, 147.11))         # back components, Radxa photo (camera-13m-214-view.png)
base = M('head_pi_zero_w_header_base')
bt = (base.vertices @ AX).max()
pins = {n: M(f'head_pi_zero_w_header_pin_{n:02d}') for n in range(1, 41)}
pc = {n: p.vertices.mean(0) for n, p in pins.items()}

def plug_end(n):
    c = pc[n]; o = c + (bt - c @ AX) * AX
    return o, o + PLUG * AX

def status(n):
    o, e = plug_end(n)
    top = e + 1.27 * PERP
    y = e[1]
    xface = (e + 1.27 * PERP)[0]
    if top[2] <= CAM_PCB['z'][0] or not (CAM_PCB['y'][0] - 0.6 < y < CAM_PCB['y'][1] + 0.6):
        return 'open', None
    for sy, sz in SCREWS[:2]:
        if abs(y - sy) < HEAD_R + 0.6:
            return 'screw', HEAD_X[0] - xface
    return 'tight', CAM_PCB['x'][0] - xface

fig = plt.figure(figsize=(15, 8.6), facecolor='white')
# ---------- left: side section through the pin 17/18 column ----------
ax1 = fig.add_axes([0.04, 0.08, 0.44, 0.80])
n_odd, n_even = 17, 18
ysec = pc[n_even][1]
face = M('face_panel')
for mesh, col, lab in ((base, '#333333', None), (face, '#d9d9d9', None)):
    s = mesh.section(plane_origin=[0, ysec, 0], plane_normal=[0, 1, 0])
    if s is not None:
        for poly in s.discrete:
            ax1.fill(poly[:, 0], poly[:, 2], color=col, ec='#555', lw=0.6)
for n in (n_odd, n_even):
    s = pins[n].section(plane_origin=[0, pc[n][1], 0], plane_normal=[0, 1, 0])
    if s is not None:
        for poly in s.discrete:
            ax1.fill(poly[:, 0], poly[:, 2], color='#c9a227', ec='#8a6d00', lw=0.5)
    o, e = plug_end(n)
    corners = [o - 1.25 * PERP, o + 1.25 * PERP, e + 1.25 * PERP, e - 1.25 * PERP]
    ax1.add_patch(Polygon([[c[0], c[2]] for c in corners], closed=True, fc='#4a7fd4' if n % 2 == 0 else '#8fb3ea',
                          ec='#1d4ea0', lw=1, alpha=0.85))
x0, x1 = CAM_PCB['x']; z0, z1 = CAM_PCB['z']
ax1.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fc='#1b6b3a', ec='k', lw=1))
ax1.add_patch(Rectangle((x1, 128.0), 6.38, 6.2, fc='#555', ec='k', lw=0.8))   # lens holder (approx band)
ax1.add_patch(Rectangle((x0 - 1.5, z0), 1.5, z1 - z0, fc='none', ec='#d62728', lw=1.2, ls='--', hatch='///'))
o, e = plug_end(n_even)
tip = e + 1.27 * PERP
ax1.add_patch(FancyArrowPatch((tip[0], tip[2] + 0.6), (x0, tip[2] + 0.6), arrowstyle='<->', mutation_scale=10, color='#d62728', lw=1.5))
ax1.annotate(f'剩 {x0 - tip[0]:.1f} mm\n给线弯 90°', (x0 - 1.0, tip[2] + 1.0), xytext=(64.5, 127), fontsize=12, color='#d62728',
             arrowprops=dict(arrowstyle='->', color='#d62728'))
ax1.annotate('杜邦插头 14.25 mm\n(深蓝=外排 18 号, 浅蓝=里排 17 号)', (66, 118.3), xytext=(55, 106.5), fontsize=11, color='#1d4ea0',
             arrowprops=dict(arrowstyle='->', color='#1d4ea0'))
ax1.annotate('A7Z 排针座', (58.5, 116), xytext=(50, 124), fontsize=11, arrowprops=dict(arrowstyle='->'))
ax1.annotate('摄像头电路板背面\n(这一段是光板)', (76.6, 120), xytext=(79.5, 108.8), fontsize=11, color='#1b6b3a',
             arrowprops=dict(arrowstyle='->', color='#1b6b3a'))
ax1.annotate('我之前错加的 1.5 mm\n"背面元件层"(红虚线)', (75.0, 140), xytext=(60.5, 143), fontsize=11, color='#d62728',
             arrowprops=dict(arrowstyle='->', color='#d62728'))
ax1.annotate('前脸', (80.5, 150), fontsize=11)
ax1.annotate('镜头', (80.2, 135.2), fontsize=10)
ax1.axhline(z0, color='#1b6b3a', lw=0.6, ls=':')
ax1.text(85.6, z0 - 1.6, '摄像头下沿 z 115.1', fontsize=9, color='#1b6b3a', ha='right')
ax1.set_xlim(48, 87); ax1.set_ylim(104, 153); ax1.set_aspect('equal')
ax1.set_xlabel('x (mm)  向前 →'); ax1.set_ylabel('z (mm)  向上 ↑')
ax1.set_title(f'侧面剖视 (沿 17/18 号针那一列切开, y = {ysec:.2f})', fontsize=13)

# ---------- right: front view of all 40 pins ----------
ax2 = fig.add_axes([0.53, 0.08, 0.45, 0.80])
y0, y1 = CAM_PCB['y']
ax2.add_patch(Rectangle((y0, z0), y1 - y0, z1 - z0, fc='#e3f1e7', ec='#1b6b3a', lw=1.5))
ax2.add_patch(Rectangle((COMP['y'][0], COMP['z'][0]), np.diff(COMP['y'])[0], np.diff(COMP['z'])[0], fc='none', ec='#999', hatch='xx', lw=0.8))
ax2.text(np.mean(COMP['y']), np.mean(COMP['z']), '背面元件\n(照片)', ha='center', va='center', fontsize=9, color='#666')
ax2.add_patch(Circle((-0.09, 131.11), 4.25, fc='#555'))
ax2.text(-0.09, 131.11, '镜头', color='white', ha='center', va='center', fontsize=9)
for sy, sz in SCREWS:
    ax2.add_patch(Circle((sy, sz), HEAD_R, fc='#888', ec='k'))
ax2.text(-14.09, 120.2, '下面两颗\n螺丝头', ha='center', fontsize=9)
cols = {'open': '#2ca02c', 'tight': '#ff9f1c', 'screw': '#d62728'}
for n in range(1, 41):
    o, e = plug_end(n)
    st, g = status(n)
    ax2.add_patch(Rectangle((e[1] - 1.2, e[2] - 1.2), 2.4, 2.4, fc=cols[st], ec='k', lw=0.5, alpha=0.9))
    ax2.text(e[1], e[2], str(n), ha='center', va='center', fontsize=7.5, color='white', fontweight='bold')
    if st != 'open' and n in (12, 18, 10, 11):
        pass
ax2.set_xlim(28, -35); ax2.set_ylim(106, 150); ax2.set_aspect('equal')
ax2.set_xlabel('y (mm)  ← 机器人左 (+Y)          机器人右 (−Y) →'); ax2.set_ylabel('z (mm)')
ax2.set_title('从 A7Z 这边往前看 (看摄像头背面): 每个插头末端的位置', fontsize=13)
from matplotlib.lines import Line2D
h = [Line2D([], [], marker='s', ls='', ms=11, mfc=cols['open'], mec='k', label='绿: 插头在摄像头下沿以下, 完全不挡'),
     Line2D([], [], marker='s', ls='', ms=11, mfc=cols['tight'], mec='k', label='橙: 前面是光板, 外排剩 1.8 mm / 里排 2.3 mm, 线要贴着插头折 90°'),
     Line2D([], [], marker='s', ls='', ms=11, mfc=cols['screw'], mec='k', label='红: 正对下面的螺丝头, 只剩 0.2 mm (外排) / 0.7 mm (里排)')]
ax2.legend(handles=h, loc='lower center', bbox_to_anchor=(0.5, -0.30), fontsize=10, frameon=False)
fig.suptitle('A7Z 排针前面到底有多少空间 (按实际模型量, 2026-10-15)', fontsize=15, y=0.97)
out = HERE / 'pin-clearance.png'
fig.savefig(out, dpi=130, bbox_inches='tight')
summary = {n: status(n) for n in range(1, 41)}
print(out); print({k: [n for n, (s, g) in summary.items() if s == k] for k in cols})
print({n: round(g, 2) for n, (s, g) in summary.items() if g is not None and n in (10, 11, 12, 17, 18, 31, 32)})
