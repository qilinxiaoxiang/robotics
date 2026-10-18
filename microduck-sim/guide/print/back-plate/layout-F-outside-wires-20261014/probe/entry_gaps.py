"""Where can a 22 AWG wire from the +y OUT windows (outside the box) get into the rear pack? (2026-10-14 draft)
Occupancy at 0.25 mm from every current guide solid (manifest; rear_frame / rear_lid replaced by this folder's P1-free
frame and the V1.11 cap) by z-slice sections; the box envelope (frame + cap outline, interior included) is blocked so no path
uses the inside of the box. Free-space distance transform -> for each start/goal pair the bottleneck radius r* (largest r
for which {clearance >= r} connects them) and where it sits. Entries are enumerated by blocking each found bottleneck
(sphere r 4) and searching again. Writes probe/entry_gaps.json and probe/entry_*.png."""
import sys, json, time
from pathlib import Path
import numpy as np, trimesh, shapely
from scipy import ndimage
import heapq
HERE = Path(__file__).resolve().parent; D = HERE.parent
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit')
import ia_lib
T0 = time.time()
def log(m): print(f'[{time.time()-T0:6.1f}s] {m}', flush=True)
H = 0.25
LO = np.array([-70.0, -36.0, -12.0]); HI = np.array([-4.0, 40.0, 48.0])
xs = np.arange(LO[0], HI[0] + 1e-9, H); ys = np.arange(LO[1], HI[1] + 1e-9, H); zs = np.arange(LO[2], HI[2] + 1e-9, H)
occ = np.zeros((len(xs), len(ys), len(zs)), bool)
man = ia_lib.manifest()
meshes = {}
for k, rec in man.items():
    if k in ('rear_frame', 'rear_lid'):
        continue
    lo, hi = np.array(rec['bounds'])
    if np.any(hi < LO) or np.any(lo > HI):
        continue
    meshes[k] = trimesh.Trimesh(*ia_lib.load_solid(k), process=False)
OPT = D.parent / 'layout-F-ear-20261014' / 'options'
meshes['frame_hidden_noP1'] = trimesh.load(str(D / 'frame_hidden_noP1-world.stl'), force='mesh')
meshes['lid_hidden'] = trimesh.load(str(OPT / 'lid_hidden-world.stl'), force='mesh')
meshes['screw_hidden'] = trimesh.load(str(OPT / 'screw_hidden-world.stl'), force='mesh')
log(f'{len(meshes)} meshes')
X2, Y2 = np.meshgrid(xs, ys, indexing='ij')
owner = {}
for k, m in meshes.items():
    b = m.bounds
    iz = np.where((zs >= b[0][2] - H) & (zs <= b[1][2] + H))[0]
    ix = np.where((xs >= b[0][0] - H) & (xs <= b[1][0] + H))[0]; iy = np.where((ys >= b[0][1] - H) & (ys <= b[1][1] + H))[0]
    if not len(ix) or not len(iy):
        continue
    sx, sy = slice(ix[0], ix[-1] + 1), slice(iy[0], iy[-1] + 1)
    for j in iz:
        try:
            s = m.section(plane_origin=[0, 0, zs[j]], plane_normal=[0, 0, 1])
        except Exception:
            s = None
        if s is None:
            continue
        try:
            pl, _ = s.to_2D(to_2D=np.eye(4))
            polys = pl.polygons_full
        except Exception:
            continue
        if not len(polys):
            continue
        g = shapely.union_all([p.buffer(0) for p in polys])
        ins = shapely.contains_xy(g, X2[sx, sy], Y2[sx, sy])
        occ[sx, sy, j] |= ins
log('occupancy %d' % occ.sum())
# block the box envelope (outer outline of frame + cap, interior included): x -67.1..-46.5
BX = (xs >= -67.2) & (xs <= -46.5)
for j, z in enumerate(zs):
    if -15.2 <= z <= 43.0:
        occ[np.ix_(BX, np.abs(ys) <= 32.05, [j])] = True
    elif -36.1 <= z < -15.2:
        occ[np.ix_(BX, np.abs(ys) <= 15.61, [j])] = True
dist = ndimage.distance_transform_edt(~occ) * H
log('edt')
def idx(p):
    return tuple(np.round((np.asarray(p) - LO) / H).astype(int))
def pt(i):
    return LO + np.asarray(i) * H

from skimage.graph import MCP_Geometric
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
def bottleneck(a, b, dmap, hi_r=3.0):
    lo_r = 0.0
    if dmap[a] <= 0 or dmap[b] <= 0:
        return 0.0
    for _ in range(12):
        r = 0.5 * (lo_r + hi_r); lab, _ = ndimage.label(dmap >= r)
        if lab[a] and lab[a] == lab[b]:
            lo_r = r
        else:
            hi_r = r
    return lo_r
def route(a, b, dmap, r):
    cost = np.where(dmap >= r, 1.0 + 0.6 / np.maximum(dmap, 0.25), np.inf)
    m = MCP_Geometric(cost, fully_connected=True); m.find_costs([a], [b]); tr = np.array(m.traceback(b))
    P = LO + tr * H; C = dmap[tr[:, 0], tr[:, 1], tr[:, 2]]
    return P, C
START = {'7V': [-58.0, 36.5, 28.2], '5V': [-58.0, 36.5, 14.0]}   # 5V start above z 12 (it rises outside the box wall first)
GOAL = {'J4_above': [-33.0, 0.0, 27.5], 'pack_channel': [-41.0, 8.0, 14.0]}
out = dict(method=__doc__, grid=dict(lo=LO.tolist(), hi=HI.tolist(), h=H), boxParts='frame_hidden_noP1 + lid_hidden + screw_hidden',
           pointClearance={k: round(float(dist[idx(p)]), 2) for k, p in {**START, **GOAL}.items()}, scenarios={})
XF = idx([-21.0, 0, 0])[0]
def nearest_parts(q):
    near = {}
    for k, m in meshes.items():
        if np.all(m.bounds[0] - 8 <= q) and np.all(m.bounds[1] + 8 >= q):
            cp, dd, _ = trimesh.proximity.closest_point(m, [q]); near[k] = round(float(dd[0]), 2)
    return dict(sorted(near.items(), key=lambda kv: kv[1])[:4])
def width(dmap, q, e, thr):
    n = 0.0
    for sgn in (1, -1):
        for s_ in np.arange(0.25, 40, 0.25):
            j = idx(q + sgn * s_ * e)
            if min(j) < 0 or any(j[a] >= dmap.shape[a] for a in range(3)) or dmap[j] < thr:
                n += s_ - 0.25; break
    return n
def plot(P, q, name):
    fig, axs = plt.subplots(1, 2, figsize=(15, 7))
    jy, jz = idx(q)[1], idx(q)[2]
    axs[0].imshow(occ[:, jy, :].T, origin='lower', extent=[LO[0], HI[0], LO[2], HI[2]], cmap='Greys', alpha=0.6)
    axs[0].plot(P[:, 0], P[:, 2], 'r-', lw=1); axs[0].plot(q[0], q[2], 'bo'); axs[0].set_title(f'{name}: x-z slice y={q[1]:.2f} (path projected)')
    axs[1].imshow(occ[:, :, jz].T, origin='lower', extent=[LO[0], HI[0], LO[1], HI[1]], cmap='Greys', alpha=0.6)
    axs[1].plot(P[:, 0], P[:, 1], 'r-', lw=1); axs[1].plot(q[0], q[1], 'bo'); axs[1].set_title(f'x-y slice z={q[2]:.2f}')
    for a in axs:
        a.grid(True, lw=0.3)
    fig.savefig(HERE / f'entry_{name}.png', dpi=100); plt.close(fig)
ZC = idx([0, 0, 12.0])[2]; XB = idx([-46.4, 0, 0])[0]
for scen in ('A_no_neck_opening', 'B_any', 'C_top_only'):
    dm = dist.copy()
    if scen[0] in 'AC':
        dm[XF:, :, :] = 0.0
    if scen[0] == 'C':
        dm[XB:, :, :ZC] = 0.0          # nothing in front of the box below z 12: no entry from under the shells
    rows = []
    for it in range(3):
        a, b = idx(START['7V']), idx(GOAL['J4_above'])
        r = bottleneck(a, b, dm)
        if r < 0.25:
            rows.append(dict(iteration=it, bottleneckRadius=round(r, 3), note='no further connection with clearance >= 0.25')); break
        P, C = route(a, b, dm, r * 0.97)
        i = int(np.argmin(C[8:-8])) + 8; q = P[i]
        t = P[min(i + 6, len(P) - 1)] - P[max(i - 6, 0)]; t = t / np.linalg.norm(t)
        e1 = np.cross(t, [0, 0, 1.0]); e1 = e1 / np.linalg.norm(e1) if np.linalg.norm(e1) > 1e-6 else np.array([0, 1.0, 0]); e2 = np.cross(t, e1)
        row = dict(iteration=it, bottleneckRadius=round(r, 3), slotHeightApprox=round(2 * r, 2), bottleneckPoint=np.round(q, 2).tolist(), pathTangent=np.round(t, 2).tolist(),
                   nearestParts=nearest_parts(q),
                   widthsAcrossPath={f'e1 {np.round(e1, 2).tolist()}': dict(clr0p9=width(dm, q, e1, 0.9), clr1p0=width(dm, q, e1, 1.0)),
                                     f'e2 {np.round(e2, 2).tolist()}': dict(clr0p9=width(dm, q, e2, 0.9), clr1p0=width(dm, q, e2, 1.0))},
                   pathLengthMm=round(float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1))), 1), path=np.round(P[::6], 2).tolist())
        rows.append(row); plot(P, q, f'{scen}_{it}'); log(json.dumps({k: v for k, v in row.items() if k != 'path'}))
        g = np.stack(np.meshgrid(*(np.arange(-16, 17),) * 3, indexing='ij'), -1).reshape(-1, 3)
        g = g[np.linalg.norm(g, axis=1) <= 16] + np.array(idx(q)); g = g[np.all((g >= 0) & (g < dm.shape), axis=1)]
        dm[g[:, 0], g[:, 1], g[:, 2]] = 0.0
    out['scenarios'][scen] = rows
    for sk, gk in (('5V', 'J4_above'), ('7V', 'pack_channel')):
        dm2 = dist.copy()
        if scen[0] in 'AC':
            dm2[XF:, :, :] = 0.0
        if scen[0] == 'C':
            dm2[XB:, :, :ZC] = 0.0
        r = bottleneck(idx(START[sk]), idx(GOAL[gk]), dm2)
        out['scenarios'][f'{scen} {sk}->{gk}'] = dict(bottleneckRadius=round(r, 3))
        log(f'{scen} {sk}->{gk} r* {r:.3f}')
(HERE / 'entry_gaps.json').write_text(json.dumps(out, indent=1))
log('done')
