#!/usr/bin/env python3
"""Zoomed plan/side slices of the left-rear pocket and the space above the jaw servo, all current parts."""
import sys, json, os
os.environ['EXT19_IA_CACHE'] = '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/ia-cache'
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/ext-v19/scripts')
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
import ext_lib as E
man = E.ia_lib.manifest()
keys = ['head_bottom', 'jaw_support', 'motor13', 'motor14', 'motor15', 'jaw_frame', 'pi', 'amplifier', 'speaker', 'speaker_retainer', 'speaker_tape',
        'clip_head', 'clip_cap', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b', 'camera_board', 'face_panel', 'head_cap',
        'head_pi_zero_w_header_base', 'mouth_sliding_ring', 'neck_pitch', 'motor11', 'idler11', 'idler_cap11', 'neck_pitch_ring', 'rear_pack', 'shell_left', 'shell_right', 'clip_bracket', 'clip_torso', 'motor12']
cols = plt.cm.tab20(np.linspace(0, 1, 20))
M = {}
for k in keys:
    if k in man:
        v, f = E.ia_lib.load_solid(k); M[k] = trimesh.Trimesh(v, f, process=False)
    else: print('missing', k)
print({k: [list(np.round(M[k].bounds[0], 1)), list(np.round(M[k].bounds[1], 1))] for k in ('amplifier', 'speaker', 'speaker_retainer', 'head_cap', 'clip_head', 'clip_cap') if k in M})
route = json.load(open('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/ext-v19/route-v19.json'))['routes'][0]['points']
R = np.array([p[:3] for p in route])
ttl = json.load(open('/Users/xiangzheng/code/robotics/microduck-sim/guide/content/routes.json'))['routes']
S1311 = np.array(ttl['ttl-13-11']); S1514 = np.array(ttl['ttl-15-14']); S1413 = np.array(ttl['ttl-14-13'])
def plan(zs, out, normal=(0, 0, 1), lim=None, ncol=3):
    n = len(zs); rows = int(np.ceil(n / ncol)); fig, axs = plt.subplots(rows, ncol, figsize=(7 * ncol, 7 * rows)); axs = np.atleast_1d(axs).ravel()
    for ax, z in zip(axs, zs):
        o = np.array(normal, float) * z
        for i, (k, m) in enumerate(M.items()):
            s = m.section(plane_origin=o, plane_normal=normal)
            if s is None: continue
            c = cols[i % 20]; lab = k
            for ent in s.discrete:
                e = np.asarray(ent)
                if normal == (0, 0, 1): x, y = e[:, 0], e[:, 1]
                elif normal == (1, 0, 0): x, y = e[:, 1], e[:, 2]
                else: x, y = e[:, 0], e[:, 2]
                ax.plot(x, y, '-', color=c, lw=1.2, label=lab); lab = None
        for P, cc, nm in ((R, 'k', 'bundle'), (S1311, 'm', 'ttl 13-11'), (S1514, 'c', 'ttl 15-14'), (S1413, 'g', 'ttl 14-13')):
            if normal == (0, 0, 1): ax.plot(P[:, 0], P[:, 1], '.-', color=cc, lw=0.8, ms=3, label=nm)
            elif normal == (1, 0, 0): ax.plot(P[:, 1], P[:, 2], '.-', color=cc, lw=0.8, ms=3, label=nm)
            else: ax.plot(P[:, 0], P[:, 2], '.-', color=cc, lw=0.8, ms=3, label=nm)
        if normal == (0, 0, 1):
            for i, p in enumerate(R): ax.annotate(f'{i}:{p[2]:.0f}', (p[0], p[1]), fontsize=6)
            ax.set_title(f'z = {z}'); ax.set_xlabel('x'); ax.set_ylabel('y')
        elif normal == (1, 0, 0): ax.set_title(f'x = {z}'); ax.set_xlabel('y'); ax.set_ylabel('z')
        else: ax.set_title(f'y = {z}'); ax.set_xlabel('x'); ax.set_ylabel('z')
        ax.set_aspect('equal'); ax.grid(True, lw=0.3); ax.set_xticks(np.arange(lim[0][0], lim[0][1] + 1, 5)); ax.set_yticks(np.arange(lim[1][0], lim[1][1] + 1, 5))
        ax.tick_params(labelsize=6)
        if lim: ax.set_xlim(lim[0]); ax.set_ylim(lim[1])
    h, l = axs[0].get_legend_handles_labels(); d = dict(zip(l, h))
    fig.legend(d.values(), d.keys(), loc='lower center', ncol=8, fontsize=7)
    fig.savefig(out, dpi=120); plt.close(fig); print(out)
plan([107, 110, 112, 114, 117, 120], 'zoom_plan_low.png', lim=((-10, 60), (-35, 45)))
plan([124, 128, 131, 134, 137, 141], 'zoom_plan_high.png', lim=((-10, 60), (-35, 45)))
plan([145, 148], 'zoom_plan_top.png', lim=((-10, 80), (-35, 45)), ncol=2)
plan([8, 12, 15, 18, 21, 24], 'zoom_side_y.png', normal=(0, 1, 0), lim=((-30, 80), (95, 155)))
plan([4, 8, 12, 16, 20, 30], 'zoom_side_x.png', normal=(1, 0, 0), lim=((-35, 45), (95, 155)))
plan([40, 48, 52, 58, 66, 76], 'zoom_side_x2.png', normal=(1, 0, 0), lim=((-35, 45), (95, 155)))
