#!/usr/bin/env python3
"""Plan-view slices of the head and neck at several z levels (robot frame), parts coloured, designed route overlaid."""
import sys, json, os
os.environ['EXT19_IA_CACHE'] = '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/ia-cache'
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/ext-v19/scripts')
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
import ext_lib as E
man = E.ia_lib.manifest()
keys = ['head_bottom', 'jaw_support', 'motor13', 'motor14', 'motor15', 'jaw_frame', 'pi', 'amplifier', 'speaker', 'speaker_retainer',
        'clip_torso', 'clip_bracket', 'clip_head', 'clip_cap', 'neck_pitch', 'motor11', 'motor12', 'idler11', 'idler_cap11', 'head_yaw_link',
        'head_roll_ring_a', 'head_roll_ring_b', 'neck_link_a', 'neck_link_b', 'shell_left', 'shell_right', 'rear_pack', 'camera_board', 'face_panel',
        'head_pi_zero_w_header_base', 'mouth_sliding_ring', 'neck_pitch_ring', 'speaker_tape', 'imu_board']
cols = plt.cm.tab20(np.linspace(0, 1, len(keys)))
M = {}
for k in keys:
    if k in man:
        v, f = E.ia_lib.load_solid(k); M[k] = trimesh.Trimesh(v, f, process=False)
    else:
        print('missing', k)
M['head_cap_v19'] = trimesh.load(str(E.PARTS['head_cap_v19']), force='mesh')
route = json.load(open('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/ext-v19/route-v19.json'))['routes'][0]['points']
R = np.array([p[:3] for p in route])
def plan(zs, out, normal=(0, 0, 1), lim=None):
    n = len(zs); fig, axs = plt.subplots(1, n, figsize=(7 * n, 7))
    for ax, z in zip(np.atleast_1d(axs), zs):
        o = np.array(normal, float) * z
        for i, (k, m) in enumerate(M.items()):
            s = m.section(plane_origin=o, plane_normal=normal)
            if s is None: continue
            c = cols[i % len(cols)] if k in keys else (0.3, 0.3, 0.3, 1)
            lab = k
            for ent in s.discrete:
                e = np.asarray(ent)
                if normal == (0, 0, 1): x, y = e[:, 0], e[:, 1]
                elif normal == (1, 0, 0): x, y = e[:, 1], e[:, 2]
                else: x, y = e[:, 0], e[:, 2]
                ax.plot(x, y, '-', color=c, lw=1, label=lab); lab = None
        if normal == (0, 0, 1):
            ax.plot(R[:, 0], R[:, 1], 'k.-', lw=0.8, ms=3)
            for i, p in enumerate(R): ax.annotate(f'{i}:{p[2]:.0f}', (p[0], p[1]), fontsize=6)
            ax.set_xlabel('x (forward)'); ax.set_ylabel('y (left)'); ax.set_title(f'z = {z}')
        elif normal == (1, 0, 0):
            ax.plot(R[:, 1], R[:, 2], 'k.-', lw=0.8, ms=3)
            for i, p in enumerate(R): ax.annotate(f'{i}:{p[0]:.0f}', (p[1], p[2]), fontsize=6)
            ax.set_xlabel('y (left)'); ax.set_ylabel('z'); ax.set_title(f'x = {z}')
        else:
            ax.plot(R[:, 0], R[:, 2], 'k.-', lw=0.8, ms=3)
            for i, p in enumerate(R): ax.annotate(f'{i}:{p[1]:.0f}', (p[0], p[2]), fontsize=6)
            ax.set_xlabel('x (forward)'); ax.set_ylabel('z'); ax.set_title(f'y = {z}')
        ax.set_aspect('equal'); ax.grid(True, lw=0.3)
        if lim: ax.set_xlim(lim[0]); ax.set_ylim(lim[1])
    h, l = np.atleast_1d(axs)[0].get_legend_handles_labels(); d = dict(zip(l, h))
    fig.legend(d.values(), d.keys(), loc='lower center', ncol=8, fontsize=7)
    fig.savefig(out, dpi=110); plt.close(fig); print(out)
plan([104, 110], 'plan_a.png', lim=((-40, 95), (-50, 50)))
plan([114, 118], 'plan_b.png', lim=((-40, 95), (-50, 50)))
plan([122, 127], 'plan_c.png', lim=((-40, 95), (-50, 50)))
plan([133, 140], 'plan_d.png', lim=((-40, 95), (-50, 50)))
plan([147], 'plan_e.png', lim=((-40, 95), (-50, 50)))
plan([26, 34], 'side_x.png', normal=(1, 0, 0), lim=((-50, 50), (20, 160)))
plan([48, 20], 'side_x2.png', normal=(1, 0, 0), lim=((-50, 50), (95, 160)))
plan([-22, 0, 18], 'side_y.png', normal=(0, 1, 0), lim=((-40, 95), (20, 160)))
