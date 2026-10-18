#!/usr/bin/env python3
"""What surrounds the V1.8 Pi rails: exact gaps from each rail to every neighbour (static, head-roll and jaw sweeps),
and section drawings of the free space around the rails (all head solids, the yaw body swept through head roll
+-25 deg and the jaw through 0..40 deg in 2.5 deg steps, the Pi group with its 13 receiving housings, the cable
centrelines as tubes, and the recommended audio layout). Writes ../neighbourhood.json and ../png/nb-*.png.
"""
from __future__ import annotations

import json

import manifold3d as m3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from pm_lib import (CAP_V18, FIXED, JAW_PIVOT, ROLL_P, SCREWS, SIM, STUDY, YAW, AUDIO_SOLIDS, Head, audio_solid,
                    audio_wire_tubes, box, cable_clearance, cyl, corridor_keepouts, j, load_stl_man, rot)


def rails(cap):
    out = {}
    for name, sgn in (('minus_y_rail', -1), ('plus_y_rail', 1)):
        lo = [49.0, 25.4 if sgn > 0 else -32.4, 114.0]
        hi = [61.0, 32.4 if sgn > 0 else -25.4, 145.0]
        out[name] = cap ^ box(lo, hi)
    return out


def obstacles(H):
    ob = {}
    for k in FIXED + H.pi:
        if k != 'head_cap':
            ob[k] = H.get(k)
    for k in YAW:
        ob[k + '@roll'] = m3.Manifold.batch_boolean([H.get(k).transform(rot([-1, 0, 0], float(a), ROLL_P))
                                                     for a in np.arange(-25, 25.01, 2.5)], m3.OpType.Add)
    ob['jaw_frame@0..40'] = m3.Manifold.batch_boolean([H.get('jaw_frame').transform(rot([0, 1, 0], float(a), JAW_PIVOT))
                                                       for a in np.arange(0, 40.01, 2.5)], m3.OpType.Add)
    routes = json.loads((SIM / 'guide/content/routes.json').read_text())['routes']
    for cid, r in (('head_csi', 4.0), ('bundle_head', 3.0)):
        p = np.asarray(routes[cid], float)
        segs = [cyl(a, b - a, float(np.linalg.norm(b - a)), r, 24) + m3.Manifold.sphere(r, 24).translate(a.tolist())
                for a, b in zip(p[:-1], p[1:])]
        ob['cable_' + cid] = m3.Manifold.batch_boolean(segs, m3.OpType.Add)
    for k in AUDIO_SOLIDS:
        ob['audio_' + k] = audio_solid(k)
    ob.update(audio_wire_tubes())
    return ob


def draw(ax, M, normal, offset, axes, **kw):
    """Section of a manifold by the plane normal . p = offset (normal is a unit axis)."""
    i = int(np.argmax(np.abs(normal)))
    if i == 2:
        cs = M.slice(offset)
        polys = cs.to_polygons()
        for P in polys:
            P = np.vstack([P, P[:1]])
            ax.plot(P[:, 0], P[:, 1], **kw)
        return
    # rotate so the requested axis becomes z
    if i == 1:
        T = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0.0]])[:3]   # (x, z, y)
    else:
        T = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0.0]])[:3]   # (y, z, x)
    cs = M.transform(T).slice(offset)
    for P in cs.to_polygons():
        P = np.vstack([P, P[:1]])
        ax.plot(P[:, 0], P[:, 1], **kw)


def main():
    H = Head()
    cap = load_stl_man(CAP_V18)
    R = rails(cap)
    ob = obstacles(H)
    res = {'rails': {}}
    for name, M in R.items():
        rows = []
        for k, O in ob.items():
            b0, b1 = np.array(M.bounding_box()).reshape(2, 3), np.array(O.bounding_box()).reshape(2, 3)
            if np.any(b0[0] - 10 > b1[1]) or np.any(b1[0] - 10 > b0[1]):
                continue
            g = float(M.min_gap(O, 10))
            if g < 10:
                rows.append({'with': k, 'gapMm': round(g, 2), 'overlapMm3': round((M ^ O).volume(), 3)})
        rows.sort(key=lambda r: r['gapMm'])
        res['rails'][name] = {'boundsMm': np.round(np.array(M.bounding_box()).reshape(2, 3), 2), 'volumeMm3': round(M.volume(), 1),
                              'neighbours': rows[:14]}
        print(name, rows[:10])
    # free-space sections
    union = m3.Manifold.batch_boolean(list(ob.values()), m3.OpType.Add)
    keep = corridor_keepouts()
    for side, sgn in (('minus_y', -1), ('plus_y', 1)):
        fig, axs = plt.subplots(2, 3, figsize=(15, 9.5))
        for a, z in zip(axs[0], (120.0, 130.0, 140.0)):
            draw(a, cap, [0, 0, 1], z, None, color='#d97706', lw=1.0)
            draw(a, union, [0, 0, 1], z, None, color='#64748b', lw=0.6)
            for kk, K in keep.items():
                draw(a, K, [0, 0, 1], z, None, color='#16a34a', lw=0.8, ls='--')
            for sid, c in SCREWS.items():
                if np.sign(c[1]) == sgn:
                    a.plot(c[0], c[1], 'kx')
            a.set_xlim(36, 66); a.set_ylim(sorted((sgn * 18, sgn * 42))); a.set_aspect('equal'); a.grid(lw=0.3)
            a.set_title(f'plan z = {z:.0f}', fontsize=8); a.set_xlabel('x'); a.set_ylabel('y')
        for a, y in zip(axs[1], (sgn * 29.0, sgn * 31.5, sgn * 34.0)):
            draw(a, cap, [0, 1, 0], y, None, color='#d97706', lw=1.0)
            draw(a, union, [0, 1, 0], y, None, color='#64748b', lw=0.6)
            for sid, c in SCREWS.items():
                if np.sign(c[1]) == sgn:
                    a.plot(c[0], c[2], 'kx')
            a.set_xlim(36, 66); a.set_ylim(108, 155); a.set_aspect('equal'); a.grid(lw=0.3)
            a.set_title(f'side section y = {y:+.1f}', fontsize=8); a.set_xlabel('x'); a.set_ylabel('z')
        fig.suptitle(f'V1.8 Pi rail ({side}): orange cap, grey = every neighbour incl. yaw body over roll +-25, jaw 0..40, '
                     'Pi group + 13 housings, cable tubes, audio layout; green dashed = neck-route keep-outs', fontsize=9)
        fig.tight_layout(); fig.savefig(STUDY / f'png/nb-{side}.png', dpi=105); plt.close(fig)
    (STUDY / 'neighbourhood.json').write_text(json.dumps(j(res), indent=1))


if __name__ == '__main__':
    main()
