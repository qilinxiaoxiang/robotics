"""Render the left split-ankle assembly as a GIF from guide-data.json (same geometry and approach paths as the guide steps
'ankle-split' and 'ankle-feet' in guide/content/steps.py).

    /tmp/microduck-cad-venv/bin/python assembly_animation.py            -> assembly-left.gif beside this file

Stages: 1 sleeve slides onto the link boss along the shaft, 2 base rises onto the servo output, 3 side comes up from
below 8 mm inboard then slides outboard onto the sleeve, 4 foot slides up from below. Static: lower link, servo, washer.
"""
import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import imageio.v2 as imageio

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'content' / 'interference-audit'))
import ia_lib as L  # noqa: E402

STATIC = ['lower', 'motor6', 'washer6']
# key -> list of offsets (mm, world) the part passes through before its seat; the guide approach lists are relative
MOVES = [('smallring', [[0, -22, 0]]),            # along the shaft from the inboard side onto the 10 mm boss
         ('ankle', [[0, 0, -28]]),                 # base up from below onto the servo output
         ('ankle_cheek', [[0, -8, -30], [0, -8, 0]]),  # steps.py 'ankle-split' approach
         ('foot', [[0, 0, -12]])]                  # steps.py 'ankle-feet' approach
LABEL = {'smallring': '1  black sleeve slides onto the link boss (no press)',
         'ankle': '2  orange base onto the servo output, 4 x M2 x 4',
         'ankle_cheek': '3  orange side up from below, then along the shaft onto the sleeve, 2 x M2 x 8',
         'foot': '4  yellow foot slides up from below, 1 x M2 x 6 at the toe'}
FRAMES_PER_LEG = 14
LIGHT = np.array([0.4, -0.7, 0.6]) / np.linalg.norm([0.4, -0.7, 0.6])


def part_color(p):
    c = p['color']  # guide-data.json hex; the black link and sleeve are lifted so their edges show on the white page
    return '#4a4a4a' if c.lower() == '#202020' else c


def shaded(tri, col):
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    k = 0.55 + 0.45 * np.clip(n @ LIGHT, 0, 1)
    rgb = np.array(matplotlib.colors.to_rgb(col))
    return np.clip(rgb[None, :] * k[:, None], 0, 1)


def main():
    g = L.load_guide()
    parts = {p['key']: p for p in g['parts']}
    meshes = {}
    for k in STATIC + [m[0] for m in MOVES]:
        v, f = L.decode_guide_part(parts[k])
        meshes[k] = (v, f, part_color(parts[k]))
    allv = np.vstack([meshes[k][0] for k in ('ankle', 'ankle_cheek', 'foot', 'smallring')])
    c = (allv.min(0) + allv.max(0)) / 2 + np.array([0, 0, 6])
    r = (allv.max(0) - allv.min(0)).max() * 0.62
    frames = []
    placed = list(STATIC)

    def draw(moving=None, offset=None, label=''):
        fig = plt.figure(figsize=(8, 6), dpi=100)
        ax = fig.add_subplot(111, projection='3d')
        for k in placed + ([moving] if moving else []):
            v, f, col = meshes[k]
            if k == moving:
                v = v + np.asarray(offset)
            tri = v[f]
            pc = Poly3DCollection(tri, facecolors=shaded(tri, col), edgecolors='none', linewidths=0)
            pc.set_zsort('average')
            ax.add_collection3d(pc)
        ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
        ax.view_init(elev=22, azim=-125)  # from the inboard side, slightly in front and above, so the side's path shows
        ax.set_axis_off()
        fig.text(0.02, 0.95, 'Left split ankle, V1.22', fontsize=12, weight='bold')
        fig.text(0.02, 0.905, label, fontsize=10)
        fig.tight_layout()
        fig.canvas.draw()
        img = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()
        plt.close(fig)
        return img

    frames.append(draw(label='link, servo and washer on the bench'))
    for key, path in MOVES:
        pts = [np.asarray(p, float) for p in path] + [np.zeros(3)]
        for a, b in zip(pts[:-1], pts[1:]):
            n = max(4, int(FRAMES_PER_LEG * np.linalg.norm(b - a) / 30))
            for t in np.linspace(0, 1, n, endpoint=False):
                frames.append(draw(key, a + (b - a) * t, LABEL[key]))
        placed.append(key)
        for _ in range(4):
            frames.append(draw(label=LABEL[key] + '  (seated)'))
    for _ in range(8):
        frames.append(draw(label='done: the foot holds the side in; to open, foot off first'))
    out = HERE / 'assembly-left.gif'
    imageio.mimsave(out, frames, duration=0.12, loop=0)
    print(out, len(frames), 'frames')


if __name__ == '__main__':
    main()
