"""Cable corridors in the closed head with the Pi seat shifted by [-DX, 0, DZ] and a 2x20 IDC socket on the header.

Same method as verify-cap/scripts/reroute2.py: 0.5 mm voxels, obstacles = head_cap + head parts fixed at cap-on +
speaker parts + amplifier (space outside the cap's convex hull blocked); the Pi group (PCB, components, header,
solder tails, Pi screw heads) plus the IDC socket body form a second obstacle class. Euclidean distance transforms,
then a 26-connected Euclidean shortest path inside {cap/fixed clearance >= keep, Pi-class clearance >= keepPi},
string-pulled, with an exact mesh-distance readback. If no path exists at the thresholds, the best achievable
cap/fixed clearance is found by bisection (connectivity) and reported with the bottleneck.

Routes (waypoints from guide/content/routes.json):
  bundle_head  from waypoint 8 (32.26, 25.98, 138.28) to the socket's conductor exit at column 4 (pins 7/8 area);
  head_i2s     from the socket's conductor exit at column 6 to head_i2s waypoint 6 (42.0, 28.0, 137.0);
  head_csi     from the camera connector (73, -3, 131) to the Pi CSI connector end moved with the Pi.
Thresholds: keep = 2.91 / keepPi = 1.25 (V1.6 drawn tail, verify-cap reroute2.json); the released V1.7 route has
2.95 / 1.13. Each case is run for the released V1.7 (dx 4.6, dz 0, socket on the header) and the candidate.
Usage: DX=.. DZ=.. CAND=<world.stl> route_v18.py   writes ../routes-v18-<tag>.json
"""
import json, sys, os, heapq, gc, time, resource
import numpy as np, trimesh
from matplotlib.path import Path as MPath
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import *

T0 = time.time()
def prog(msg):
    print(f'[{time.time()-T0:7.1f}s {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20:5.0f}MiB] {msg}', flush=True)

DX = float(os.environ['DX']); DZ = float(os.environ['DZ']); CAND = Path(os.environ['CAND'])
H_SOCKET = float(os.environ.get('H', '10.6'))
TAG = os.environ.get('TAG', f'dx{DX}-dz{DZ}')
KEEP, KEEP_PI = 2.91, 1.25
Pv = 0.5
LO = np.array([26.0, -36.0, 106.0]); HI = np.array([88.0, 46.0, 156.0])
nx, ny, nz = (np.round((HI - LO) / Pv)).astype(int)
xs = LO[0] + Pv * (np.arange(nx) + 0.5); ys = LO[1] + Pv * (np.arange(ny) + 0.5); zs = LO[2] + Pv * (np.arange(nz) + 0.5)
XY = np.stack(np.meshgrid(xs, ys, indexing='ij'), -1).reshape(-1, 2)
S, prov = solids(None)
OBS = [k for k in FIXED + SPEAKER + ['amplifier'] if k in S]
Bx = box(LO - 2, HI + 2)
others = union([S[k] for k in OBS]) ^ Bx
pi_keys = sorted(k for k in S if k == 'pi' or (k.startswith('head_pi') and 'receiving' not in k))
fas = json.load(open(ROOT / 'guide/content/fasteners.json'))['screws']
heads = []
for s_ in fas:
    if s_['id'].startswith('E-pi'):
        c = np.array(s_['center']) + np.array([4.6, 0, 0])
        heads.append(to_mf(trimesh.creation.cylinder(radius=2.0, segment=[c, c - 1.5 * np.array(s_['axis'])], sections=32)))
EVEN_C, ODD_C = 0.5 * sum(T_LOW), 0.5 * sum(T_HIGH)
routes = json.load(open(ROOT / 'guide/content/routes.json'))['routes']
bh = np.array(routes['bundle_head'], float); i2s = np.array(routes['head_i2s'], float); csi = np.array(routes['head_csi'], float)
CASES = {'V1.7 (dx 4.6, dz 0)': (np.array([-4.6, 0, 0]), load_cap(CAP_V17, CAP_V17_SHA)),
         'candidate': (np.array([-DX, 0, DZ]), to_mf(trimesh.load(CAND, force='mesh')))}


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
    return tuple(np.clip(np.floor((np.asarray(p) - LO) / Pv).astype(int), 0, [nx - 1, ny - 1, nz - 1]))


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
        if d[j] < best[0]:
            best = (float(d[j]), pts[i + j].round(2).tolist())
    return best


def shortest_w(mask, s, t):
    ids = np.full(mask.shape, -1, np.int64); ids[mask] = np.arange(mask.sum())
    rows, cols, ws = [], [], []
    for a in (0, 1):
        for b in (-1, 0, 1):
            for c in (-1, 0, 1):
                if (a, b, c) <= (0, 0, 0):
                    continue
                A_ = ids[max(0, -a):nx - max(0, a), max(0, -b):ny - max(0, b), max(0, -c):nz - max(0, c)]
                B_ = ids[max(0, a):nx + min(0, a), max(0, b):ny + min(0, b), max(0, c):nz + min(0, c)]
                ok = (A_ >= 0) & (B_ >= 0)
                rows.append(A_[ok]); cols.append(B_[ok]); ws.append(np.full(ok.sum(), Pv * np.sqrt(a * a + b * b + c * c), np.float32))
    n = int(mask.sum())
    G = coo_matrix((np.concatenate(ws), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    del rows, cols, ws
    si, ti = int(ids[s]), int(ids[t])
    if si < 0 or ti < 0:
        return None
    dist, pred = dijkstra(G, directed=False, indices=si, return_predecessors=True)
    if not np.isfinite(dist[ti]):
        return None
    inv = np.argwhere(mask); out = [ti]
    while out[-1] != si:
        out.append(int(pred[out[-1]]))
    ijk = inv[np.array(out[::-1])]
    return np.stack([xs[ijk[:, 0]], ys[ijk[:, 1]], zs[ijk[:, 2]]], 1)


def simplify(path, edt, keep, edt2, keep2):
    out = [path[0]]; i = 0
    while i < len(path) - 1:
        j = len(path) - 1
        while j > i + 1:
            seg = sample(np.array([path[i], path[j]]), 0.25)
            if min(edt[idx(p)] for p in seg) >= keep and min(edt2[idx(p)] for p in seg) >= keep2:
                break
            j -= 1
        out.append(path[j]); i = j
    return np.array(out)


def exit_point(col, d):
    """Conductor exit 2 mm above the socket's key-side face, 7 mm above the mating face, at column col."""
    y = 25.4 - 2.54 * col + 1.27
    return P(S_BASE_TOP + 7.0, y, ODD_C + 1.85 + 2.0) + d


others_occ = raster(others)
prog('others rastered')
rep = {'gridMm': Pv, 'box': [LO.tolist(), HI.tolist()], 'keep': KEEP, 'keepPi': KEEP_PI, 'socketHeight': H_SOCKET,
       'obstacles': OBS + ['head_cap'], 'piClass': pi_keys + ['E-pi screw heads', 'IDC socket'], 'cases': {}}
for label, (sh, cap) in CASES.items():
    occ = others_occ | raster(cap ^ Bx) | ~raster(mf.Manifold.hull(cap) ^ Bx)
    edt = ndimage.distance_transform_edt(~occ, sampling=Pv) - Pv / 2; del occ
    sock = union([local_hull((S_BASE_TOP, S_BASE_TOP + H_SOCKET), (-27.8, 27.8), (EVEN_C - 1.85, ODD_C + 1.85), sh),
                  local_hull((S_BASE_TOP, S_BASE_TOP + H_SOCKET), (-1.9, 1.9), (ODD_C + 1.85, ODD_C + 3.35), sh)])
    pig = union([tr(S[k], sh) for k in pi_keys] + [tr(h, sh) for h in heads] + [sock]) ^ Bx
    edt_pi = ndimage.distance_transform_edt(~raster(pig), sampling=Pv) - Pv / 2
    obst_tm = mf_to_tm(union([others, cap ^ Bx])); pig_tm = mf_to_tm(pig)
    prog(f'{label}: fields ready')
    r = {}
    jobs = {'bundle_head': (bh[8], exit_point(4, sh)), 'head_i2s': (exit_point(6, sh), i2s[6]),
            'head_csi': (csi[0], np.array([69.0, -31.0, 128.0]) + sh)}
    for name, (a, b) in jobs.items():
        s, t = idx(a), idx(b)
        rec = {'from': rnd(a.tolist()), 'to': rnd(b.tolist()), 'edtAtEnds': [round(float(edt[s]), 2), round(float(edt[t]), 2)],
               'edtPiAtEnds': [round(float(edt_pi[s]), 2), round(float(edt_pi[t]), 2)]}
        # the end at the socket (or at the CSI connector) lies inside the Pi-class clearance by construction: free a
        # 3 mm ball around both ends from the Pi-class threshold so the path can reach them
        ball = np.zeros((nx, ny, nz), bool)
        for e in (s, t):
            ii = [slice(max(0, e[q] - 6), e[q] + 7) for q in range(3)]
            ball[ii[0], ii[1], ii[2]] = True
        pi_ok = (edt_pi >= KEEP_PI) | (ball & (edt_pi > 0))
        mask = (edt >= KEEP) & pi_ok
        path = shortest_w(mask, s, t); gc.collect()
        if path is None:
            lo_, hi_ = 0.0, KEEP
            for _ in range(14):
                m = 0.5 * (lo_ + hi_)
                lab, _n = ndimage.label(pi_ok & (edt >= m), structure=np.ones((3, 3, 3)))
                lo_, hi_ = (m, hi_) if lab[s] > 0 and lab[s] == lab[t] else (lo_, m)
            rec['feasibleAtKeep'] = False; rec['bestCapAndFixedEdtMm'] = round(lo_, 2)
            path = shortest_w(pi_ok & (edt >= lo_ - 0.01), s, t)
            keep_used = max(lo_ - 0.01, 0)
        else:
            rec['feasibleAtKeep'] = True; keep_used = KEEP
        if path is not None:
            path[0], path[-1] = a, b
            simp = simplify(path, edt, keep_used, np.where(ball, 99.0, edt_pi), KEEP_PI)
            pts = sample(simp)
            core = pts[[i for i, p in enumerate(pts) if not ball[idx(p)]]] if len(pts) > 2 else pts
            dmin, at = exact_min(obst_tm, pts)
            dpi, atpi = exact_min(pig_tm, core) if len(core) else (None, None)
            rec.update({'waypoints': simp.round(2).tolist(), 'lengthMm': round(plen(simp), 2),
                        'exactMinDistToCapAndFixedMm': round(dmin, 2), 'at': at,
                        'exactMinDistToPiClassOutsideEndBallsMm': None if dpi is None else round(dpi, 2), 'atPi': atpi})
        r[name] = rec
        prog(f'{label} {name}: {json.dumps({k: v for k, v in rec.items() if k != "waypoints"})}')
    rep['cases'][label] = r
    del edt, edt_pi, obst_tm, pig_tm; gc.collect()
    json.dump(rep, open(OUT / f'routes-v18-{TAG}.json', 'w'), indent=1)
prog('done')
