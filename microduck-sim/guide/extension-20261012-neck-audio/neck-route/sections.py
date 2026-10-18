#!/usr/bin/env python3
"""Exact cross-sections of the candidate passages, in the head frame, at q = 0 and over head yaw and roll.

A section is a plane (axis = value) through a passage. Every solid near it is cut exactly with manifold3d (the solid is
rotated so the plane normal is z, then Manifold.slice). Existing cables crossing the plane are added as circles of the
guide radius where their centreline crosses it. The section is rasterised at 0.05 mm (even-odd point-in-polygon on the exact
outline) and a Euclidean distance transform gives the distance to material (resolution 0.05 mm); the free region
connected to the seed gives
  radius  = largest inscribed circle (the free-space radius of the passage at that section) and its centre,
  width   = twice the radius; the bounding parts are those with material within 0.125 mm of that circle.
Parts move with their MJCF bodies; sections are taken in the head frame (lower shell, jaw support, jaw servo, Pi fixed),
so only head yaw and head roll change them (neck pitch and head pitch move the whole head with the bracket below it,
which matters only for the floor sections, included through the bracket's yaw/roll relative motion).
Writes sections.json and SCRATCH/sec-<name>-<pose>.npz (for the figures).
"""
import sys
import time

import numpy as np
import manifold3d as m3
from scipy import ndimage
from matplotlib.path import Path as MPath

sys.path.insert(0, __import__('os').path.dirname(__file__))
from nr_lib import FK, HERE, SCRATCH, body_of, cable_tubes, ia_lib, jdump, load_solid, rnd  # noqa: E402

RES = 0.05
WIN = 9.0
# name: (axis, value, seed in the other two coordinates (order: x->(y,z), y->(x,z), z->(x,y)), label)
SECTIONS = {
    'gap-plus-y-z115': ('z', 115.0, (13.85, 12.65), 'servo-cable gap behind the jaw servo, +y side (yaw link | jaw servo), mid height'),
    'gap-plus-y-z127': ('z', 127.3, (13.85, 12.65), 'servo-cable gap behind the jaw servo, +y side, narrowest height'),
    'slot-minus-y-z129': ('z', 129.1, (16.9, -26.7), 'slot between yaw link and jaw support, -y side, narrowest height'),
    'slot-minus-y-z115': ('z', 115.0, (25.0, -26.7), 'slot between yaw link and jaw support, -y side, mid height'),
    'pi-top-plus-y-x61': ('x', 61.0, (23.25, 147.0), 'over the Pi top edge, +y (where the current route crosses)'),
    'pi-top-minus-y-x61': ('x', 61.0, (-20.7, 147.5), 'over the Pi top edge, -y'),
}
# Channel profiles: horizontal sections every few mm up the two passages (seed on the corridor centreline).
for _z in (104.0, 106.0, 108.0, 110.0, 112.0, 120.0, 124.0):
    SECTIONS[f'chan-minus-y-z{_z:g}'] = ('z', _z, (30.0, -26.8), f'-y channel (ID13 / yaw link | lower-shell collar, jaw support) at z {_z:g}')
for _z in (104.0, 108.0, 120.0):
    SECTIONS[f'gap-plus-y-z{_z:g}'] = ('z', _z, (14.0, 13.0), f'+y gap (yaw link, ID13 | jaw servo ID15, lower shell) at z {_z:g}')
ROLLS = [-25.0, -21.4, -15.0, -10.0, -5.0, 0.0, 5.0, 9.9, 15.0, 20.0, 25.0]
YAWS = [-170.0, -90.0, -24.6, 0.0, 34.0, 90.0, 170.0]
TO_Z = {'z': np.eye(3), 'x': np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0.]]), 'y': np.array([[1, 0, 0], [0, 0, 1], [0, 1, 0.]])}

fk = FK()
g = ia_lib.load_guide()
KEYS = [p['key'] for p in g['parts'] if body_of(p['key']) is not None and p['key'] != 'head_cap'] + ['head_cap_nonotch']
SOL = {}
for k in KEYS:
    v, f = load_solid(k)
    if v[:, 2].max() < 70:
        continue
    SOL[k] = (v, f, body_of(k.replace('_nonotch', '')))
CABLES = cable_tubes(0.1)


def rel_T(q):
    """Per body: transform from q = 0 robot frame to the head frame at pose q (head-fixed parts stay put)."""
    T = fk.part_T(q)
    Hinv = np.linalg.inv(T['jaw_soft'])
    return {b: Hinv @ T[b] for b in T}


def section(name, q, with_cables=True):
    axis, val, seed, _ = SECTIONS[name]
    R = TO_Z[axis]
    Tr = rel_T(q)
    seed = np.array(seed)
    lo2, hi2 = seed - WIN, seed + WIN
    n = int(round(2 * WIN / RES)) + 1
    gx = lo2[0] + RES * np.arange(n)
    gy = lo2[1] + RES * np.arange(n)
    G = np.stack(np.meshgrid(gx, gy, indexing='ij'), -1).reshape(-1, 2)
    lab_part = np.zeros(len(G), np.int16)
    names = ['free']
    for k, (v, f, b) in SOL.items():
        T = Tr[b]
        w = (v @ T[:3, :3].T + T[:3, 3]) @ R.T
        if w[:, 2].min() > val or w[:, 2].max() < val:
            continue
        if (w[:, :2].min(0) > hi2).any() or (w[:, :2].max(0) < lo2).any():
            continue
        polys = ia_lib.to_manifold(w, f).slice(float(val)).to_polygons()
        ins = np.zeros(len(G), bool)
        for poly in polys:
            poly = np.asarray(poly)
            if len(poly) < 3 or (poly.min(0) > hi2).any() or (poly.max(0) < lo2).any():
                continue
            ins ^= MPath(poly).contains_points(G)
        if ins.any():
            names.append(k)
            lab_part[ins & (lab_part == 0)] = len(names) - 1
    circles = []
    if with_cables:
        for cid, pts, r in CABLES:
            w = pts @ R.T                      # cables drawn in the q = 0 frame (treated as head-fixed: flexible, see README)
            sg = np.sign(w[:, 2] - val)
            for i in np.where(sg[:-1] * sg[1:] <= 0)[0]:
                t = (val - w[i, 2]) / (w[i + 1, 2] - w[i, 2] + 1e-12)
                c = w[i, :2] + t * (w[i + 1, :2] - w[i, :2])
                if (np.abs(c - seed) < WIN + r).all():
                    circles.append((cid, c, r))
                    names.append('cable:' + cid)
                    ins = np.linalg.norm(G - c, axis=1) < r
                    lab_part[ins & (lab_part == 0)] = len(names) - 1
    L = lab_part.reshape(n, n)
    free = L == 0
    D, (ii, jj) = ndimage.distance_transform_edt(free, sampling=RES, return_indices=True)
    D = D - RES / 2
    comp_lab, _ = ndimage.label(free)
    si = tuple(np.round((seed - lo2) / RES).astype(int))
    # the passage = the free component holding the widest free pixel within 3 mm of the seed (the seed itself may sit in
    # an existing cable)
    near = (np.linalg.norm(G - seed, axis=1) <= 3.0).reshape(n, n) & free
    if not near.any():
        return {'blocked': True, 'radiusMm': 0.0}, D, None
    kk = np.unravel_index(np.argmax(np.where(near, D, -1)), D.shape)
    comp = comp_lab[kk]
    Dm = np.where(comp_lab == comp, D, 0)
    k = np.unravel_index(np.argmax(Dm), Dm.shape)
    rmax = float(Dm[k])
    centre2 = lo2 + RES * np.array(k)
    # owners of the occupied pixels touching the inscribed circle
    rr = np.linalg.norm(G - centre2, axis=1)
    ring = (rr <= rmax + RES * 2.5) & (lab_part > 0)
    bound = sorted({names[i] for i in np.unique(lab_part[ring])})
    c3 = np.array([centre2[0], centre2[1], val])
    centre_world = c3 @ R
    touches_window = bool(((comp_lab == comp)[[0, -1], :]).any() or ((comp_lab == comp)[:, [0, -1]]).any())
    return {'radiusMm': rnd(rmax, 3), 'diameterMm': rnd(2 * rmax, 2), 'centreHeadFrame': rnd(centre_world, 2),
            'boundedBy': bound, 'cablesInSection': [c[0] for c in circles],
            'componentTouchesWindowEdge': touches_window}, D, (lo2, RES, comp_lab == comp, L, names)


WIRES = {'22AWG_silicone_1p7': 1.7, '26AWG_silicone_1p3': 1.3}
DUPONT_DIAG = 2.54 * np.sqrt(2)          # 1-pin Dupont housing, 2.54 mm square: passes a circle of this diameter


def capacity(D, comp, lo2, centre, half=8.0, margin=0.05):
    """How many round conductors of each diameter fit side by side in this section within +-half mm of the passage
    centre (greedy packing of non-overlapping circles on the distance raster, a lower bound), and whether a 1-pin Dupont
    housing (2.54 mm square, threaded end first) fits anywhere in it."""
    n = D.shape[0]
    gx = lo2[0] + RES * np.arange(n)
    gy = lo2[1] + RES * np.arange(n)
    X, Y = np.meshgrid(gx, gy, indexing='ij')
    near = (np.abs(X - centre[0]) <= half) & (np.abs(Y - centre[1]) <= half) & comp
    out = {}
    for name, d in WIRES.items():
        feas = near & (D >= d / 2 + margin)
        idx = np.argwhere(feas)
        order = np.argsort(D[feas])                 # walls first
        pts = np.stack([X[feas], Y[feas]], 1)[order]
        acc = []
        for q in pts:
            if all((q[0] - a[0]) ** 2 + (q[1] - a[1]) ** 2 >= (d + margin) ** 2 for a in acc[-60:]) and \
               all((q[0] - a[0]) ** 2 + (q[1] - a[1]) ** 2 >= (d + margin) ** 2 for a in acc):
                acc.append(q)
        out[name] = len(acc)
    out['dupontHousingFits'] = bool((near & (D >= DUPONT_DIAG / 2 + margin)).any())
    out['windowHalfMm'] = half
    return out


def main():
    t0 = time.time()
    out = {'method': __doc__.strip().splitlines()[0], 'resolutionMm': RES, 'windowHalfMm': WIN, 'sections': {}}
    for name, (axis, val, seed, label) in SECTIONS.items():
        rec = {'plane': f'{axis} = {val}', 'seed': seed, 'label': label, 'q0': {}, 'roll': [], 'yawRoll': []}
        r0, D, info = section(name, {}, True)
        rec['q0']['withExistingCables'] = r0
        r1, D1, info1 = section(name, {}, False)
        rec['q0']['partsOnly'] = r1
        if info:
            ctr = [r0['centreHeadFrame'][i] for i in ({'z': (0, 1), 'x': (1, 2), 'y': (0, 2)}[axis])]
            rec['q0']['capacityWithExistingCables'] = capacity(D, info[2], info[0], ctr)
        if info:
            np.savez(SCRATCH / f'sec-{name}-q0.npz', D=D, lo=info[0], res=RES, comp=info[2], L=info[3], names=np.array(info[4]),
                     centre=r0['centreHeadFrame'], r=r0['radiusMm'])
        print(name, 'q0', r0['radiusMm'], r0.get('boundedBy'), '| parts only', r1['radiusMm'], f'{time.time() - t0:.0f}s', flush=True)
        floor = False
        for roll in ROLLS:
            yaws = YAWS if floor else [0.0]
            for yaw in yaws:
                q = {'head_roll': np.radians(roll), 'head_yaw': np.radians(yaw)}
                rr, _, _ = section(name, q, True)
                rp, _, _ = section(name, q, False)
                row = {'rollDeg': roll, 'yawDeg': yaw, 'withExistingCables': rr.get('radiusMm'), 'partsOnly': rp.get('radiusMm'),
                       'boundedBy': rp.get('boundedBy'), 'inPolicyRange': bool(-21.4 <= roll <= 9.9 and -24.6 <= yaw <= 34.0)}
                (rec['yawRoll'] if floor else rec['roll']).append(row)
        rows = rec['yawRoll'] if floor else rec['roll']
        pol = [r for r in rows if r['inPolicyRange']]
        rec['minPartsOnlyPolicyMm'] = min(r['partsOnly'] for r in pol)
        rec['minPartsOnlyMjcfMm'] = min(r['partsOnly'] for r in rows)
        rec['minWithCablesPolicyMm'] = min(r['withExistingCables'] for r in pol)
        worst = min(pol, key=lambda r: r['withExistingCables'])
        rw, Dw, iw = section(name, {'head_roll': np.radians(worst['rollDeg'])}, True)
        if iw:
            ctr = [rw['centreHeadFrame'][i] for i in ({'z': (0, 1), 'x': (1, 2), 'y': (0, 2)}[axis])]
            rec['worstPolicyRoll'] = {'rollDeg': worst['rollDeg'], 'withExistingCables': rw,
                                      'capacityWithExistingCables': capacity(Dw, iw[2], iw[0], ctr)}
        print('   min policy', rec['minPartsOnlyPolicyMm'], 'min mjcf', rec['minPartsOnlyMjcfMm'], f'{time.time() - t0:.0f}s', flush=True)
        out['sections'][name] = rec
        jdump(out, HERE / 'sections.json')


if __name__ == '__main__':
    main()
