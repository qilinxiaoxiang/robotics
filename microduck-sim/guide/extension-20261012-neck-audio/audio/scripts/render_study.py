#!/usr/bin/env python3
"""Section drawings and views of the recommended audio study. Writes ../png/study-*.png."""
from __future__ import annotations

import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh

from check_lib import ROLL_P, YAW, rot
from scene import HEAD_KEYS_FIXED, STUDY, load_tm, manifest, pi_group_keys

S = STUDY / 'study-solids'
PNG = STUDY / 'png'
STUDY_COL = {'head_cap_extension': '#d97706', 'speaker': '#2563eb', 'speaker_retainer': '#059669',
             'amplifier': '#7c3aed', 'amp_housings': '#dc2626', 'pi_housing_pin04': '#dc2626',
             'pi_housing_pin12': '#dc2626', 'pi_housing_pin14': '#dc2626', 'pi_housing_pin35': '#dc2626',
             'pi_housing_pin40': '#dc2626', 'speaker_screws_envelope': '#111827', 'amp_screws_envelope': '#111827',
             'speaker_leads_envelope': '#0ea5e9'}


def section(ax, m, o, nrm, axes, color, lw):
    s = m.section(plane_origin=o, plane_normal=nrm)
    if s is None:
        return
    for e in s.entities:
        p = s.vertices[e.points]
        ax.plot(p[:, axes[0]], p[:, axes[1]], color=color, lw=lw)


def main():
    man = manifest()
    base = {k: load_tm(k) for k in HEAD_KEYS_FIXED + ['jaw_frame'] + pi_group_keys(man) if k not in ('neck_pitch',)}
    swept = []
    for k in YAW:
        for a in (-25, 25):
            T = np.eye(4)
            T[:3, :] = rot([-1, 0, 0], a, ROLL_P)
            swept.append(load_tm(k).apply_transform(T))
    study = {k: trimesh.load(S / f'{k}-world.stl', force='mesh') for k in STUDY_COL}
    wires = json.loads((STUDY / 'wire-routes.json').read_text())
    views = [('y', 0.0, 'side section y = 0: speaker under the rear roof, amplifier, housings, Pi'),
             ('y', -7.62, 'side section y = -7.62 (LRC housing row)'),
             ('x', 3.0, 'cross section x = 3 through the speaker, collar and retainer bosses'),
             ('x', 24.79, 'cross section x = 24.79 through the amplifier posts'),
             ('z', 141.0, 'plan section z = 141')]
    for ax_name, val, title in views:
        i = 'xyz'.index(ax_name)
        nrm = np.eye(3)[i]
        o = nrm * val
        axes = [j for j in range(3) if j != i]
        fig, ax = plt.subplots(figsize=(11, 6.5))
        for k, m in base.items():
            section(ax, m, o, nrm, axes, '#9ca3af', 0.6)
        for m in swept:
            section(ax, m, o, nrm, axes, '#cbd5e1', 0.5)
        for k, m in study.items():
            section(ax, m, o, nrm, axes, STUDY_COL[k], 1.3)
        for name, p in wires.items():
            p = np.asarray(p)
            ax.plot(p[:, axes[0]], p[:, axes[1]], ls=':', lw=0.9, color='#be185d' if name.startswith('amp') else '#0ea5e9')
        ax.set_aspect('equal')
        ax.grid(True, lw=0.3)
        ax.set_xlabel('xyz'[axes[0]] + ' mm')
        ax.set_ylabel('xyz'[axes[1]] + ' mm')
        ax.set_title(title + '\norange study cap, blue speaker, green retainer, purple amp, red housings, black screws, '
                     'grey V1.8 parts, light grey yaw body at roll +-25 deg, dotted wires (projected)', fontsize=8)
        fig.tight_layout()
        fig.savefig(PNG / f'study-section-{ax_name}{val:+.0f}.png', dpi=110)
        plt.close(fig)
    # exterior: the cap from above with the grille, and from the rear-left
    cap = study['head_cap_extension']
    G = json.loads((STUDY / 'study-build.json').read_text())['grille']
    for name, elev, azim in (('top', 90, -90), ('rear-left', 35, 150)):
        fig = plt.figure(figsize=(9, 7))
        ax = fig.add_subplot(111, projection='3d')
        mm = cap.simplify_quadric_decimation(face_count=60000) if len(cap.faces) > 60000 else cap
        pc = Poly3DCollection(mm.triangles, facecolor='#f59e0b', edgecolor='none', alpha=1.0)
        light = np.array([0.3, -0.4, 0.86])
        nrm = mm.face_normals
        shade = 0.45 + 0.55 * np.clip(nrm @ light / np.linalg.norm(light), 0, 1)
        pc.set_facecolor(np.c_[0.96 * shade, 0.62 * shade, 0.04 * shade + 0.02, np.ones(len(shade))])
        ax.add_collection3d(pc)
        b = cap.bounds
        ax.set_xlim(b[0][0], b[1][0]); ax.set_ylim(-63, 63); ax.set_zlim(b[0][2] - 20, b[1][2] + 20)
        ax.set_box_aspect((b[1][0] - b[0][0], 126, b[1][2] - b[0][2] + 40))
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        ax.set_title(f'Study cap exterior ({name}): {G["holes"]} x Ø{G["holeDiameterMm"]} grille over the speaker; nothing else changes outside', fontsize=9)
        fig.tight_layout()
        fig.savefig(PNG / f'study-exterior-{name}.png', dpi=110)
        plt.close(fig)
    print('rendered')


if __name__ == '__main__':
    main()
