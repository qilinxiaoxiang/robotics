"""Shared geometry for the cap-settle study (robot frame, mm; x forward, y left, z up).

Pi header local frame (V1.6 seat, from verify-cap/inspect1.json):
  A  = (cos10, 0, -sin10)  pin axis, pins point forward and 10 deg down
  EY = (0, 1, 0)           along the 2x20 row
  CT = (sin10, 0, cos10)   across the two rows (up the board)
  point = s*A + y*EY + t*CT; header plastic top s = 43.231; pin tips s = 49.191.
  Row bands in t: CAD odd row 123.679..126.219, CAD even row 126.219..128.759.
A cap version with Pi shift dx carries every Pi-side item by [-dx, 0, 0]. The cap is lowered by [0, 0, 40].
"""
import hashlib, json, math, os
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
ROOT = Path('/Users/xiangzheng/code/robotics/microduck-sim')
CACHE = Path(os.environ.get('CS_CACHE', '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/'
                                        '92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/cap-settle-cache'))
CAP_V16 = Path('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/'
               'scratchpad/cap-v16-backup/world-head_cap.stl')
CAP_V16_SHA = '5c22fbf6186e089f9f1238baf9fc4e87493610710dba745e8b7d74eaec1a5428'
CAP_V17 = ROOT / 'guide/print/world/head_cap.stl'
CAP_V17_SHA = '5c2364f2ee31c8baef24eb93dcaeb8126125f5dcaf3d73b9826d004fcca78572'

C10, S10 = math.cos(math.radians(10)), math.sin(math.radians(10))
A = np.array([C10, 0.0, -S10]); EY = np.array([0.0, 1.0, 0.0]); CT = np.array([S10, 0.0, C10])
S_BASE_TOP = 43.231
PIN_LEN = 5.96
S_TIP = S_BASE_TOP + PIN_LEN
T_LOW = (123.679, 126.219)   # CAD odd row (lower, nearer the PCB edge)
T_HIGH = (126.219, 128.759)  # CAD even row (upper)
APPROACH = np.array([0.0, 0.0, 40.0])

USED_PINS = [1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 14, 35, 40]
AMP_PINS = [4, 12, 14, 35, 40]
FIXED = ['head_bottom', 'face_panel', 'eye_trim', 'camera_board', 'camera_retainer', 'camera_clamp_screw_1',
         'camera_clamp_screw_2', 'camera_clamp_screw_3', 'jaw_support', 'mouth_sliding_ring', 'jaw_frame', 'lower_pad',
         'upper_pad', 'motor15', 'motor14', 'motor13', 'head_roll_ring_a', 'head_roll_ring_b', 'head_yaw_link',
         'neck_pitch_ring']
CAMERA_STACK = ['camera_board', 'camera_retainer', 'camera_clamp_screw_1', 'camera_clamp_screw_2',
                'camera_clamp_screw_3', 'face_panel', 'eye_trim']
SPEAKER = ['speaker_cradle', 'speaker', 'speaker_keeper', 'speaker_mount_screw_1', 'speaker_mount_screw_2']


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def col_y(pin):
    k = (pin + 1) // 2
    return (25.4 - 2.54 * k, 25.4 - 2.54 * (k - 1))


def row_t(pin, physical=False):
    """CAD numbering: odd pins in the lower row. physical=True swaps rows (real Pi: even row along the board edge)."""
    odd = pin % 2 == 1
    if physical:
        odd = not odd
    return T_LOW if odd else T_HIGH


def P(s, y, t):
    return s * A + y * EY + t * CT


def to_mf(m):
    return mf.Manifold(mf.Mesh64(vert_properties=np.ascontiguousarray(m.vertices, np.float64),
                                 tri_verts=np.ascontiguousarray(m.faces, np.uint64)))


def mf_to_tm(M):
    o = M.to_mesh64()
    return trimesh.Trimesh(np.asarray(o.vert_properties)[:, :3].copy(), np.asarray(o.tri_verts).astype(np.int64), process=False)


def bbox(M):
    return np.array(M.bounding_box()).reshape(2, 3)


def tr(M, d):
    return M.translate([float(x) for x in d])


def union(Ms):
    Ms = [m for m in Ms if m is not None]
    return mf.Manifold.batch_boolean(Ms, mf.OpType.Add) if len(Ms) > 1 else Ms[0]


def box(lo, hi):
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    return mf.Manifold.cube(list(hi - lo), False).translate(list(lo))


def overlap(Am, Bm):
    a, b = bbox(Am), bbox(Bm)
    if np.any(a[1] < b[0]) or np.any(b[1] < a[0]):
        return 0.0
    return (Am ^ Bm).volume()


def gap(Am, Bm, search=8.0):
    """Exact triangle-mesh distance (manifold3d min_gap); 0 when touching or overlapping; capped at `search`."""
    a, b = bbox(Am), bbox(Bm)
    d = np.maximum(0, np.maximum(a[0] - b[1], b[0] - a[1]))
    if np.linalg.norm(d) > search:
        return search
    if overlap(Am, Bm) > 1e-6:
        return 0.0
    return float(Am.min_gap(Bm, search))


def load_npz(tag):
    z = np.load(CACHE / f'{tag}-head.npz')
    keys = sorted({k[:-3] for k in z.files})
    return {k: (z[k + '__v'], z[k + '__f']) for k in keys}


def robust_solid(v, f):
    m = trimesh.Trimesh(np.asarray(v, float), np.asarray(f, np.int64), process=True)
    if not m.is_volume:
        m.merge_vertices(digits_vertex=5)
        m.update_faces(m.nondegenerate_faces()); m.update_faces(m.unique_faces())
        trimesh.repair.fill_holes(m); trimesh.repair.fix_normals(m, multibody=True)
    M = to_mf(m)
    if M.status() == mf.Error.NoError and M.volume() > 0:
        return M, 'closed'
    m.merge_vertices(digits_vertex=4)
    M = to_mf(m)
    if M.status() == mf.Error.NoError and M.volume() > 0:
        return M, 'welded'
    parts, kinds = [], {'solid': 0, 'hull': 0}
    for c in m.split(only_watertight=False):
        trimesh.repair.fix_normals(c)
        C = to_mf(c)
        if C.status() == mf.Error.NoError and C.volume() > 0:
            parts.append(C); kinds['solid'] += 1
        elif len(c.vertices) >= 4:
            H = mf.Manifold.hull_points(np.asarray(c.vertices))
            if H.volume() > 1e-6:
                parts.append(H); kinds['hull'] += 1
    return union(parts), f'components {kinds}'


def solids(keys=None):
    """Full-resolution CAD solids (source export, Pi group at the V1.6 seat) for the requested keys."""
    s = load_npz('source')
    out, prov = {}, {}
    for k in (keys or sorted(s)):
        if k not in s:
            continue
        M, how = robust_solid(*s[k])
        out[k] = M; prov[k] = how
    return out, prov


def load_cap(path, expect_sha=None):
    if expect_sha:
        assert sha(path) == expect_sha, (path, sha(path))
    return to_mf(trimesh.load(path, force='mesh', process=True))


def local_hull(s_rng, y_rng, t_rng, d=np.zeros(3)):
    pts = np.array([P(si, yi, ti) for si in s_rng for yi in y_rng for ti in t_rng]) + d
    return mf.Manifold.hull_points(pts)


def sweep(M, approach=APPROACH):
    """Exact swept solid of a convex piece along a straight approach."""
    return mf.Manifold.hull(union([M, tr(M, approach)]))


def sphere_pts(c, r, n=16):
    """Points on a polyhedron circumscribing a sphere (vertices at r / cos(pi/n) so faces lie outside the sphere)."""
    u = np.linspace(0, math.pi, n // 2 + 1); v = np.linspace(0, 2 * math.pi, n, endpoint=False)
    rr = r / math.cos(math.pi / n) / math.cos(math.pi / n)
    pts = [[0, 0, rr], [0, 0, -rr]]
    for a in u[1:-1]:
        for b in v:
            pts.append([rr * math.sin(a) * math.cos(b), rr * math.sin(a) * math.sin(b), rr * math.cos(a)])
    return np.asarray(pts) + np.asarray(c)


def capsule(p0, p1, r, n=16):
    return mf.Manifold.hull_points(np.vstack([sphere_pts(p0, r, n), sphere_pts(p1, r, n)]))


def wire_chain(c0, a_dir, b_dir, rho, run, r_w, n_arc=9):
    """Wire leaving point c0 along a_dir, bending 90 deg towards b_dir with centreline radius rho, then a straight
    run along b_dir. Returns convex capsule pieces (each piece's sweep is exact)."""
    a_dir = np.asarray(a_dir, float); b_dir = np.asarray(b_dir, float)
    centre = c0 + rho * b_dir
    th = np.linspace(0, math.pi / 2, n_arc)
    pts = [centre - rho * b_dir * math.cos(t_) + rho * a_dir * math.sin(t_) for t_ in th]
    end = pts[-1]
    pieces = [capsule(p, q, r_w) for p, q in zip(pts[:-1], pts[1:])]
    if run > 0:
        pieces.append(capsule(end, end + run * b_dir, r_w))
    return pieces, np.asarray(pts)


def rnd(x, n=3):
    if isinstance(x, dict):
        return {k: rnd(v, n) for k, v in x.items()}
    if isinstance(x, (list, tuple, np.ndarray)):
        return [rnd(y, n) for y in x]
    if isinstance(x, (float, np.floating)):
        return round(float(x), n)
    return x
