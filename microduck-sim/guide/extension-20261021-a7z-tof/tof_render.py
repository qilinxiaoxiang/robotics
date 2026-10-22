"""Pick the ToF spot that keeps the planned LED sightline clear, then draw front view + two sections."""
import json, sys, numpy as np, trimesh, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
from matplotlib.collections import PolyCollection
R = '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/'
W, A, F = R + 'world/', R + 'a7z-head/', R + 'face-a7z/'
OUT = sys.argv[1]
d = json.load(open(OUT + '/tof_place.json'))
FB, DEPTH, BW, BH, HALF = 80.1, 6.5, 12.7, 22.9, np.radians(22.5)

# A7Z green LED (LED_NOTE: s 47.9 from pin-1 end, d 28.1 from header edge, component side)
fr = json.load(open(A + 'checks.json'))['frame']
O, ES, ED, N = (np.array(fr[k]) for k in ('origin', 'es', 'ed', 'n'))
led = O + 47.9 * ES + 28.1 * ED + 2.0 * N
hole = np.array([FB, -20.0, 143.0])

def box_hits_segment(yc, zc, p0, p1, pad=1.0):
    lo = np.array([FB - DEPTH, yc - BW / 2 - pad, zc - BH / 2 - pad]); hi = np.array([FB, yc + BW / 2 + pad, zc + BH / 2 + pad])
    t = np.linspace(0, 1, 400)[:, None]; pts = p0 + t * (p1 - p0)
    return bool(((pts >= lo) & (pts <= hi)).all(axis=1).any())

ok = [c for c in d['all'] if not box_hits_segment(c['y'], c['z'], led, hole)]
ok.sort(key=lambda c: c['cam_axis_mm'])
pick = ok[0]
yc, zc = pick['y'], pick['z']
print('LED at', led.round(1), 'candidates clear of LED ray', len(ok), 'of', len(d['all']), 'pick', pick)

parts = {'face': (F + 'face_panel_a7z.stl', '#f2f2ee', '#9a9a90'), 'trim': (F + 'eye_trim_a7z.stl', '#2b2b2b', '#111'),
         'camera': (F + 'camera_13m214.stl', '#3d7a3d', '#1f4f1f'), 'cap': (A + 'head_cap_a7z-world.stl', '#e8e8e2', '#888'),
         'jaw': (W + 'jaw_frame.stl', '#f0a030', '#a06010'), 'bottom': (W + 'head_bottom.stl', '#e8e8e2', '#888'),
         'a7z': (W + 'a7z_pcb.stl', '#1d3f8f', '#102050')}
M = {k: trimesh.load(p) for k, (p, _, _) in parts.items()}

fig = plt.figure(figsize=(15, 9.5))
gs = fig.add_gridspec(2, 2, width_ratios=[1.25, 1], height_ratios=[1, 1])

# 1. front view (viewer in front of the duck: duck's right on the left of the picture)
ax = fig.add_subplot(gs[:, 0])
for k in ['face', 'trim']:
    m = M[k]; v = m.vertices[m.faces]
    front = m.face_normals[:, 0] > 0.2
    ax.add_collection(PolyCollection(v[front][:, :, 1:], facecolor=parts[k][1], edgecolor='none'))
cy = M['camera'].bounds
ax.add_patch(Rectangle((-16.1, 115.1), 32.2, 32.0, fill=False, ls='--', lw=1.4, ec='#2e7d32'))
ax.text(0, 148.2, 'camera board (behind face)', ha='center', fontsize=9, color='#2e7d32')
ax.add_patch(Rectangle((16.1, 125), 17.2, 12, fill=False, ls=':', lw=1.2, ec='#2e7d32'))
ax.text(24.7, 123.3, 'camera ribbon', ha='center', fontsize=8, color='#2e7d32')
feas = [(c['y'], c['z']) for c in ok]
fy, fz = np.array(feas).T
ax.scatter(fy, fz, s=6, c='#7fbf7f', alpha=0.5, label='board centres that fit')
ax.add_patch(Rectangle((yc - BW / 2, zc - BH / 2), BW, BH, fill=False, lw=2.2, ec='#c62828', ls='--'))
ax.text(yc, zc - BH / 2 - 2.2, 'VL53L8CX carrier\n12.7 x 22.9 (behind face)', ha='center', va='top', fontsize=9, color='#c62828')
ax.add_patch(Rectangle((yc - 4.0, zc - 2.3), 8.0, 4.6, fc='#c62828', ec='k', lw=0.8))
ax.annotate('future window ~8 x 4.6 mm\n(needs face reprint)', (yc, zc + 2.3), (yc - 6, zc + 24), fontsize=9,
            arrowprops=dict(arrowstyle='->', color='#c62828'), color='#c62828', ha='center')
ax.add_patch(plt.Circle((-20, 143), 1.5, fc='#43a047', ec='k'))
ax.annotate('planned LED hole (y -20, z 143)', (-20, 144.5), (-20, 158), fontsize=9, ha='center',
            arrowprops=dict(arrowstyle='->'))
ax.plot([0], [131.11], 'k+', ms=10)
ax.set_xlim(-48, 48); ax.set_ylim(106, 162); ax.set_aspect('equal'); ax.invert_xaxis() if False else None
ax.set_xlabel("y (mm)   <- duck's right            duck's left ->"); ax.set_ylabel('z (mm)')
ax.set_title('Front view of the face (as you look at the duck)')
ax.legend(loc='lower right', fontsize=8)

def section(ax, normal, origin, axes, title, xl, yl, sensor):
    for k in ['cap', 'bottom', 'jaw', 'face', 'trim', 'camera', 'a7z']:
        s = M[k].section(plane_origin=origin, plane_normal=normal)
        if s is None: continue
        for e in s.discrete:
            ax.fill(e[:, axes[0]], e[:, axes[1]], fc=parts[k][1], ec=parts[k][2], lw=0.8, alpha=0.95)
    sx, sv = sensor
    ax.add_patch(Rectangle((FB - DEPTH, sv - (BW if axes[1] == 1 else BH) / 2), DEPTH, BW if axes[1] == 1 else BH,
                           fc='#ef9a9a', ec='#c62828', lw=1.5, alpha=0.8))
    L = 45
    ax.fill([sx, sx + L, sx + L], [sv, sv + L * np.tan(HALF), sv - L * np.tan(HALF)], fc='#ffcdd2', ec='#c62828', alpha=0.35, lw=1)
    ax.text(sx + 30, sv, '45 deg FoV', fontsize=8, color='#c62828', va='center')
    ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect('equal'); ax.set_title(title, fontsize=10)

ax2 = fig.add_subplot(gs[0, 1])
section(ax2, [0, 0, 1], [0, 0, zc], (0, 1), f'Top section at z {zc:.0f} (looking down)', (40, 128), (-48, 40), (FB - 0.3, yc))
ax2.set_xlabel('x (mm), forward ->'); ax2.set_ylabel('y (mm)')
ax3 = fig.add_subplot(gs[1, 1])
section(ax3, [0, 1, 0], [0, yc, 0], (0, 2), f'Side section at y {yc:.0f} (from the duck\'s right)', (40, 128), (96, 162), (FB - 0.3, zc))
ax3.set_xlabel('x (mm), forward ->'); ax3.set_ylabel('z (mm)')
fig.suptitle(f'VL53L8CX (Pololu 3419) behind the A7Z face: centre y {yc:.1f}, z {zc:.1f} (study only, no print file changed)', fontsize=12)
fig.tight_layout()
fig.savefig(OUT + '/tof-placement.png', dpi=130)
json.dump(dict(pick=pick, led=led.round(2).tolist(), n_clear=len(ok), clear_range=dict(y=[min(fy), max(fy)], z=[min(fz), max(fz)])),
          open(OUT + '/tof_pick.json', 'w'), indent=1)
