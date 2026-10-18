"""Weighted shortest re-routes and route topology. Can bundle_head still be routed with the V1.6 clearance after the Pi seat moves 4.6 mm back?

Obstacles: head_cap (V1.6 or candidate), the head parts fixed at cap-on, speaker parts and amplifier in final pose.
The Pi group (PCB, components, header, solder tails) is a second obstacle class: the V1.6 route runs about 1.4 mm from it,
so a re-route must keep at least the V1.6 Pi clearance and the V1.6 clearance to everything else. The GPIO housing is the
destination and is not an obstacle.
Space outside the cap's convex hull is blocked. 0.5 mm voxels, Euclidean distance transform, maximum-bottleneck search
from waypoint 8 to the route end, then a shortest path at the V1.6 bottleneck and an exact mesh-distance readback.
"""
import json, sys, os, heapq
from collections import deque
import numpy as np, trimesh
from matplotlib.path import Path as MPath
from scipy import ndimage
sys.path.insert(0, os.path.dirname(__file__))
from vc import *

DX = 4.6; P = 0.5
LO = np.array([26.0, -4.0, 106.0]); HI = np.array([88.0, 46.0, 152.0])
nx, ny, nz = (np.round((HI - LO) / P)).astype(int)
xs = LO[0] + P * (np.arange(nx) + 0.5); ys = LO[1] + P * (np.arange(ny) + 0.5); zs = LO[2] + P * (np.arange(nz) + 0.5)
XY = np.stack(np.meshgrid(xs, ys, indexing='ij'), -1).reshape(-1, 2)
S, prov = solids()
OBS = [k for k in FIXED + SPEAKER + ['amplifier'] if k in S]
Bx = box(LO - 2, HI + 2)
others = union([S[k] for k in OBS]) ^ Bx
caps = {'V1.6': to_mf(load_stl(CAP_V16)), 'candidate': to_mf(load_stl(Path(os.environ.get('CAND', ROOT / 'guide/print/candidates/head-cap-pi-shift/head_cap-pi-shift-world.stl'))))}

def raster(M):
    occ = np.zeros((nx, ny, nz), bool)
    for k, z in enumerate(zs):
        par = np.zeros(len(XY), bool)
        for poly in M.slice(float(z)).to_polygons():
            if len(poly) >= 3:
                par ^= MPath(np.asarray(poly)).contains_points(XY)
        occ[:, :, k] = par.reshape(nx, ny)
    return occ

def idx(p):
    return tuple(np.clip(np.floor((np.asarray(p) - LO) / P).astype(int), 0, [nx - 1, ny - 1, nz - 1]))

bh = np.array(json.load(open(ROOT / 'guide/content/routes.json'))['routes']['bundle_head'], float)
def sample(path, step=0.25):
    out = []
    for a, b in zip(path[:-1], path[1:]):
        n = max(2, int(np.linalg.norm(b - a) / step) + 1); out.append(a + (b - a) * np.linspace(0, 1, n)[:, None])
    return np.vstack(out)
def plen(path):
    return float(np.linalg.norm(np.diff(path, axis=0), axis=1).sum())
def exact_min(mesh, pts):
    best = (np.inf, None)
    for i in range(0, len(pts), 50):
        _, d, _ = trimesh.proximity.closest_point(mesh, pts[i:i + 50]); j = int(np.argmin(d))
        if d[j] < best[0]: best = (float(d[j]), pts[i + j].round(2).tolist())
    return best

OFF = np.array([(a * ny + b) * nz + c for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1) if (a, b, c) != (0, 0, 0)])
DIJ = np.array([(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1) if (a, b, c) != (0, 0, 0)])
def nbrs(u):
    i, j, k = np.unravel_index(u, (nx, ny, nz))
    v = np.array([i, j, k]) + DIJ
    ok = (v >= 0).all(1) & (v < [nx, ny, nz]).all(1)
    return np.ravel_multi_index(v[ok].T, (nx, ny, nz))
def bottleneck(edt, s, t, allow=None):
    """Max over paths of the min clearance (widest path, Dijkstra on -min), flat indices."""
    E = edt.ravel(); A = None if allow is None else allow.ravel()
    s = int(np.ravel_multi_index(s, (nx, ny, nz))); t = int(np.ravel_multi_index(t, (nx, ny, nz)))
    best = np.full(E.size, -1.0, np.float32); best[s] = E[s]; h = [(-float(E[s]), s)]
    while h:
        nb, u = heapq.heappop(h); nb = -nb
        if u == t: return nb
        if nb < best[u]: continue
        for v in nbrs(u):
            if A is not None and not A[v]: continue
            w = min(nb, float(E[v]))
            if w > best[v]:
                best[v] = w; heapq.heappush(h, (-w, int(v)))
    return None
def shortest(mask, s, t):
    M = mask.ravel(); s = int(np.ravel_multi_index(s, (nx, ny, nz))); t = int(np.ravel_multi_index(t, (nx, ny, nz)))
    prev = np.full(M.size, -1, np.int64); prev[s] = s; q = deque([s])
    while q:
        u = q.popleft()
        if u == t: break
        for v in nbrs(u):
            if M[v] and prev[v] < 0:
                prev[v] = u; q.append(int(v))
    if prev[t] < 0: return None
    out = [t]
    while out[-1] != s: out.append(int(prev[out[-1]]))
    ijk = np.array(np.unravel_index(np.array(out[::-1]), (nx, ny, nz))).T
    return np.stack([xs[ijk[:, 0]], ys[ijk[:, 1]], zs[ijk[:, 2]]], 1)
def simplify(path, edt, keep, edt2=None, keep2=0.0):
    """Greedy string-pulling: drop vertices while every sample of the shortcut keeps edt >= keep."""
    out = [path[0]]; i = 0
    while i < len(path) - 1:
        j = len(path) - 1
        while j > i + 1:
            seg = sample(np.array([path[i], path[j]]), 0.25)
            if min(edt[idx(p)] for p in seg) >= keep and (edt2 is None or min(edt2[idx(p)] for p in seg) >= keep2): break
            j -= 1
        out.append(path[j]); i = j
    return np.array(out)

from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
import gc
c10, s10 = np.cos(np.radians(10)), np.sin(np.radians(10))
def shortest_w(mask, s, t):
    """Euclidean-weighted 26-connected shortest path inside mask (scipy csgraph Dijkstra)."""
    ids = np.full(mask.shape, -1, np.int64); ids[mask] = np.arange(mask.sum())
    rows, cols, ws = [], [], []
    for a in (0, 1):
        for b in (-1, 0, 1):
            for c in (-1, 0, 1):
                if (a, b, c) <= (0, 0, 0): continue
                A = ids[max(0, -a):nx - max(0, a), max(0, -b):ny - max(0, b), max(0, -c):nz - max(0, c)]
                B = ids[max(0, a):nx - max(0, -a) if a < 0 else nx, max(0, b):(ny if b >= 0 else ny + b), max(0, c):(nz if c >= 0 else nz + c)]
                A = ids[max(0, -a):nx - max(0, a), max(0, -b):ny - max(0, b), max(0, -c):nz - max(0, c)]
                B = ids[max(0, a):nx + min(0, a), max(0, b):ny + min(0, b), max(0, c):nz + min(0, c)]
                ok = (A >= 0) & (B >= 0)
                rows.append(A[ok]); cols.append(B[ok]); ws.append(np.full(ok.sum(), P * np.sqrt(a * a + b * b + c * c), np.float32))
    n = int(mask.sum())
    G = coo_matrix((np.concatenate(ws), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    del rows, cols, ws
    si, ti = int(ids[s]), int(ids[t])
    if si < 0 or ti < 0: return None
    dist, pred = dijkstra(G, directed=False, indices=si, return_predecessors=True)
    if not np.isfinite(dist[ti]): return None
    inv = np.argwhere(mask)
    out = [ti]
    while out[-1] != si: out.append(int(pred[out[-1]]))
    ijk = inv[np.array(out[::-1])]
    return np.stack([xs[ijk[:, 0]], ys[ijk[:, 1]], zs[ijk[:, 2]]], 1)
def crossing(path, sh):
    """Where the route crosses the Pi PCB mid-plane (pin-axis coordinate s), in (y, t)."""
    sx = path[:, 0] * c10 - path[:, 2] * s10 + sh[0] * -c10
    tt = path[:, 0] * s10 + path[:, 2] * c10 + sh[0] * -s10
    sgn = np.sign(sx - 39.89)
    k = np.where(np.diff(sgn) != 0)[0]
    return [[round(float(path[i, 1]), 2), round(float(tt[i]), 2)] for i in k]

others_occ = raster(others)
pi_keys = sorted(k for k in S if k == 'pi' or (k.startswith('head_pi') and 'receiving' not in k))
PIG = union([S[k] for k in pi_keys])
rep = {'gridMm': P, 'box': [LO.tolist(), HI.tolist()], 'obstacles': OBS + ['head_cap'], 'piGroup': pi_keys, 'DX': DX,
       'pcbNote': 'PCB mid-plane at pin-axis s = 39.89 (V1.6 frame); crossing lists (y, t) where t runs along the board from the header edge (t ~124) to the top edge (t ~152); |y| > 32.5 means around a side edge.',
       'edtNote': 'EDT values are voxel estimates, conservative by up to about 0.35 mm; exact mesh distances are reported for each path.'}
start = bh[8]; keep = None
for label, cap in caps.items():
    sh = np.array([-DX, 0, 0]) if label == 'candidate' else np.zeros(3)
    occ = others_occ | raster(cap ^ Bx) | ~raster(mf.Manifold.hull(cap) ^ Bx)
    edt = ndimage.distance_transform_edt(~occ, sampling=P) - P / 2; del occ
    pig = tr(PIG, sh) ^ Bx
    edt_pi = ndimage.distance_transform_edt(~raster(pig), sampling=P) - P / 2
    end = bh[-1] + sh; s, t = idx(start), idx(end)
    drawn = bh[8:].copy(); drawn[-3:] += sh; dpts = sample(drawn)
    r = {'drawnTail': {'waypoints': drawn.round(2).tolist(), 'lengthMm': round(plen(drawn), 2),
                       'edtMinToCapAndFixed': round(float(min(edt[idx(p)] for p in dpts)), 2),
                       'edtMinToPiGroup': round(float(min(edt_pi[idx(p)] for p in dpts)), 2), 'pcbCrossing': crossing(drawn if len(drawn) > 50 else dpts, sh)}}
    if keep is None:
        keep, keep_pi = r['drawnTail']['edtMinToCapAndFixed'], r['drawnTail']['edtMinToPiGroup']
    sx = (xs[:, None, None] * c10 - zs[None, None, :] * s10) - sh[0] * c10
    Y = np.broadcast_to(ys[None, :, None], (nx, ny, nz))
    base = (edt >= keep) & (edt_pi >= keep_pi)
    variants = {'any topology': base, 'around the +y edge (crossing the PCB plane only at y > 28)': base & ~((np.abs(sx - 39.89) < 6) & (Y < 28))}
    for vname, mask in variants.items():
        path = shortest_w(mask, s, t); gc.collect()
        if path is None:
            topo = variants[vname] | ~base  # same topology restriction, cap/fixed threshold released
            topo = (edt_pi >= keep_pi) & ~((np.abs(sx - 39.89) < 6) & (Y < 28)) if 'edge' in vname else (edt_pi >= keep_pi)
            lo_, hi_ = 0.0, keep
            for _ in range(14):
                m = (lo_ + hi_) / 2
                lab, _n = ndimage.label(topo & (edt >= m), structure=np.ones((3, 3, 3)))
                lo_, hi_ = (m, hi_) if lab[s] > 0 and lab[s] == lab[t] else (lo_, m)
            r[vname] = {'feasibleAtV16Clearance': False, 'bestCapAndFixedEdtMm': round(lo_, 2)}
            path = shortest_w(topo & (edt >= lo_ - 0.01), s, t)
            if path is not None:
                pts = sample(path); e = np.array([edt[idx(p)] for p in pts]); j = int(np.argmin(e))
                cor = box(pts[j] - 6, pts[j] + 6); o = mf_to_tm(union([others, cap ^ Bx]) ^ cor)
                for k in OBS + ['head_cap']:
                    pass
                near = {}
                for k in OBS:
                    Mk = S[k] ^ cor
                    if not Mk.is_empty():
                        _, d, _ = trimesh.proximity.closest_point(mf_to_tm(Mk), pts[j:j + 1]); near[k] = round(float(d[0]), 2)
                Mc = cap ^ cor
                if not Mc.is_empty():
                    _, d, _ = trimesh.proximity.closest_point(mf_to_tm(Mc), pts[j:j + 1]); near['head_cap'] = round(float(d[0]), 2)
                r[vname].update({'bottleneckPoint': pts[j].round(2).tolist(), 'exactDistAtBottleneckMm': near})
            print(label, vname, json.dumps(r[vname]), flush=True); continue
        path[0], path[-1] = start, end
        simp = simplify(path, edt, keep, edt_pi, keep_pi)
        cor = box(simp.min(0) - 8, simp.max(0) + 8)
        obst_tm = mf_to_tm(union([others, cap ^ Bx]) ^ cor); pig_tm = mf_to_tm(pig ^ cor)
        pts = sample(simp)
        dmin, at = exact_min(obst_tm, pts); dpi, atpi = exact_min(pig_tm, pts)
        r[vname] = {'waypoints': simp.round(2).tolist(), 'lengthMm': round(plen(simp), 2), 'pcbCrossing': crossing(pts, sh),
                    'exactMinDistToCapAndFixedMm': round(dmin, 2), 'at': at, 'exactMinDistToPiGroupMm': round(dpi, 2), 'atPi': atpi,
                    'fullRouteLengthMm': round(plen(np.vstack([bh[:8], simp])), 2)}
        del obst_tm, pig_tm; gc.collect()
        print(label, vname, json.dumps(r[vname]), flush=True)
    rep[label] = r
    del edt, edt_pi; gc.collect()
rep['keep'] = {'capAndFixedEdtMm': keep, 'piGroupEdtMm': keep_pi, 'source': 'minimum along the V1.6 drawn tail (waypoint 8 to the end)'}
rep['fullRouteLengthV16DrawnMm'] = round(plen(bh), 2)
json.dump(rep, open(HERE / 'reroute2.json', 'w'), indent=1)
