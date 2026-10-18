#!/usr/bin/env python3
"""Occupancy columns at the clip sites (design aid; scratch output SCRATCH/occ-<site>.npz and .png).

Grid in the seat plane (e1, e2 in -22..22 mm, 0.25 mm), rays along -n from n = 20 mm (n = outward normal = -screw
axis). Every crossing interval of every solid is recorded as occupied: static parts of the site body as they are;
parts of other bodies at every sampled pose (MJCF FK, same pose grids as site_maps.py); for the head sites the cap
descent (0..40 mm, 1 mm steps) as relative motion between the cap group (cap, Pi + Pi parts) and the lower head.
Screw solids (head + shank, fasteners.json) count as static. Output: per n level (0..9 mm, 0.25 mm) a boolean image
'static' and 'moving'.
Usage: site_occ.py site [cap_stl]
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
STEP, HALF, NTOP = 0.25, 22.0, 20.0
LEVELS = np.arange(0.0, 9.01, 0.25)
RADIUS = 45.0


def poses(site):
    if site == 'torso':
        return [dict(neck_pitch=D2R(n), head_pitch=D2R(h), head_yaw=D2R(y), head_roll=0.0, jaw=j)
                for n, h, y, j in itertools.product(np.arange(-90, 61, 10), (-90, 0, 90), (0,), (0, 40))]
    if site == 'bracket':
        return [dict(neck_pitch=0.0, head_pitch=D2R(h), head_yaw=D2R(y), head_roll=D2R(r), jaw=j)
                for h, y, r, j in itertools.product(np.arange(-90, 91, 10), np.arange(-170, 171, 20), (-25, 0, 25), (0,))]
    return [dict(neck_pitch=0.0, head_pitch=0.0, head_yaw=0.0, head_roll=D2R(r), jaw=j)
            for r, j in itertools.product(np.arange(-25, 25.1, 2.5), np.arange(0, 40.1, 2.5))]


def intervals(m, O, d):
    """Occupied ray intervals [t0, t1] along O + t d for a closed mesh (pairs of sorted hits)."""
    loc, ir, _ = m.ray.intersects_location(O, np.repeat(d[None], len(O), 0), multiple_hits=True)
    out = {}
    if len(loc) == 0:
        return out
    t = np.einsum('ij,j->i', loc - O[ir], d)
    order = np.lexsort((t, ir))
    ir, t = ir[order], t[order]
    for k in np.unique(ir):
        tt = t[ir == k]
        tt = tt[np.concatenate([[True], np.diff(tt) > 1e-6])]
        if len(tt) % 2 == 1:
            tt = tt[:-1]
        out[int(k)] = tt.reshape(-1, 2)
    return out


def main():
    site = sys.argv[1]
    cap_stl = sys.argv[2] if len(sys.argv) > 2 else str(E.STUDY_CAP)
    r = F[SITES[site]]
    c, ax = np.array(r['center']), np.array(r['axis'])
    nrm = -ax / np.linalg.norm(ax)
    u, v, _ = E.frame(nrm)
    sb = SITE_BODY[site]
    g = np.arange(-HALF, HALF + 1e-9, STEP)
    G1, G2 = np.meshgrid(g, g, indexing='ij')
    O = c + G1.ravel()[:, None] * u + G2.ravel()[:, None] * v + NTOP * nrm
    d = -nrm
    nl = len(LEVELS)
    static = np.zeros((nl, len(g), len(g)), bool)
    moving = np.zeros_like(static)
    who = {}
    man = E.ia_lib.manifest()
    keys = [k for k, m in man.items()
            if np.linalg.norm(np.maximum(0, np.maximum(np.array(m['bounds'])[0] - c, c - np.array(m['bounds'])[1]))) < RADIUS]
    if site in ('head', 'cap') and 'head_cap' not in keys:
        keys.append('head_cap')
    fk = FK()
    P = poses(site)
    Ts = [fk.part_T(q) for q in P]
    cap_group = lambda k: k == 'head_cap' or k == 'pi' or k.startswith('head_pi_')

    def mark(arr, m, T):
        Ti = np.linalg.inv(T)
        O0 = O @ Ti[:3, :3].T + Ti[:3, 3]
        d0 = Ti[:3, :3] @ d
        # cull rays far from the mesh box
        lo, hi = m.bounds[0] - 1, m.bounds[1] + 1
        tt = np.linspace(0, NTOP + 1, 6)
        pts = O0[:, None, :] + tt[None, :, None] * d0
        near = np.any(np.all((pts > lo) & (pts < hi), axis=2), axis=1)
        if not near.any():
            return 0
        idx = np.flatnonzero(near)
        hit = 0
        res = {}
        for q in range(0, len(idx), 1500):
            for k, iv in intervals(m, O0[idx[q:q + 1500]], d0).items():
                res[k + q] = iv
        for k, iv in res.items():
            for t0, t1 in iv:
                n0, n1 = NTOP - t1, NTOP - t0          # occupied height range above the seat plane
                sel = (LEVELS >= n0) & (LEVELS <= n1)
                if sel.any():
                    i = idx[k]
                    arr[sel, i // len(g), i % len(g)] = True
                    hit += 1
        return hit

    for k in keys:
        if k == 'head_cap':
            m = trimesh.load(cap_stl, force='mesh')
        else:
            vv, ff = E.ia_lib.load_solid(k)
            m = trimesh.Trimesh(vv, ff, process=False)
        b = body_of(k) or ('jaw_soft' if k == 'head_cap' else 'trunk_base')
        if site == 'head' and cap_group(k):
            tfs = [np.eye(4)] + [np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, dz], [0, 0, 0, 1.0]]) for dz in np.arange(1, 40.1, 1.0)]
            dest = 'moving'
        elif site == 'cap' and b == 'jaw_soft' and not cap_group(k):
            tfs = [np.eye(4)] + [np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, -dz], [0, 0, 0, 1.0]]) for dz in np.arange(1, 40.1, 1.0)]
            dest = 'moving'
        elif b == sb:
            tfs, dest = [np.eye(4)], 'static'
        else:
            bb = 'jaw' if k == 'jaw_frame' else b
            tfs = [np.linalg.inv(T[sb]) @ T[bb] for T in Ts]
            dest = 'moving'
        tot = 0
        for T in tfs:
            tot += mark(static if dest == 'static' else moving, m, T)
        if tot:
            who[k] = (dest, tot)
        print(k, dest, tot, flush=True)
        del m
        import gc; gc.collect()
    for sid, s in F.items():
        if s.get('center') is not None and np.linalg.norm(np.array(s['center']) - c) < 30:
            m = E.tm(E.screw_solid(s['center'], s['axis'], s['lengthMm'], d=s['diameterMm'], head_d=s['headDiameterMm'],
                                   head_h=s['headHeightMm']))
            b = {'S12': 'trunk_base', 'S11': 'neck_pitch', 'H-j': 'jaw_soft', 'E-p': 'jaw_soft'}.get(sid[:3])
            mark(static, m, np.eye(4))
    np.savez_compressed(E.SCRATCH / f'occ-{site}.npz', static=static, moving=moving, levels=LEVELS, g=g, c=c, u=u, v=v, n=nrm)
    show = [0.25, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    fig, axs = plt.subplots(2, 4, figsize=(22, 11))
    ext = [-HALF, HALF, -HALF, HALF]
    for axp, h in zip(axs.ravel(), show):
        i = int(round(h / 0.25))
        img = np.ones(static.shape[1:] + (3,))
        img[moving[i]] = (0.55, 0.7, 1.0)
        img[static[i]] = (0.35, 0.35, 0.35)
        img[static[i] & moving[i]] = (0.1, 0.1, 0.4)
        axp.imshow(np.transpose(img, (1, 0, 2)), origin='lower', extent=ext)
        for sid, s in F.items():
            if s.get('center') is not None and np.linalg.norm(np.array(s['center']) - c) < 30:
                q = (np.array(s['center']) - c) @ np.c_[u, v]
                axp.plot(q[0], q[1], 'r+')
                axp.text(q[0], q[1], sid.split('-', 1)[1], fontsize=6, color='red')
        axp.set_title(f'{site} n = {h} mm; e1={np.round(u, 2)} e2={np.round(v, 2)}', fontsize=8)
        axp.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(E.SCRATCH / f'occ-{site}.png', dpi=70)
    print({k: v for k, v in who.items()})


if __name__ == '__main__':
    main()
