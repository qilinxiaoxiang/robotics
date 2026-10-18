#!/usr/bin/env python3
"""Exploration: sections through the four clip screws (parts within 20 mm, screw heads from fasteners.json).
Writes SCRATCH/sites-<id>.png and SCRATCH/sites.json (nearby part distances to the screw seat)."""
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh

import ext_lib as E

SITES = {'S12-horn-025': None, 'S11-horn-040': None, 'H-jaw_support-03': None, 'E-pi-04': None}
CAP = sys.argv[1] if len(sys.argv) > 1 else None


def main():
    F = E.fasteners()
    man = E.ia_lib.manifest()
    out = {}
    for sid in SITES:
        r = F[sid]
        c, ax = np.array(r['center']), np.array(r['axis'])
        u, v, a = E.frame(ax)
        keys = []
        for k, m in man.items():
            b = np.array(m['bounds'])
            d = np.maximum(0, np.maximum(b[0] - c, c - b[1]))
            if np.linalg.norm(d) < 20:
                keys.append(k)
        meshes = {}
        for k in keys:
            if k == 'head_cap' and CAP:
                meshes[k] = trimesh.load(CAP, force='mesh')
            else:
                vv, ff = E.ia_lib.load_solid(k)
                meshes[k] = trimesh.Trimesh(vv, ff, process=False)
        # nearby screws as solids
        for sid2, r2 in F.items():
            if r2.get('center') is None:
                continue
            if np.linalg.norm(np.array(r2['center']) - c) < 20:
                meshes['screw:' + sid2] = E.tm(E.screw_solid(r2['center'], r2['axis'], r2['lengthMm'],
                                                              d=r2['diameterMm'], head_d=r2['headDiameterMm'],
                                                              head_h=r2['headHeightMm']))
        dist = {}
        for k, m in meshes.items():
            dist[k] = round(float(trimesh.proximity.closest_point(m, [c])[1][0]), 2)
        out[sid] = {'center': c, 'axis': ax, 'u': u, 'v': v, 'nearby': dict(sorted(dist.items(), key=lambda kv: kv[1]))}
        # sections: plane normal = axis at offsets (outside the seat: -0.5, -1.5, -3 mm), plane normal = u, plane normal = v
        planes = [('axis -1.0 (tab)', a, c - 1.0 * a, (u, v)), ('axis -3.0 (above head)', a, c - 3.0 * a, (u, v)),
                  ('plane u', u, c, (v, a)), ('plane v', v, c, (u, a))]
        fig, axs = plt.subplots(2, 2, figsize=(14, 14))
        cols = plt.cm.tab20(np.linspace(0, 1, max(2, len(meshes))))
        for axp, (title, n, o, (e1, e2)) in zip(axs.ravel(), planes):
            for (k, m), col in zip(meshes.items(), cols):
                try:
                    s = m.section(plane_origin=o, plane_normal=n)
                except Exception:
                    s = None
                if s is None:
                    continue
                for seg in s.discrete:
                    P = (seg - o) @ np.c_[e1, e2]
                    axp.plot(P[:, 0], P[:, 1], color=col, lw=1.2 if not k.startswith('screw') else 0.8,
                             ls='-' if not k.startswith('screw') else '--')
                axp.plot([], [], color=col, label=k)
            axp.set_aspect('equal')
            axp.set_xlim(-20, 20)
            axp.set_ylim(-20, 20)
            axp.grid(alpha=0.3)
            axp.set_title(f'{sid} {title}: e1={np.round(e1, 2)}, e2={np.round(e2, 2)}', fontsize=8)
        axs[0, 0].legend(fontsize=6, loc='upper left')
        fig.tight_layout()
        fig.savefig(E.SCRATCH / f'sites-{sid}.png', dpi=80)
        plt.close(fig)
        print(sid, out[sid]['nearby'])
    E.jdump(E.rnd(out, 3), E.SCRATCH / 'sites.json')


if __name__ == '__main__':
    main()
