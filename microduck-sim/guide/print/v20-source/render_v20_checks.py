"""Section drawings for the V2.0 source checks: tunnel cap, shell-to-pack screw stacks, jaw pivot boss. Writes png/."""
import sys, json
from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'rear-pack'))
import pack_lib as P  # noqa: E402

R = json.load(open(HERE / 'v20-source.json'))
old = {k: P.solid_mesh(k) for k in ('shell_left', 'shell_right', 'rear_pack', 'jaw_frame', 'mouth_sliding_ring')}
new = {'shell_left': trimesh.load(HERE / 'shell_left_v20-world.stl'), 'shell_right': trimesh.load(HERE / 'shell_right_v20-world.stl'),
       'jaw_frame': trimesh.load(HERE / 'jaw_frame_v20-world.stl')}
(HERE / 'png').mkdir(exist_ok=True)


def draw(ax, mesh, origin, normal, axes, color, lw):
    s = mesh.section(plane_origin=origin, plane_normal=normal)
    if s is None:
        return
    for e in s.discrete:
        ax.plot(e[:, axes[0]], e[:, axes[1]], color, lw=lw)


# tunnel cap
X0, Z0 = -38.0, 34.96
fig, axs = plt.subplots(2, 3, figsize=(15, 9))
for row, (key, ys) in enumerate((('shell_left', (18, 34)), ('shell_right', (-34, -18)))):
    for col, (n, o, lab, ax_) in enumerate([((0, 0, 1), (0, 0, Z0), 'z 35.0 (tunnel axis)', (0, 1)),
                                            ((0, 0, 1), (0, 0, Z0 + 1.8), 'z 36.8', (0, 1)),
                                            ((1, 0, 0), (X0, 0, 0), 'x -38 (tunnel axis)', (1, 2))]):
        ax = axs[row, col]
        draw(ax, old[key], o, n, ax_, 'k', 2.2); draw(ax, new[key], o, n, ax_, 'r', 1.0)
        if ax_ == (0, 1):
            ax.set_xlim(-48, -28); ax.set_ylim(*ys); ax.set_xlabel('x'); ax.set_ylabel('y')
        else:
            ax.set_xlim(*ys); ax.set_ylim(28, 43); ax.set_xlabel('y'); ax.set_ylabel('z')
        ax.set_aspect('equal'); ax.set_title(f'{key} {lab}: black printed, red V2.0'); ax.grid(alpha=.3)
plt.tight_layout(); plt.savefig(HERE / 'png' / 'tunnel-fill-sections.png', dpi=110); plt.close()

# shell-to-pack screws: section through the screw axis, plane x = -21.5 (y-z) and plane y = +-20 (x-z)
fig, axs = plt.subplots(2, 2, figsize=(12, 9))
for row, key in enumerate(('shell_left', 'shell_right')):
    s = R['packScrews'][key]; sx, sy, seat = s['center']; tip = s['tipZ']
    for col, (n, o, ax_, lab) in enumerate([((1, 0, 0), (sx, 0, 0), (1, 2), f'x {sx}'), ((0, 1, 0), (0, sy, 0), (0, 2), f'y {sy:+g}')]):
        ax = axs[row, col]
        draw(ax, old['rear_pack'], o, n, ax_, 'tab:orange', 1.6)
        draw(ax, new[key], o, n, ax_, 'k', 1.4)
        c = sy if ax_[0] == 1 else sx
        ax.add_patch(plt.Rectangle((c - 2.0, seat), 4.0, 1.6, fc='tab:blue', alpha=.5))
        ax.add_patch(plt.Rectangle((c - 1.0, tip), 2.0, seat - tip, fc='tab:blue', alpha=.35))
        ax.plot([c - 0.8, c - 0.8, c + 0.8, c + 0.8], [s['packBarTopZ'], s['pilotDrill']['bottomZ'], s['pilotDrill']['bottomZ'], s['packBarTopZ']], 'g--', lw=1)
        ax.set_xlim(c - 9, c + 9); ax.set_ylim(28, 46); ax.set_aspect('equal'); ax.grid(alpha=.3)
        ax.set_title(f'{key} screw, plane {lab}: black V2.0 shell, orange V1.9 pack,\nblue M2 x 6, green dashed dia 1.6 pilot ({s["engagementMm"]:.1f} mm thread in pack)')
plt.tight_layout(); plt.savefig(HERE / 'png' / 'pack-screw-sections.png', dpi=110); plt.close()

# jaw pivot boss: plane z 118.61 (x-y) and plane x 26.1 (y-z)
JX, JZ = 26.1, 118.61
fig, axs = plt.subplots(1, 2, figsize=(12, 5.5))
for ax, (n, o, ax_, lims) in zip(axs, [((0, 0, 1), (0, 0, JZ), (0, 1), ((16, 36), (-47, -33))),
                                        ((1, 0, 0), (JX, 0, 0), (1, 2), ((-47, -33), (108, 129)))]):
    draw(ax, old['jaw_frame'], o, n, ax_, 'k', 2.2); draw(ax, new['jaw_frame'], o, n, ax_, 'r', 1.0)
    draw(ax, old['mouth_sliding_ring'], o, n, ax_, 'tab:green', 1.0)
    ax.set_xlim(*lims[0]); ax.set_ylim(*lims[1]); ax.set_aspect('equal'); ax.grid(alpha=.3)
    ax.set_title(f'jaw passive arm, plane {"z 118.61" if ax_ == (0, 1) else "x 26.1"}: black printed, red V2.0, green ring')
plt.tight_layout(); plt.savefig(HERE / 'png' / 'jaw-hole-sections.png', dpi=110); plt.close()
print('ok')
