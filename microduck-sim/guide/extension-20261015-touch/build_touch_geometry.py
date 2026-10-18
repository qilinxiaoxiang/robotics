"""Touch extension geometry for the guide: XIAO ESP32-S3 on foam tape inside the cap, five copper pads, nine wire routes.

Inputs: the print-gate closed solids (ia_lib CACHE; set IA_CACHE) in the final pose, where the head cap is closed.
Outputs:
  world/touch_xiao.stl          Seeed XIAO ESP32-S3: 21 x 17.8 x 1.2 mm board, 17.5 x 13 x 2.4 mm shield and
                                            module, USB-C on the rear end; components towards the head interior.
  world/touch_xiao_tape.stl     1 mm foam double-sided tape under the flat back of the board, pressed to
                                            0.8 mm against the inner left wall of the cap.
  world/touch_pad_<id>.stl      copper foil tape 0.1 mm thick on the inner face of the cap wall (L1, R1, L2,
                                            R2, M), each 18 x 18 mm or smaller where the window holds less wall.
  touch_routes.json                         centrelines (robot frame, mm) of five pad leads and four A7Z leads.
Wires: every lead is soldered to a XIAO edge pad (castellated hole, top face). Pad leads are soldered to their copper
pad. The A7Z leads end in a female jumper plug on A7Z header pins 17 (3.3 V), 25 (GND), 29 (TWI0 SCL) and 31 (TWI0 SDA).
"""
import heapq, json, sys
from pathlib import Path
import numpy as np, trimesh
from scipy import ndimage

HERE = Path(__file__).resolve().parent
GUIDE = HERE.parent
sys.path.insert(0, str(GUIDE / 'content' / 'interference-audit'))
from ia_lib import load_solid, manifest, load_guide   # noqa: E402

WORLD = HERE / 'world'                           # staged here; copied to guide/print/world after the checks
ANCHOR = np.array([-4.2, 32.3, 126.8])          # inner left wall point nearest the pocket found by analysis/oriented_fit.py
TAPE = 0.8                                       # pressed foam tape
PCB = (21.0, 17.8, 1.2)
PADS = {'l1': (30, 50, 12, 32), 'r1': (30, 50, -32, -12), 'l2': (2, 26, 20, 34), 'r2': (2, 26, -34, -20), 'm': (42, 54, -8, 8)}
# XIAO edge pads used: (index from the USB end, edge). Edge +1 = D0..D6, edge -1 = 5V, GND, 3V3, D10, D9, D8, D7.
PITCH = 2.54
XIAO_PIN = {'D0': (0, +1), 'D1': (1, +1), 'D2': (2, +1), 'D3': (3, +1), 'D4': (4, +1), 'D5': (5, +1),
            '3V3': (2, -1), 'GND': (1, -1), 'D8': (5, -1)}
PAD_PIN = {'l1': 'D0', 'r1': 'D1', 'l2': 'D2', 'r2': 'D3', 'm': 'D8'}
A7Z = {'3V3': 17, 'GND': 25, 'D5': 29, 'D4': 31}  # D5 = SCL, D4 = SDA on the XIAO
CLEAR = 1.75                                     # grid clearance from occupied voxel centres for a 0.65 mm wire (1 mm grid)


def closed(k):
    v, f = load_solid(k)
    return trimesh.Trimesh(v, f, process=False)


cap = closed('head_cap')

# ---------------------------------------------------------------- XIAO pose: flat back parallel to the wall patch
pts, fi = trimesh.sample.sample_surface_even(cap, 40000, seed=2)
nrm = cap.face_normals[fi]
near = np.linalg.norm(pts - ANCHOR, axis=1) < 13
n0 = np.array([0.28, -0.89, -0.37])
patch = pts[near & (nrm @ n0 > 0.8)]
c = patch.mean(0)
n = np.linalg.svd(patch - c)[2][2]
n = n if n @ n0 > 0 else -n                      # into the head
ex = np.array([1.0, 0, 0]) - n[0] * n; ex /= np.linalg.norm(ex)   # long axis forward, in the wall plane
ey = np.cross(n, ex)                             # D0..D6 edge on +ey (up the wall)
Rb = np.column_stack([ex, ey, n])


def board_T(origin):
    T = np.eye(4); T[:3, :3] = Rb; T[:3, 3] = origin; return T


def local_box(ext, centre):
    b = trimesh.creation.box(extents=ext); b.apply_translation(centre); return b


# Board origin: centre of the back face. Slide along the wall to the pocket centre, then off the wall by the tape.
centre_wall = np.array([-1.7, 24.2, 123.4])
o = centre_wall - ((centre_wall - c) @ n) * n
pq = trimesh.proximity.ProximityQuery(cap)


def tape_mesh(origin):
    return local_box((PCB[0], PCB[1], TAPE), (0, 0, -TAPE / 2)).apply_transform(board_T(origin))


# Push off the wall until the tape's back face is 0.2 mm into the cap at its deepest point (foam pressed into the curve).
for off in np.arange(-2, 6, 0.05):
    org = o + n * (TAPE + off)
    t = tape_mesh(org)
    back = trimesh.sample.sample_surface_even(local_box((PCB[0], PCB[1], 0.01), (0, 0, -TAPE)).apply_transform(board_T(org)), 3000, seed=0)[0]
    inside = cap.contains(back)
    depth = pq.signed_distance(back[inside]).max() if inside.any() else 0   # trimesh: positive inside
    if not inside.any() or depth <= 0.2:
        break
origin = org
T = board_T(origin)
xiao = trimesh.util.concatenate([
    local_box(PCB, (0, 0, PCB[2] / 2)),
    local_box((17.5, 13.0, 2.4), (1.0, 0, PCB[2] + 1.2)),          # shield can and module
    local_box((7.4, 9.0, 3.2), (-PCB[0] / 2 + 3.0, 0, PCB[2] + 1.6)),  # USB-C, rear end (local -x)
]).apply_transform(T)
xiao = trimesh.boolean.union(xiao.split(only_watertight=False), engine='manifold')
tape = tape_mesh(origin)
WORLD.mkdir(exist_ok=True)
xiao.export(WORLD / 'touch_xiao.stl'); tape.export(WORLD / 'touch_xiao_tape.stl')
print('board placed', origin.round(2), flush=True)


def pin_xyz(name):
    i, side = XIAO_PIN[name]
    x = -PCB[0] / 2 + 2.88 + i * PITCH          # both edges count from the USB end (local -x)
    y = side * (PCB[1] / 2 - 0.9)
    return (T @ [x, y, PCB[2] + 0.7, 1])[:3], (T @ [x, y + side * 3.5, PCB[2] + 0.7, 1])[:3]


# ---------------------------------------------------------------- copper pads: second hit of a downward ray = inner face
ri = trimesh.ray.ray_triangle.RayMeshIntersector(cap)


def inner_grid(xs, ys):
    """Inner face z of the cap wall at each (x, y) node (NaN where there is no wall right under the outer skin)."""
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    O = np.column_stack([X.ravel(), Y.ravel(), np.full(X.size, 170.0)])
    loc, iray, _ = ri.intersects_location(O, np.tile([0, 0, -1.0], (len(O), 1)), multiple_hits=True)
    Z = np.full(X.size, np.nan)
    for r in range(len(O)):
        z = np.sort(loc[iray == r, 2])[::-1]
        if len(z) >= 2 and z[0] - z[1] <= 5.0:   # second hit = inner face of the wall under the outer skin
            Z[r] = z[1]
    return X, Y, Z.reshape(X.shape)


pads, pad_meta = {}, {}
for pid, (x0, x1, y0, y1) in PADS.items():
    xs, ys = np.arange(x0, x1 + 0.01, 1.0), np.arange(y0, y1 + 0.01, 1.0)
    X, Y, Z = inner_grid(xs, ys)
    best = None
    for s in (18, 16, 14, 12, 10):               # largest square with wall under every node, nearest the window centre
        ok = [(i, j) for i in range(len(xs) - s) for j in range(len(ys) - s) if not np.isnan(Z[i:i + s + 1, j:j + s + 1]).any()]
        if ok:
            i, j = min(ok, key=lambda q: (xs[q[0]] + s / 2 - (x0 + x1) / 2) ** 2 + (ys[q[1]] + s / 2 - (y0 + y1) / 2) ** 2)
            best = (s, xs[i] + s / 2, ys[j] + s / 2, np.stack([X, Y, Z], -1)[i:i + s + 1, j:j + s + 1]); break
    assert best, pid
    s, cx, cy, P = best
    m = len(P)
    N = np.cross(np.gradient(P, axis=0), np.gradient(P, axis=1))   # surface normals from the node grid
    N /= np.linalg.norm(N, axis=2, keepdims=True)
    N = np.where(N[..., 2:3] > 0, -N, N)         # unit normals pointing down into the head
    top, bot = P + N * 0.02, P + N * 0.12          # 0.1 mm copper, 0.02 mm off the wall (adhesive)
    V = np.vstack([top.reshape(-1, 3), bot.reshape(-1, 3)]); off = m * m
    F = []
    for i in range(m - 1):
        for j in range(m - 1):
            a, b, cc, d = i * m + j, i * m + j + 1, (i + 1) * m + j + 1, (i + 1) * m + j
            F += [[a, b, cc], [a, cc, d], [a + off, cc + off, b + off], [a + off, d + off, cc + off]]
    ring = [(0, j) for j in range(m)] + [(i, m - 1) for i in range(1, m)] + [(m - 1, j) for j in range(m - 2, -1, -1)] + [(i, 0) for i in range(m - 2, 0, -1)]
    for k in range(len(ring)):
        a = ring[k][0] * m + ring[k][1]; b = ring[(k + 1) % len(ring)][0] * m + ring[(k + 1) % len(ring)][1]
        F += [[a, a + off, b + off], [a, b + off, b]]
    pm = trimesh.Trimesh(V, np.array(F), process=True)
    trimesh.repair.fix_normals(pm)
    assert pm.is_watertight, pid
    pm.export(WORLD / f'touch_pad_{pid}.stl'); print('pad', pid, s, flush=True)
    pads[pid] = pm
    # lead start: the pad node nearest the XIAO, 0.75 mm off the copper
    flat = (P + N * 0.85).reshape(-1, 3)
    pad_meta[pid] = {'size_mm': s, 'centre_xy': [round(cx, 1), round(cy, 1)], 'lead_start': flat[np.argmin(np.linalg.norm(flat - origin, axis=1))]}

# ---------------------------------------------------------------- routing grid: the 1 mm head grid of analysis/head_space.py
# (every gate solid, closed and filled) plus the new board, tape and pads. Routes keep CLEAR from occupied voxel centres;
# cables.py then checks the drawn tubes exactly against the solids.
hs = np.load(HERE / 'analysis' / 'head_space.npz')
occ, LO, G = hs['occ'].copy(), hs['lo'], float(hs['p'])
shape = np.array(occ.shape)
for mesh in [xiao, tape, *pads.values()]:
    lo, hi = np.floor((mesh.bounds[0] - LO) / G).astype(int) - 1, np.ceil((mesh.bounds[1] - LO) / G).astype(int) + 1
    ax = [LO[d] + (np.arange(lo[d], hi[d]) + 0.5) * G for d in range(3)]
    Q = np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3)
    d = trimesh.proximity.ProximityQuery(mesh).signed_distance(Q)      # positive inside
    hit = (d > -0.5 * G).reshape([len(a) for a in ax])                  # voxel within half a cell of the solid
    occ[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] |= hit
print('grid stamped', occ.sum(), flush=True)
dist = ndimage.distance_transform_edt(~occ) * G
# keep wires inside the head: outside = reachable from the grid boundary through free cells above the cap rim
free = dist >= CLEAR
# Every touch wire rides on the cap and lifts with it: keep it above the cap rim (z 111.1) with 2 mm to spare.
free[:, :, :int(np.ceil((113.0 - LO[2]) / G))] = False
lab, _ = ndimage.label(free)
centre_lab = lab[tuple(np.floor((np.array([20, 0, 135]) - LO) / G).astype(int))]
assert centre_lab, 'head centre not free'
free = lab == centre_lab
cost_mult = np.where(dist < 2.8, 1.0, 1.6)       # prefer lying against a surface, as a taped wire does


def cell(p):
    return tuple(np.floor((np.asarray(p) - LO) / G).astype(int))


def nearest_free(p):
    i = np.array(cell(p)); best, bd = None, 1e9
    for d in np.argwhere(np.ones((9, 9, 9), bool)) - 4:
        q = i + d
        if np.all(q >= 0) and np.all(q < shape) and free[tuple(q)]:
            dd = np.linalg.norm(d)
            if dd < bd: best, bd = tuple(q), dd
    assert best is not None, p
    return best


NB = [d for d in np.argwhere(np.ones((3, 3, 3), bool)) - 1 if np.any(d)]
NBL = [np.linalg.norm(d) for d in NB]


def astar(a, b):
    a, b = nearest_free(a), nearest_free(b)
    bb = np.array(b); openq = [(0, 0, a)]; g = {a: 0}; par = {a: None}
    while openq:
        _, gc, u = heapq.heappop(openq)
        if u == b: break
        if gc > g[u]: continue
        for d, l in zip(NB, NBL):
            v = (u[0] + d[0], u[1] + d[1], u[2] + d[2])
            if not (0 <= v[0] < shape[0] and 0 <= v[1] < shape[1] and 0 <= v[2] < shape[2]) or not free[v]:
                continue
            ng = gc + l * cost_mult[v]
            if ng < g.get(v, 1e18):
                g[v] = ng; par[v] = u
                heapq.heappush(openq, (ng + np.linalg.norm(np.array(v) - bb), ng, v))
    assert b in par, 'no path'
    path = [b]
    while par[path[-1]] is not None: path.append(par[path[-1]])
    pts = LO + (np.array(path[::-1]) + 0.5) * G
    # thin to corners: keep a point where the direction changes, then drop points closer than 3 mm
    keep = [pts[0]]
    for i in range(1, len(pts) - 1):
        if np.linalg.norm((pts[i + 1] - pts[i]) - (pts[i] - pts[i - 1])) > 1e-6 and np.linalg.norm(pts[i] - keep[-1]) >= 3.0:
            keep.append(pts[i])
    keep.append(pts[-1])
    return np.array(keep)


routes = {}
for pid, meta in pad_meta.items():
    pin = PAD_PIN[pid]
    end, out = pin_xyz(pin)
    mid = astar(meta['lead_start'], out)
    routes[f'touch_pad_{pid}'] = np.vstack([meta['lead_start'], mid[1:-1], out, end]).round(2).tolist()
for pin, a7z in A7Z.items():
    end, out = pin_xyz(pin)
    y = -19.05 + (35 - a7z) * 1.27
    # Up through the 2.3 mm gap between the plug ends (x 73.9) and the camera board (x 76.2), as the amplifier BCLK
    # wire does on pin 12, then back over the A7Z towards the cap roof.
    tail = np.array([[72.5, y, 129.0], [75.1, y, 123.0], [75.1, y, 114.66], [73.7, y, 114.06]])
    mid = astar(out, tail[0])
    routes[f'touch_a7z_pin{a7z}'] = np.vstack([end, out, mid[1:-1], tail]).round(2).tolist()

L = {k: round(float(np.sum(np.linalg.norm(np.diff(np.array(v), axis=0), axis=1))), 1) for k, v in routes.items()}
out = {'_doc': __doc__.strip().splitlines()[0], 'board_origin': origin.round(2).tolist(), 'board_axes': Rb.round(4).tolist(),
       'pads': {k: {'size_mm': v['size_mm'], 'centre_xy': v['centre_xy']} for k, v in pad_meta.items()},
       'lengths_mm': L, 'routes': routes}
(HERE / 'touch_routes.json').write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ('board_origin', 'pads', 'lengths_mm')}, indent=1))
print('xiao bounds', xiao.bounds.round(1).tolist(), 'watertight', xiao.is_watertight, 'tape watertight', tape.is_watertight)
