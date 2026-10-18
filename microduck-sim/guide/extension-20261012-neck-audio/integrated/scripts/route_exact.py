#!/usr/bin/env python3
"""Exact clearance along a found in-head route (route_search.py output) in the integrated head.

1. The voxel path is smoothed (moving average over 7 voxels, end points kept) and resampled every 0.5 mm.
2. Profile: at every sample, the exact unsigned distance from the centreline to every solid of route_scene.scene() at
   every sampled pose of its sweep (jaw 0..40 deg every 2 deg, head roll -25..+25 deg every 2.5 deg), via trimesh
   closest-point queries (unsigned: the route lies in free voxels by construction). This is the free radius of a round tube on that centreline (not re-centred). The re-centred
   radius is the largest such distance over offsets up to 1.5 mm (0.5 mm steps) in the plane perpendicular to the
   route: the free radius of the passage at that point, where the group may shift sideways.
3. Sections: at the narrowest place of the re-centred profile and at the narrowest places of the profile (local minima
   at least 6 mm apart, lowest first) the plane through
   the sample perpendicular to the route is cut exactly through every solid and pose (manifold3d slice in a rotated
   frame), rasterised at 0.05 mm, and a Euclidean distance transform gives the largest inscribed circle of the free
   region holding the route (radius, width = 2 x radius) and how many 1.7 mm / 1.3 mm round wires fit side by side within
   +-8 mm of its centre (greedy packing, a lower bound), and whether a 1-pin Dupont housing (2.54 mm square, diagonal
   3.59 mm) passes.
4. Descent: every sample is classified inside or outside the cap-descent mask (route-occ.npz): inside = must ride with
   the cap (or be free slack), outside = may be clipped to the lower head.
Usage: route_exact.py <scenario>. Writes ../route-exact-<scenario>.json and SCRATCH/route-exact-<scenario>.npz.
"""
import json
import sys
import time

import manifold3d as m3
import numpy as np
import trimesh
from matplotlib.path import Path as MPath
from scipy import ndimage

import int_lib as L
from check_lib import tm_from_man
from route_scene import poses, scene

RES, WIN = 0.05, 9.0
CHUNK = int(__import__("os").environ.get("ROUTE_CHUNK", "12"))   # closest-point batch size (bounds memory on the large cap mesh)
WIRES = {'22AWG_silicone_1p7': 1.7, '26AWG_silicone_1p3': 1.3}
DUPONT_DIAG = 2.54 * np.sqrt(2)


def smooth(P, w=7):
    P = np.asarray(P, float)
    if len(P) <= w:
        return P
    k = np.ones(w) / w
    Q = np.stack([np.convolve(np.pad(P[:, i], (w // 2, w // 2), mode='edge'), k, mode='valid') for i in range(3)], 1)
    Q[0], Q[-1] = P[0], P[-1]
    return Q


def resample(p, step=0.5):
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    n = max(2, int(np.ceil(s[-1] / step)) + 1)
    t = np.linspace(0, s[-1], n)
    return np.stack([np.interp(t, s, p[:, i]) for i in range(3)], 1), t


def all_solids(S, reach=12.0):
    """Every solid and sweep pose whose bounding box comes within `reach` mm of a route sample (others are dropped
    at once to bound memory); each with its trimesh for distance queries."""
    out = []
    for name, (M, grp) in scene().items():
        for j, Mp in enumerate(poses(name, M, grp)):
            b = np.array(Mp.bounding_box()).reshape(2, 3)
            gap = np.linalg.norm(np.maximum(0, np.maximum(b[0] - S, S - b[1])), axis=1)
            if gap.min() < reach:
                out.append((name, grp, j, Mp, tm_from_man(Mp)))
    return out


def profile(S, solids):
    d = np.full(len(S), np.inf)
    who = np.full(len(S), '', dtype=object)
    lo, hi = S.min(0) - 10, S.max(0) + 10
    for name, grp, j, M, tm in solids:
        b = np.array(M.bounding_box()).reshape(2, 3)
        if (b[0] > hi).any() or (b[1] < lo).any():
            continue
        gap = np.linalg.norm(np.maximum(0, np.maximum(b[0] - S, S - b[1])), axis=1)
        sel = gap < np.minimum(d, 10.0)
        if not sel.any():
            continue
        idx = np.where(sel)[0]
        dd = np.concatenate([trimesh.proximity.closest_point(tm, S[idx[i:i + CHUNK]])[1] for i in range(0, len(idx), CHUNK)])
        better = dd < d[idx]
        d[idx[better]] = dd[better]
        who[idx[better]] = name
    return d, who


def frame(t):
    t = t / np.linalg.norm(t)
    a = np.array([0, 0, 1.0]) if abs(t[2]) < 0.9 else np.array([1.0, 0, 0])
    u = np.cross(t, a)
    u /= np.linalg.norm(u)
    v = np.cross(t, u)
    return u, v, t


def section(p, t, solids):
    u, v, w = frame(t)
    R = np.stack([u, v, w])                      # world -> local (rows)
    n = int(round(2 * WIN / RES)) + 1
    g = -WIN + RES * np.arange(n)
    G = np.stack(np.meshgrid(g, g, indexing='ij'), -1).reshape(-1, 2)
    lab = np.zeros(len(G), np.int16)
    names = ['free']
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = -R @ p
    for name, grp, j, M, _ in solids:
        b = np.array(M.bounding_box()).reshape(2, 3)
        if np.linalg.norm(np.maximum(0, np.maximum(b[0] - p, p - b[1]))) > WIN * 1.5:
            continue
        Ml = M.transform(T[:3])
        bl = np.array(Ml.bounding_box()).reshape(2, 3)
        if bl[0, 2] > 0 or bl[1, 2] < 0 or (bl[0, :2] > WIN).any() or (bl[1, :2] < -WIN).any():
            continue
        polys = Ml.slice(0.0).to_polygons()
        ins = np.zeros(len(G), bool)
        for poly in polys:
            poly = np.asarray(poly)
            if len(poly) >= 3:
                ins ^= MPath(poly).contains_points(G)
        if ins.any():
            if name not in names:
                names.append(name)
            lab[ins & (lab == 0)] = names.index(name)
    Lb = lab.reshape(n, n)
    free = Lb == 0
    D = ndimage.distance_transform_edt(free, sampling=RES) - RES / 2
    comp_lab, _ = ndimage.label(free)
    near = (np.linalg.norm(G, axis=1) <= 2.0).reshape(n, n) & free
    if not near.any():
        return {'blocked': True, 'radiusMm': 0.0}, None
    kk = np.unravel_index(np.argmax(np.where(near, D, -1)), D.shape)
    comp = comp_lab == comp_lab[kk]
    local = float(np.where(near.reshape(n, n) & comp, D, 0).max())   # passage radius within 2 mm of the route point
    Dm = np.where(comp, D, 0)
    k = np.unravel_index(np.argmax(Dm), Dm.shape)
    rmax = float(Dm[k])
    c2 = g[list(k)]
    ring = (np.linalg.norm(G - c2, axis=1) <= rmax + 2.5 * RES) & (lab > 0)
    bound = sorted({names[i] for i in np.unique(lab[ring])})
    X, Y = np.meshgrid(g, g, indexing='ij')
    nearc = (np.abs(X - c2[0]) <= 8) & (np.abs(Y - c2[1]) <= 8) & comp
    cap = {}
    for nm, dw in WIRES.items():
        feas = nearc & (D >= dw / 2 + 0.05)
        pts = np.stack([X[feas], Y[feas]], 1)[np.argsort(D[feas])]
        acc = []
        for q in pts:
            if all((q[0] - a[0]) ** 2 + (q[1] - a[1]) ** 2 >= (dw + 0.05) ** 2 for a in acc):
                acc.append(q)
        cap[nm] = len(acc)
    cap['dupontHousingFits'] = bool((nearc & (D >= DUPONT_DIAG / 2 + 0.05)).any())
    # extent of the free strip that holds a 1.7 mm wire: longest chord of {D >= 0.9} along its principal direction
    strip = nearc & (D >= 0.9)
    ext = 0.0
    if strip.sum() > 3:
        Q = np.stack([X[strip], Y[strip]], 1)
        Qc = Q - Q.mean(0)
        e = np.linalg.svd(Qc, full_matrices=False)[2][0]
        ext = float(np.ptp(Qc @ e))
    centre = p + c2[0] * u + c2[1] * v
    return {'localRadiusMm': round(local, 3), 'localWidthMm': round(2 * local, 2),
            'radiusMm': round(rmax, 3), 'widthMm': round(2 * rmax, 2), 'centre': np.round(centre, 2).tolist(),
            'note': 'local = largest free circle centred within 2 mm of the route; radius/width = largest anywhere in the '
                    'free region of the +-9 mm window that holds the route',
            'boundedBy': bound, 'capacityWithin8mm': cap, 'stripLengthHolding1p7WireMm': round(ext, 2),
            'touchesWindowEdge': bool(comp[[0, -1], :].any() or comp[:, [0, -1]].any())}, (D, Lb, names, comp, g)


def main(name):
    t0 = time.time()
    z = np.load(L.SCRATCH / f'route-search-{name}.npz')
    occ = np.load(L.SCRATCH / 'route-occ.npz')
    S, s = resample(smooth(z['pts']))
    solids = all_solids(S)
    print('solids near the route', len(solids), f'{time.time() - t0:.0f}s', flush=True)
    d, who = profile(S, solids)
    # re-centred profile
    tang = np.gradient(S, axis=0)
    offs = [(a, b) for a in np.arange(-1.5, 1.51, 0.5) for b in np.arange(-1.5, 1.51, 0.5) if a * a + b * b <= 2.25 + 1e-9]
    cand = []
    for i in range(len(S)):
        u, v, _ = frame(tang[i])
        cand.extend(S[i] + a * u + b * v for a, b in offs)
    dc, _ = profile(np.array(cand), solids)
    dc = dc.reshape(len(S), len(offs)).max(1)
    print('profile', f'{time.time() - t0:.0f}s', 'min', round(float(d.min()), 3), who[int(np.argmin(d))], flush=True)
    # local minima, lowest first, >= 6 mm apart, skipping the first and last 2 mm (the ends sit at the slot and housings)
    order = np.argsort(d)
    picks = []
    # plus the narrowest place of the re-centred profile (the passage itself, where the group may shift sideways)
    ic = int(np.argmin(np.where((s >= 5.0) & (s <= s[-1] - 2.0), dc, np.inf)))
    picks.append(ic)
    for i in order:
        if s[i] < 2.0 or s[i] > s[-1] - 2.0:
            continue
        if all(abs(s[i] - s[j]) >= 6.0 for j in picks):
            picks.append(int(i))
        if len(picks) >= 5:
            break
    secs = []
    for i in picks:
        t = S[min(i + 2, len(S) - 1)] - S[max(i - 2, 0)]
        rec, extra = section(S[i], t, solids)
        rec.update({'atMm': round(float(s[i]), 1), 'point': np.round(S[i], 2).tolist(), 'profileRadiusMm': round(float(d[i]), 3),
                    'nearestOnProfile': who[i]})
        secs.append(rec)
        if extra is not None:
            np.savez_compressed(L.SCRATCH / f'route-sec-{name}-{len(secs)}.npz', D=extra[0], L=extra[1], names=np.array(extra[2]),
                                comp=extra[3], g=extra[4])
        print('section at', rec['atMm'], rec['radiusMm'], rec.get('boundedBy'), rec.get('capacityWithin8mm'), f'{time.time() - t0:.0f}s', flush=True)
    lo, P = occ['lo'], float(occ['pitch'])
    ijk = np.clip(np.round((S - lo) / P).astype(int), 0, np.array(occ['descent'].shape) - 1)
    inD = occ['descent'][tuple(ijk.T)]
    # stretches inside the descent mask
    runs = []
    cur = None
    for k, f in enumerate(inD):
        if f and cur is None:
            cur = k
        if (not f or k == len(inD) - 1) and cur is not None:
            runs.append([round(float(s[cur]), 1), round(float(s[k]), 1)])
            cur = None
    out = {'_method': __doc__.strip(), 'scenario': name, 'lengthMm': round(float(s[-1]), 1),
           'profile': {'minRadiusMm': round(float(d.min()), 3), 'at': np.round(S[int(np.argmin(d))], 2).tolist(),
                       'atMm': round(float(s[int(np.argmin(d))]), 1), 'nearest': who[int(np.argmin(d))],
                       'lengthBelowRadius': {f'{r}': round(float(0.5 * (d < r).sum()), 1) for r in (1.0, 1.5, 2.0, 2.5, 3.0)}},
           'recentredProfile': {'minRadiusMm': round(float(dc.min()), 3), 'atMm': round(float(s[int(np.argmin(dc))]), 1),
                                'at': np.round(S[int(np.argmin(dc))], 2).tolist(),
                                'lengthBelowRadius': {f'{r}': round(float(0.5 * (dc < r).sum()), 1) for r in (2.5, 3.0, 3.5, 4.0, 5.0)},
                                'minRadiusExcludingFirst5mm': round(float(dc[s > 5.0].min()), 3),
                                'atExcludingFirst5mm': np.round(S[s > 5.0][int(np.argmin(dc[s > 5.0]))], 2).tolist()},
           'sections': secs, 'descentMaskStretchesMm': runs, 'start': S[0], 'end': S[-1]}
    L.jdump(L.rnd(out, 3), L.STUDY / f'route-exact-{name}.json')
    np.savez_compressed(L.SCRATCH / f'route-exact-{name}.npz', S=S, s=s, d=d, dc=dc, who=who.astype(str), inD=inD)
    print(json.dumps(L.rnd({k: v for k, v in out.items() if k != '_method'}, 2))[:3000])


if __name__ == '__main__':
    main(sys.argv[1])
