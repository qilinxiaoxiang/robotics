#!/usr/bin/env python3
"""Free-space maps at the four clip sites (design aid; scratch output).

For each site: section slices parallel to the mounting face at several heights n above the seat plane. Static parts
(same body as the site) are drawn grey; parts on other bodies are drawn in colour at every sampled pose (their union is
the space they can sweep relative to the site body); screw solids from fasteners.json are drawn red.
Poses: MJCF joints sampled over the full MJCF ranges (neck pitch -90..60, head pitch -90..90, head yaw -170..170, head
roll -25..25) on coarse grids, jaw 0..40; the cap descent (cap parts lifted 0..40 mm) for the head sites.
Usage: site_maps.py [site ...]   (torso bracket head cap)
"""
import itertools
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh

import ext_lib as E
from nr_lib import FK, body_of

D2R = np.radians
F = E.fasteners()
SITES = {'torso': 'S12-horn-025', 'bracket': 'S11-horn-040', 'head': 'H-jaw_support-03', 'cap': 'E-pi-04'}
SITE_BODY = {'torso': 'trunk_base', 'bracket': 'neck_pitch', 'head': 'jaw_soft', 'cap': 'jaw_soft'}
CAP_KEYS = ['head_cap', 'pi']


def mesh(k):
    if k == 'head_cap':
        return trimesh.load(E.STUDY_CAP, force='mesh')
    v, f = E.ia_lib.load_solid(k)
    return trimesh.Trimesh(v, f, process=False)


def poses(site):
    if site == 'torso':
        g = [dict(neck_pitch=D2R(n), head_pitch=D2R(h), head_yaw=0.0, head_roll=0.0, jaw=0.0)
             for n, h in itertools.product(np.arange(-90, 61, 10), np.arange(-90, 91, 30))]
    elif site == 'bracket':
        g = [dict(neck_pitch=0.0, head_pitch=D2R(h), head_yaw=D2R(y), head_roll=D2R(r), jaw=j)
             for h, y, r, j in itertools.product(np.arange(-90, 91, 15), np.arange(-170, 171, 20), (-25, 0, 25), (0, 40))]
    else:
        g = [dict(neck_pitch=0.0, head_pitch=0.0, head_yaw=0.0, head_roll=D2R(r), jaw=j)
             for r, j in itertools.product(np.arange(-25, 26, 5), np.arange(0, 41, 5))]
    return g


def main():
    sites = sys.argv[1:] or list(SITES)
    fk = FK()
    man = E.ia_lib.manifest()
    for site in sites:
        r = F[SITES[site]]
        c, ax = np.array(r['center']), np.array(r['axis'])
        nrm = -ax / np.linalg.norm(ax)
        u, v, _ = E.frame(nrm)
        sb = SITE_BODY[site]
        keys = []
        for k, m in man.items():
            b = np.array(m['bounds'])
            if np.linalg.norm(np.maximum(0, np.maximum(b[0] - c, c - b[1]))) < 60:
                keys.append(k)
        if site in ('head', 'cap') and 'head_cap' not in keys:
            keys.append('head_cap')
        meshes = {k: mesh(k) for k in keys}
        screws = {}
        for sid, s in F.items():
            if s.get('center') is not None and np.linalg.norm(np.array(s['center']) - c) < 30:
                screws[sid] = E.tm(E.screw_solid(s['center'], s['axis'], s['lengthMm'], d=s['diameterMm'],
                                                 head_d=s['headDiameterMm'], head_h=s['headHeightMm']))
        P = poses(site)
        Ts = [fk.part_T(q) for q in P]
        heights = [0.3, 1.0, 2.0, 3.5, 5.0, 6.5]
        fig, axs = plt.subplots(2, 3, figsize=(18, 12))
        for axp, h in zip(axs.ravel(), heights):
            o = c + h * nrm
            for k, m in meshes.items():
                b = body_of(k) or ('jaw_soft' if k == 'head_cap' else None)
                if b is None:
                    continue
                same = (b == sb) or (site == 'cap' and k in CAP_KEYS) or (site == 'head' and b == 'jaw_soft' and k not in CAP_KEYS)
                if same and not (site == 'head' and k in CAP_KEYS):
                    tf = [np.eye(4)]
                    col, lw = (0.3, 0.3, 0.3), 1.4
                elif site in ('head', 'cap') and (b == 'jaw_soft'):
                    # cap descent: cap parts move relative to the lower head (or the lower head relative to the cap)
                    sgn = 1 if site == 'head' else -1
                    tf = []
                    for dz in np.arange(0, 40.1, 2.0):
                        T = np.eye(4)
                        T[2, 3] = sgn * dz
                        tf.append(T)
                    col, lw = (0.95, 0.55, 0.1), 0.5
                else:
                    tf = []
                    for T in Ts:
                        Tr = np.linalg.inv(T[sb]) @ T[b if b != 'jaw_soft' or k != 'jaw_frame' else 'jaw']
                        tf.append(Tr)
                    col, lw = (0.15, 0.4, 0.9), 0.4
                    if k == 'jaw_frame':
                        col = (0.9, 0.7, 0.0)
                for T in tf:
                    # section of the moved mesh = section of the q0 mesh with the plane mapped back
                    Ti = np.linalg.inv(T)
                    o0 = Ti[:3, :3] @ o + Ti[:3, 3]
                    n0 = Ti[:3, :3] @ nrm
                    try:
                        s = m.section(plane_origin=o0, plane_normal=n0)
                    except Exception:
                        s = None
                    if s is None:
                        continue
                    for seg in s.discrete:
                        segw = seg @ T[:3, :3].T + T[:3, 3]
                        Q = (segw - o) @ np.c_[u, v]
                        axp.plot(Q[:, 0], Q[:, 1], color=col, lw=lw, alpha=0.8 if lw > 1 else 0.35)
            for sid, m in screws.items():
                s = m.section(plane_origin=o, plane_normal=nrm)
                if s is None:
                    continue
                for seg in s.discrete:
                    Q = (seg - o) @ np.c_[u, v]
                    axp.plot(Q[:, 0], Q[:, 1], color='red', lw=1.0)
                q = (np.array(F[sid]['center']) - c) @ np.c_[u, v]
                axp.text(q[0], q[1], sid.split('-', 1)[1], fontsize=6, color='red')
            axp.set_aspect('equal')
            axp.set_xlim(-22, 22)
            axp.set_ylim(-22, 22)
            axp.grid(alpha=0.3)
            axp.set_title(f'{site} {SITES[site]}  n = {h} mm above seat plane;  e1 = {np.round(u, 2)}, e2 = {np.round(v, 2)}',
                          fontsize=8)
        fig.tight_layout()
        fig.savefig(E.SCRATCH / f'map-{site}.png', dpi=75)
        plt.close(fig)
        print(site, 'done', len(P), 'poses', flush=True)


if __name__ == '__main__':
    main()
