"""Shared loaders for the independent head_cap / GPIO-housing verification (robot frame, mm, x fwd, y left, z up)."""
import hashlib, json
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf

HERE = Path(__file__).resolve().parent
ROOT = Path('/Users/xiangzheng/code/robotics/microduck-sim')
RD = ROOT / 'build-pack-20260913/redesign-20260913'
FI = RD / 'workflow-review-20261009/enclosed-wiring-repair/power-sensor/head-controller-study/final-integration-20261009'
CAP_V16 = ROOT / 'guide/print/world/head_cap.stl'
CAP_V16_STL = ROOT / 'guide/print/stl/head_cap.stl'
BASE_SHELL = RD / 'head-redesign-20261008/curved-head/community-curved-head-world.stl'
RAILS = [FI / 'pi-roof-side-rail-0.stl', FI / 'pi-roof-side-rail-1.stl']
BOSSES = [FI / f'controller-roof-boss-{i}.stl' for i in range(4)]
SPK_POSTS = RD / 'workflow-review-20261009/enclosed-wiring-repair/head-layout/speaker-mount-repair/speaker_roof_posts-candidate-world.stl'
AMP_POSTS = [RD / f'workflow-review-20261009/enclosed-wiring-repair/head-layout/head-flexible-harness/amp-mounts/amp_roof_post_{i}.stl' for i in range(2)]
V15_WORLD = FI / 'prototype-adoption/head-cap-prototype-world.stl'

# Parts that ride on the cap in step cap-on (guide/content/steps.py: cap + SPEAKER + amplifier + pi parts + gpio)
SPEAKER = ['speaker_cradle', 'speaker', 'speaker_keeper', 'speaker_mount_screw_1', 'speaker_mount_screw_2']
USED_PINS = [1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 14, 35, 40]
# Head parts already installed when the cap comes down (chapter 6 + neck), i.e. fixed during cap-on.
FIXED = ['head_bottom', 'face_panel', 'eye_trim', 'camera_board', 'camera_retainer', 'camera_clamp_screw_1',
         'camera_clamp_screw_2', 'camera_clamp_screw_3', 'jaw_support', 'mouth_sliding_ring', 'jaw_frame', 'lower_pad',
         'motor15', 'motor14', 'motor13', 'head_roll_ring_a', 'head_roll_ring_b', 'head_yaw_link', 'neck_pitch_ring']
CAMERA_STACK = ['camera_board', 'camera_retainer', 'camera_clamp_screw_1', 'camera_clamp_screw_2', 'camera_clamp_screw_3',
                'face_panel', 'eye_trim']


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load_npz(tag):
    z = np.load(HERE / f'{tag}-head.npz')
    keys = sorted({k[:-3] for k in z.files})
    return {k: (z[k + '__v'], z[k + '__f']) for k in keys}


def to_tm(v, f, repair=True):
    m = trimesh.Trimesh(np.asarray(v, float), np.asarray(f, np.int64), process=True)
    if repair and not m.is_volume:
        m.merge_vertices(digits_vertex=5)
        m.update_faces(m.nondegenerate_faces())
        m.update_faces(m.unique_faces())
        trimesh.repair.fill_holes(m)
        trimesh.repair.fix_normals(m, multibody=True)
    return m


def to_mf(m):
    M = mf.Manifold(mf.Mesh64(vert_properties=np.ascontiguousarray(m.vertices, np.float64),
                              tri_verts=np.ascontiguousarray(m.faces, np.uint64)))
    return M


def mf_to_tm(M):
    o = M.to_mesh64()
    return trimesh.Trimesh(np.asarray(o.vert_properties)[:, :3].copy(), np.asarray(o.tri_verts).astype(np.int64), process=False)


def load_stl(p):
    return trimesh.load(p, force='mesh', process=True)


def solids(source='mixed'):
    """Robot-frame manifolds for the head. Full-resolution CAD export, except guide-only keys and the V1.6 cap."""
    g = load_npz('guide'); s = load_npz('source')
    out, prov = {}, {}
    for k in sorted(set(g) | set(s)):
        if k in ('head_cap', 'openrb', 'head_pi_gpio_pin_20_receiving'):
            continue
        if k in s and source != 'guide':
            v, f = s[k]; prov[k] = 'full-build-data-current.json'
        else:
            v, f = g[k]; prov[k] = 'guide-data.json'
        m = to_tm(v, f)
        M = to_mf(m)
        if M.status() != mf.Error.NoError or M.volume() <= 0:
            M, how = robust_solid(v, f); prov[k] += f' (repaired: {how})'
        out[k] = M
    cap = load_stl(CAP_V16); out['head_cap'] = to_mf(cap); prov['head_cap'] = str(CAP_V16)
    return out, prov


def bbox(M):
    return np.array(M.bounding_box()).reshape(2, 3)


def tr(M, d):
    return M.translate(list(map(float, d)))


def overlap(A, B):
    a, b = bbox(A), bbox(B)
    if np.any(a[1] < b[0]) or np.any(b[1] < a[0]):
        return 0.0
    return (A ^ B).volume()


def union(Ms):
    Ms = [m for m in Ms if m is not None]
    return mf.Manifold.batch_boolean(Ms, mf.OpType.Add) if len(Ms) > 1 else Ms[0]


def box(lo, hi):
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    return mf.Manifold.cube(list(hi - lo), False).translate(list(lo))


def r3(x):
    return [round(float(v), 3) for v in x]


def robust_solid(v, f):
    """Closed solid from a possibly unwelded mesh: weld; if still not manifold, union per-component solids (hull fallback per component)."""
    m = trimesh.Trimesh(np.asarray(v, float), np.asarray(f, np.int64), process=True)
    m.merge_vertices(digits_vertex=4)
    m.update_faces(m.nondegenerate_faces()); m.update_faces(m.unique_faces())
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
    return union(parts), f"components {kinds}"
