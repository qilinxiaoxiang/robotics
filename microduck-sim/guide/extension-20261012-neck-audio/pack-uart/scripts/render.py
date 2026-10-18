"""PNG sections and views of the socket area (matplotlib, exact mesh sections). Writes ../png/*.png."""
import json
import numpy as np, trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
import uart_lib as U

S = json.loads((U.STUDY / 'sockets.json').read_text())
O = json.loads((U.STUDY / 'options.json').read_text())
SS = U.STUDY / 'study-solids'
M = {k: U.tm(k) for k in ['rear_pack', 'rear_pack_cover', 'regulator', 'openrb_board', 'shell_left', 'shell_right']}
M['cover_A'] = trimesh.load(SS / 'cover_with_windows_A+G.stl')
M['plugs_A'] = trimesh.load(SS / 'plugs_A.stl'); M['plug_GND'] = trimesh.load(SS / 'plug_GND.stl')
M['wires_A'] = trimesh.load(SS / 'wires_A.stl'); M['wire_GND'] = trimesh.load(SS / 'wire_GND.stl')
M['vin20_new'] = trimesh.load(SS / 'vin20_rerouted.stl')
M['vin20_old'] = U.from_m(U.tube(U.ROUTES['vin20'], U.CABLE_R['vin20']))
for k in ('dxl5', 'dxl10', 'openrbpwr', 'trunk'):
    M['cab_' + k] = U.from_m(U.tube(U.ROUTES[k], U.CABLE_R[k]))
STY = {'rear_pack': ('#f2a541', 'pack (orange)'), 'rear_pack_cover': ('#444444', 'cover'), 'cover_A': ('#444444', 'cover with window'),
       'regulator': ('#3b7dd8', 'DFR1202 converter'), 'openrb_board': ('#2e8b57', 'OpenRB-150'), 'shell_left': ('#bbbbbb', 'torso shell'),
       'shell_right': ('#bbbbbb', None), 'plugs_A': ('#d62728', 'Dupont male plug'), 'plug_GND': ('#d62728', None),
       'wires_A': ('#8c1aff', 'jumper wire'), 'wire_GND': ('#8c1aff', None), 'vin20_new': ('#ef6c00', '20 V lead, re-routed'),
       'vin20_old': ('#ef6c00', '20 V lead, guide route'), 'cab_dxl5': ('#6a3df0', 'leg links'), 'cab_dxl10': ('#6a3df0', None),
       'cab_openrbpwr': ('#c0392b', '5 V pairs'), 'cab_trunk': ('#c0392b', None)}


def section(ax, keys, axis, val, plane_xy, dashed=()):
    n = np.zeros(3); n[axis] = 1; o = np.zeros(3); o[axis] = val
    done = set()
    for k in keys:
        sec = M[k].section(plane_origin=o, plane_normal=n)
        if sec is None:
            continue
        col, lab = STY[k]
        for ent in sec.discrete:
            P = ent[:, plane_xy]
            ls = '--' if k in dashed else '-'
            fill = k not in dashed
            ax.add_patch(Polygon(P, closed=True, fc=col if fill else 'none', ec=col, alpha=0.55 if fill else 1, lw=0.8, ls=ls,
                                 label=lab if (lab and k not in done) else None))
            done.add(k)


def finish(ax, title, xl, yl, lims):
    ax.set_xlim(*lims[0]); ax.set_ylim(*lims[1]); ax.set_aspect('equal'); ax.grid(alpha=0.25)
    ax.set_title(title, fontsize=10); ax.set_xlabel(xl); ax.set_ylabel(yl)
    h, l = ax.get_legend_handles_labels(); seen = {}
    for hh, ll in zip(h, l):
        seen.setdefault(ll, hh)
    ax.legend(seen.values(), seen.keys(), fontsize=7, loc='upper right')


TOP = S['rows']['J7']['socketTopX']
# 1. why the guide hookup fails: section through J7 (y = 9.93)
fig, ax = plt.subplots(figsize=(8, 8))
yJ7 = S['rows']['J7']['rowCentreY']
section(ax, ['shell_left', 'rear_pack', 'rear_pack_cover', 'regulator', 'openrb_board', 'cab_openrbpwr', 'cab_trunk'], 1, yJ7, [0, 2])
for s in S['rows']['J7']['sockets'][:8]:
    ax.annotate(f"{s['socket']} {s['name'].split(' ')[0]}", (TOP, s['z']), xytext=(TOP + 4, s['z']), fontsize=7, va='center',
                arrowprops=dict(arrowstyle='-', lw=0.4))
for nm, n in (('D14', 6), ('D13', 7)):
    z = S['rows']['J7']['sockets'][n - 1]['z']
    ax.add_patch(Rectangle((TOP - 14, z - 1.27), 14, 2.54, fc='none', ec='red', lw=1.4, ls='--',
                           label='straight Dupont plug needed (14 mm)' if n == 6 else None))
ax.annotate('2.04 mm from socket top\nto converter back', (-36, 1.5), xytext=(-60, 12), fontsize=8, arrowprops=dict(arrowstyle='->'))
ax.annotate('10.04 mm socket top\nto cover inside', (-40, -7.7), xytext=(-62, -16), fontsize=8, arrowprops=dict(arrowstyle='->'))
finish(ax, f'Section y = {yJ7} (J7 row, guide sockets 4/6/7): D13 and D14 sit behind the converter', 'x (mm, forward →)', 'z (mm)',
       ((-66, -18), (-25, 22)))
fig.savefig(U.STUDY / 'png' / '1-section-J7-why-not.png', dpi=150, bbox_inches='tight'); plt.close(fig)

# 2. option A: section through J6 (y = -10.43)
fig, ax = plt.subplots(figsize=(8, 10))
yJ6 = S['rows']['J6']['rowCentreY']
section(ax, ['shell_right', 'rear_pack', 'cover_A', 'regulator', 'openrb_board', 'plugs_A', 'wires_A', 'vin20_new', 'vin20_old',
             'cab_dxl5', 'cab_dxl10'], 1, yJ6, [0, 2], dashed=('vin20_old',))
section(ax, ['wires_A'], 1, yJ6 - 0.68, [0, 2])
for s in S['rows']['J6']['sockets'][:7]:
    ax.annotate(f"{s['socket']} {s['name'].split(' ')[0]}", (TOP, s['z']), xytext=(TOP + 4, s['z']), fontsize=7, va='center',
                arrowprops=dict(arrowstyle='-', lw=0.4))
ax.annotate('window in cover\n3.5 x 6.1 mm', (-46, -9), xytext=(-66, -22), fontsize=8, arrowprops=dict(arrowstyle='->'))
ax.annotate('wires run up the cover back\nand over its top edge', (-50.6, 15), xytext=(-70, 20), fontsize=8, arrowprops=dict(arrowstyle='->'))
finish(ax, f'Option A, section y = {yJ6} (J6 row): plugs in A1 / A2 below the converter', 'x (mm, forward →)', 'z (mm)',
       ((-72, -18), (-45, 42)))
fig.savefig(U.STUDY / 'png' / '2-section-J6-option-A.png', dpi=150, bbox_inches='tight'); plt.close(fig)

# 3. rear view (looking forward at the cover; robot +y on the left as seen from behind)
fig, ax = plt.subplots(figsize=(7, 9))
section(ax, ['cover_A'], 0, -46.0, [1, 2])
section(ax, ['regulator'], 0, -41.0, [1, 2])
section(ax, ['rear_pack'], 0, -42.0, [1, 2])
for row, col in (('J6', '#2e8b57'), ('J7', '#2e8b57')):
    for s in S['rows'][row]['sockets'][:8]:
        ax.add_patch(Rectangle((s['y'] - 0.55, s['z'] - 0.55), 1.1, 1.1, fc=col, ec='k', lw=0.3))
        ax.text(s['y'] + (1.6 if row == 'J6' else -1.6), s['z'], f"{row}-{s['socket']} {s['name'].split(' ')[0]}", fontsize=6,
                ha='left' if row == 'J6' else 'right', va='center')
ax.invert_xaxis()
finish(ax, 'Rear view at x = -46 (cover cut), converter (blue) and pack at x -41/-42; sockets in green', 'y (mm, robot left ←)', 'z (mm)',
       ((24, -24), (-24, 32)))
fig.savefig(U.STUDY / 'png' / '3-rear-view-windows.png', dpi=150, bbox_inches='tight'); plt.close(fig)

# 4. top view of the over-the-top run (section z = 30.7)
fig, ax = plt.subplots(figsize=(9, 7))
section(ax, ['shell_left', 'shell_right', 'rear_pack', 'wires_A', 'wire_GND', 'cab_dxl5', 'cab_dxl10', 'cab_trunk'], 2, 30.7, [0, 1])
section(ax, ['cover_A', 'regulator'], 2, 26.0, [0, 1])
finish(ax, 'Section z = 30.7 (wires over the cover top edge to the guide UART path); cover and converter cut at z 26', 'x (mm, forward →)',
       'y (mm, left ↑)', ((-56, -15), (-22, 22)))
fig.savefig(U.STUDY / 'png' / '4-top-run-z30.7.png', dpi=150, bbox_inches='tight'); plt.close(fig)
print('ok')
