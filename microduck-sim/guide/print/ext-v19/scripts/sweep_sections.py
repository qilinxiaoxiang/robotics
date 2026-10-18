#!/usr/bin/env python3
"""Swept free-space sections at the clip sites (design aid; scratch PNG/NPZ).

Site frame: origin at the screw seat point, n = outward normal (= -screw axis), e1/e2 from ext_lib.frame. Each part
near the site is moved into the site body's frame at every pose of its own relevant joints (MJCF FK), transformed so
that n becomes z, and sliced with manifold3d at heights n = 0.25 .. 9 mm; the union over poses is the space that part
can occupy relative to the site. Joints per part body relative to the site body are decomposed so each body only
sweeps the joints between it and the site (no product explosion). Cap descent (0..40 mm) for the head sites.
Usage: sweep_sections.py site [cap_stl]
"""
import itertools
import os
import sys

import manifold3d as m3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import ext_lib as E
from nr_lib import FK, body_of

D2R = np.radians
F = E.fasteners()
SITES = {'torso': 'S12-horn-025', 'bracket': 'S11-horn-040', 'head': 'H-jaw_support-03', 'cap': 'E-pi-04'}
SITE_BODY = {'torso': 'trunk_base', 'bracket': 'neck_pitch', 'head': 'jaw_soft', 'cap': 'jaw_soft'}
CHAIN = ['trunk_base', 'neck', 'neck_pitch', 'yaw_roll_motion', 'jaw_soft', 'jaw']
JOINT_BETWEEN = {('trunk_base', 'neck'): 'neck_pitch', ('neck', 'neck_pitch'): 'head_pitch',
                 ('neck_pitch', 'yaw_roll_motion'): 'head_yaw', ('yaw_roll_motion', 'jaw_soft'): 'head_roll',
                 ('jaw_soft', 'jaw'): 'jaw'}
GRID = {'neck_pitch': np.arange(-90, 61, 7.5), 'head_pitch': np.arange(-90, 91, 7.5), 'head_yaw': np.arange(-170, 171, 10),
        'head_roll': np.arange(-25, 25.1, 2.5), 'jaw': np.arange(0, 40.1, 4)}
GRID_MULTI = {'head_roll': np.arange(-25, 25.1, 5), 'jaw': np.array([0, 20, 40]), 'head_pitch': np.arange(-90, 91, 15)}
LEVELS = [float(x) for x in os.environ.get('SWEEP_LEVELS', '0.25,1.0,1.75,2.5,3.5,4.5,5.5,6.5,7.5,8.5').split(',')]
PERPART = bool(os.environ.get('SWEEP_PERPART'))   # also keep per-part section polygons (key 'h:part')
TAG = os.environ.get('SWEEP_TAG', '')
CAP_GROUP = lambda k: k == 'head_cap' or k == 'pi' or k.startswith('head_pi_') or k.startswith('audio:')
AT_CAP_ON = {'head_bottom', 'face_panel', 'eye_trim', 'camera_board', 'motor13', 'motor14', 'motor15', 'jaw_support',
             'mouth_sliding_ring', 'jaw_frame', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b',
             'neck_pitch_ring', 'neck_pitch'}


def joints_between(a, b):
    i, j = CHAIN.index(a), CHAIN.index(b)
    lo, hi = min(i, j), max(i, j)
    return [JOINT_BETWEEN[(CHAIN[k], CHAIN[k + 1])] for k in range(lo, hi)]


def main():
    site = sys.argv[1]
    cap_stl = sys.argv[2] if len(sys.argv) > 2 else str(E.STUDY_CAP)
    r = F[SITES[site]]
    c, ax = np.array(r['center']), np.array(r['axis'])
    nrm = -ax / np.linalg.norm(ax)
    u, v, _ = E.frame(nrm)
    S = np.eye(4)
    S[:3, :3] = np.c_[u, v, nrm].T
    S[:3, 3] = -S[:3, :3] @ c                      # world -> site frame (e1, e2, n)
    sb = SITE_BODY[site]
    man = E.ia_lib.manifest()
    keys = [k for k, m in man.items()
            if np.linalg.norm(np.maximum(0, np.maximum(np.array(m['bounds'])[0] - c, c - np.array(m['bounds'])[1]))) < 40]
    if site in ('head', 'cap') and 'head_cap' not in keys:
        keys.append('head_cap')
    AUD = ['speaker', 'amplifier', 'amp_housings', 'amp_screws_envelope', 'speaker_screws_envelope', 'speaker_leads_envelope',
           'pi_housing_pin04', 'pi_housing_pin12', 'pi_housing_pin14', 'pi_housing_pin35', 'pi_housing_pin40']
    if site in ('head', 'cap'):
        keys += ['audio:' + a for a in AUD] + ['audio:speaker_retainer_v19']
        if (E.OUT / 'resistor_envelope_v19-world.stl').exists():
            keys.append('audio:resistor_envelope_v19')
    fk = FK()
    out = {h: {'static': m3.CrossSection(), 'moving': m3.CrossSection()} for h in LEVELS}
    who = {}
    pp = {}
    for k in keys:
        b = 'jaw_soft' if k.startswith('audio:') else (body_of(k) or 'trunk_base')
        if k == 'jaw_frame':
            b = 'jaw'
        if k.startswith('audio:'):
            a = k.split(':', 1)[1]
            src = E.OUT / f'{a}-world.stl' if a.endswith('_v19') else E.AUDIO / 'study-solids' / f'{a}-world.stl'
            M = E.stl_man(src)
        else:
            M = E.stl_man(cap_stl) if k == 'head_cap' else E.load_man(k)
        tfs, dest = None, 'moving'
        if site == 'head' and CAP_GROUP(k):
            tfs = [np.eye(4)] + [np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, dz], [0, 0, 0, 1.0]]) for dz in np.arange(2, 40.1, 2)]
        elif site == 'cap' and k in AT_CAP_ON and b in ('jaw_soft',):
            tfs = [np.eye(4)] + [np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, -dz], [0, 0, 0, 1.0]]) for dz in np.arange(2, 40.1, 2)]
        elif b == sb:
            tfs, dest = [np.eye(4)], 'static'
        if tfs is None:
            js = joints_between(sb, b)
            grids = [GRID[j] if len(js) == 1 else GRID_MULTI.get(j, GRID[j]) for j in js]
            tfs = []
            for vals in itertools.product(*grids):
                q = dict(neck_pitch=0.0, head_pitch=0.0, head_yaw=0.0, head_roll=0.0, jaw=0.0)
                for j, a in zip(js, vals):
                    q[j] = D2R(a) if j != 'jaw' else float(a)
                T = fk.part_T(q)
                tfs.append(np.linalg.inv(T[sb]) @ T[b])
        hits = 0
        for T in tfs:
            Ms = M.transform((S @ T)[:3, :])
            bb = E.bbox(Ms)
            if np.any(bb[0][:2] > 25) or np.any(bb[1][:2] < -25) or bb[1][2] < 0 or bb[0][2] > max(LEVELS) + 0.5:
                continue
            for h in LEVELS:
                if bb[0][2] <= h <= bb[1][2]:
                    cs = Ms.slice(h)
                    if not cs.is_empty():
                        out[h][dest] = out[h][dest] + cs
                        if PERPART:
                            pp.setdefault(f'{h}:{k}', m3.CrossSection())
                            pp[f'{h}:{k}'] = pp[f'{h}:{k}'] + cs
                        hits += 1
        if hits:
            who[k] = (dest, hits, len(tfs))
        print(k, b, dest, hits, len(tfs), flush=True)
    for sid, s in F.items():
        if s.get('center') is not None and np.linalg.norm(np.array(s['center']) - c) < 25:
            Ms = E.screw_solid(s['center'], s['axis'], s['lengthMm'], d=s['diameterMm'], head_d=s['headDiameterMm'],
                               head_h=s['headHeightMm']).transform(S[:3, :])
            for h in LEVELS:
                cs = Ms.slice(h)
                if not cs.is_empty():
                    out[h]['static'] = out[h]['static'] + cs
    polys = {}
    for h in LEVELS:
        for dest in ('moving', 'static'):
            polys[f'{h}:{dest}'] = [np.asarray(p).tolist() for p in out[h][dest].to_polygons()]
    for key, cs in pp.items():
        polys['part:' + key] = [np.asarray(p).tolist() for p in cs.to_polygons()]
    ncol = 5
    nrow = (len(LEVELS) + ncol - 1) // ncol
    fig, axs = plt.subplots(nrow, ncol, figsize=(6 * ncol, 6.25 * nrow), squeeze=False)
    for axp, h in zip(axs.ravel(), LEVELS):
        for dest, col in (('moving', (0.4, 0.6, 1.0)), ('static', (0.3, 0.3, 0.3))):
            for p in polys[f'{h}:{dest}']:
                p = np.asarray(p)
                axp.fill(p[:, 0], p[:, 1], color=col, alpha=0.55 if dest == 'moving' else 0.8, lw=0)
        for sid, s in F.items():
            if s.get('center') is not None and np.linalg.norm(np.array(s['center']) - c) < 25:
                q = (S[:3, :3] @ np.array(s['center']) + S[:3, 3])
                axp.plot(q[0], q[1], 'r+')
                axp.text(q[0], q[1], sid.split('-', 1)[1], fontsize=6, color='red')
        axp.set_aspect('equal')
        axp.set_xlim(-22, 22)
        axp.set_ylim(-22, 22)
        axp.grid(alpha=0.3)
        axp.set_title(f'{site} n={h}; e1={np.round(u, 2)} e2={np.round(v, 2)}', fontsize=8)
    fig.tight_layout()
    fig.savefig(E.SCRATCH / f'sweep-{site}{TAG}.png', dpi=60)
    E.jdump({'site': site, 'origin': c, 'e1': u, 'e2': v, 'n': nrm, 'levels': LEVELS, 'polygons': polys,
             'who': {k: list(v) for k, v in who.items()}}, E.SCRATCH / f'sweep-{site}{TAG}.json')
    print(who)


if __name__ == '__main__':
    main()
