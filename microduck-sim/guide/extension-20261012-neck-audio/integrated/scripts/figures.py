#!/usr/bin/env python3
"""Overlay figures of the integrated head with route A3 (png/): side (from -y), rear (from -x), top, and a close-up of
the fan in front of the header. Parts are drawn as projected, semi-transparent triangle silhouettes; route centrelines
from route-A3.json. Draws only; every number shown comes from route-A3.json / pairwise JSON.
"""
import json

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import trimesh  # noqa: E402

import int_lib as L  # noqa: E402
from check_lib import tm_from_man  # noqa: E402
from pm_lib import audio_solid, audio_wire_tubes  # noqa: E402
from route_scene import pin34_housing  # noqa: E402
from scene import load_tm  # noqa: E402

OUT = L.STUDY / 'png'
OUT.mkdir(exist_ok=True)
GROUPS = [
    ('integrated cap', '#9aa5b1', 0.10, lambda: [trimesh.load(L.INTEGRATED_CAP, force='mesh')]),
    ('lower head (shell, jaw support, face)', '#c8b89a', 0.12, lambda: [load_tm(k) for k in ('head_bottom', 'jaw_support', 'face_panel')]),
    ('head yaw link + ID13 (q = 0)', '#b39ddb', 0.25, lambda: [load_tm(k) for k in ('head_yaw_link', 'motor13')]),
    ('Pi + header housings', '#4caf50', 0.35, lambda: [load_tm('pi')] + [load_tm(f'head_pi_gpio_pin_{p:02d}_receiving') for p in (1, 2, 3, 5, 6, 8, 9, 10)]),
    ('speaker, retainer, amplifier', '#ff9800', 0.40, lambda: [tm_from_man(audio_solid(k)) for k in ('speaker', 'speaker_retainer', 'amplifier', 'amp_housings')]),
    ('audio Pi-end housings + jumpers', '#1e88e5', 0.45, lambda: [tm_from_man(audio_solid(k)) for k in ('pi_housing_pin04', 'pi_housing_pin12', 'pi_housing_pin35', 'pi_housing_pin40')]
     + [tm_from_man(pin34_housing())] + [tm_from_man(M) for k, M in audio_wire_tubes().items() if k != 'audio_wire_amp_gnd_pin14']),
    ('A3 clips', '#000000', 0.8, lambda: [trimesh.load(L.SOL / f'{k}-world.stl', force='mesh') for k in ('A3_clip_head', 'A3_clip_cap')]),
    ('A3 bundle (group r 1.7, fan r 0.65)', '#e53935', 0.75, lambda: [trimesh.load(L.SOL / f'{k}-world.stl', force='mesh') for k in ('A3_group_in_head', 'A3_fan_wires')]),
]
VIEWS = {'side': ((0, 2), 'x (mm, forward)', 'z (mm)', 'Side view from -y'),
         'rear': ((1, 2), 'y (mm, left)', 'z (mm)', 'Rear view from -x'),
         'top': ((0, 1), 'x (mm, forward)', 'y (mm, left)', 'Top view')}


def polys(meshes, ax2, box=None):
    out = []
    for m in meshes:
        T = m.vertices[m.faces][:, :, list(ax2)]
        if box is not None:
            c = T.mean(1)
            T = T[(c[:, 0] > box[0]) & (c[:, 0] < box[1]) & (c[:, 1] > box[2]) & (c[:, 1] < box[3])]
        out.append(T)
    return np.concatenate(out) if out else np.zeros((0, 3, 2))


def draw(ax, data, ax2, box=None, route=None):
    hs = []
    for (name, col, a, _), meshes in zip(GROUPS, data):
        P = polys(meshes, ax2, box)
        ax.add_collection(PolyCollection(P, facecolors=col, edgecolors='none', alpha=a))
        hs.append(Patch(color=col, alpha=min(1, a + 0.3), label=name))
    if route is not None:
        ax.plot(route[:, ax2[0]], route[:, ax2[1]], color='#b71c1c', lw=1.0, ls='--')
    ax.set_aspect('equal')
    ax.autoscale()
    ax.grid(alpha=0.3)
    return hs


def main():
    r = json.loads((L.STUDY / 'route-A3.json').read_text())
    route = np.array(r['groupPolyline'], float)
    data = [f() for *_, f in GROUPS]
    clips = r['clips']
    for v, (ax2, xl, yl, title) in VIEWS.items():
        fig, ax = plt.subplots(figsize=(13, 8))
        hs = draw(ax, data, ax2, route=route)
        for k, c in clips.items():
            h = np.array(c['hook'])
            ax.annotate(f"{k} ({c['screw']})", (h[ax2[0]], h[ax2[1]]), xytext=(10, 14), textcoords='offset points',
                        fontsize=8, arrowprops=dict(arrowstyle='-', lw=0.6))
        g = np.array(r['fanPoint'])
        ax.annotate('gather point, fan to pins 1-10', (g[ax2[0]], g[ax2[1]]), xytext=(10, -18), textcoords='offset points',
                    fontsize=8, arrowprops=dict(arrowstyle='-', lw=0.6))
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.set_title(f'{title}: integrated head (cap + audio + Pi rails A) with neck-bundle route A3 (dashed = centreline)', fontsize=10)
        ax.legend(handles=hs, fontsize=7, loc='lower left', framealpha=0.9)
        fig.tight_layout()
        fig.savefig(OUT / f'integrated-{v}.png', dpi=130)
        plt.close(fig)
    # close-up of the fan: rear view of the header front (x > 70)
    fig, axs = plt.subplots(1, 2, figsize=(14, 7))
    for ax, (ax2, xl, yl, t), box in ((axs[0], VIEWS['rear'], (5, 32, 106, 126)), (axs[1], VIEWS['top'], (66, 84, 5, 32))):
        keep = [[m.slice_plane([70, 0, 0], [1, 0, 0]) if m.bounds[1][0] > 70 else None for m in ms] for ms in data]
        keep = [[m for m in ms if m is not None and len(m.faces)] for ms in keep]
        hs = draw(ax, keep, ax2, box=box)
        ax.set_xlim(box[0], box[1])
        ax.set_ylim(box[2], box[3])
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.set_title(t + ' of everything in front of x 70 (header front)', fontsize=9)
    axs[0].legend(handles=hs, fontsize=7, loc='upper left', framealpha=0.9)
    fig.suptitle('Fan of the 8 bundle wires (red) beside the audio jumpers on pins 4 and 12 (blue)', fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / 'fan-closeup.png', dpi=130)
    plt.close(fig)
    print('written', sorted(p.name for p in OUT.glob('*.png')))


if __name__ == '__main__':
    main()
