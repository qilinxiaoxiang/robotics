"""Section plots of the parts around the top rear of the torso (shells, pack, box) to find where wires can drop into the
pack. Writes probe/sec_*.png. World frame mm."""
import sys, json
from pathlib import Path
import numpy as np, trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
HERE = Path(__file__).resolve().parent; D = HERE.parent
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit')
import ia_lib
man = ia_lib.manifest()
KEYS = ['shell_left', 'shell_right', 'rear_pack', 'openrb_board', 'imu_board', 'imu_sh4_receiving', 'torso_base', 'motor5', 'motor10',
        'xl4015_top', 'xl4015_mid', 'pd5991', 'thigh', 'right_thigh']
M = {}
for k in KEYS:
    v, f = ia_lib.load_solid(k); M[k] = trimesh.Trimesh(v, f, process=False)
M['frame'] = trimesh.load(str(D / 'frame_F-world.stl'), force='mesh') if (D / 'frame_F-world.stl').exists() else trimesh.Trimesh(*ia_lib.load_solid('rear_frame'), process=False)
M['lid'] = trimesh.Trimesh(*ia_lib.load_solid('rear_lid'), process=False)
COL = {'shell_left': 'tab:blue', 'shell_right': 'tab:cyan', 'rear_pack': 'tab:green', 'frame': 'tab:orange', 'lid': 'gold', 'openrb_board': 'purple'}
def sec(axis, val, lims, name):
    n = np.zeros(3); n[axis] = 1; o = np.zeros(3); o[axis] = val
    ax2 = [i for i in range(3) if i != axis]
    fig, ax = plt.subplots(figsize=(9, 7))
    for k, m in M.items():
        try:
            s = m.section(plane_origin=o, plane_normal=n)
        except Exception:
            s = None
        if s is None:
            continue
        for e in s.discrete:
            ax.plot(e[:, ax2[0]], e[:, ax2[1]], color=COL.get(k, 'grey'), lw=0.8)
    ax.set_xlim(lims[0]); ax.set_ylim(lims[1]); ax.set_aspect('equal'); ax.grid(True, lw=0.3)
    ax.set_xlabel('xyz'[ax2[0]]); ax.set_ylabel('xyz'[ax2[1]]); ax.set_title(f'{name}: {"xyz"[axis]} = {val}')
    from matplotlib.ticker import MultipleLocator
    ax.xaxis.set_minor_locator(MultipleLocator(1)); ax.yaxis.set_minor_locator(MultipleLocator(1)); ax.grid(True, which='minor', lw=0.1)
    fig.savefig(HERE / f'sec_{name}_{"xyz"[axis]}{val:+.0f}.png', dpi=110); plt.close(fig)
for x in (-46.0, -44.0, -40.0, -36.0, -30.0, -25.0, -22.0):
    sec(0, x, ((-40, 40), (10, 50)), 'yz')
for y in (4.0, 9.0, 13.0, 16.0, 20.0, 25.0, 29.0, 31.0):
    sec(1, y, ((-70, -10), (0, 50)), 'xz')
for z in (29.0, 33.0, 36.0, 38.5, 40.0, 41.5, 42.5):
    sec(2, z, ((-70, -10), (-40, 40)), 'xy')
print('ok')
