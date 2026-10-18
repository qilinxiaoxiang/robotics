"""Shared paths and helpers for the MicroDuck V1.9 extension release geometry (guide/print/ext-v19).

Frame: robot frame at q = 0, mm, x forward, y left, z up (guide/print/world and the interference-audit solid cache).
Read-only on every V1.8 / guide source. The audit solid cache is a private copy of the last full guide audit cache
(EXT19_IA_CACHE), so a cache rebuild by another session cannot change these checks mid-run.
The study libraries of guide/extension-20261012-neck-audio are reused by path (audio/scripts, pi-mount/scripts,
neck-route, integrated/scripts).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True          # never leave __pycache__ in the read-only guide and study folders

HERE = Path(__file__).resolve().parent
OUT = HERE.parent                                           # guide/print/ext-v19
GUIDE = OUT.parents[1]                                      # guide
SIM = GUIDE.parent                                          # microduck-sim
EXT = GUIDE / 'extension-20261012-neck-audio'
STUDY_INT = EXT / 'integrated'
AUDIO = EXT / 'audio'
PIM = EXT / 'pi-mount'
NR = EXT / 'neck-route'
SCRATCH = Path(os.environ.get('EXT19_SCRATCH', '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/'
                                                'cb2a1eef-7aa0-4728-afad-9518fb22c188/scratchpad/ext-v19'))
SCRATCH.mkdir(parents=True, exist_ok=True)
os.environ['IA_CACHE'] = os.environ.get('EXT19_IA_CACHE', str(SCRATCH / 'ia-cache'))
os.environ.setdefault('INT_SCRATCH', str(SCRATCH / 'integrated'))
os.environ.setdefault('NR_SCRATCH', str(SCRATCH / 'neck-route'))
for p in (STUDY_INT / 'scripts', PIM / 'scripts', AUDIO / 'scripts', NR):
    if str(p) not in sys.path:
        sys.path.append(str(p))
IA = GUIDE / 'content' / 'interference-audit'
if str(IA) not in sys.path:
    sys.path.append(str(IA))

import ia_lib  # noqa: E402

FASTENERS = GUIDE / 'content' / 'fasteners.json'
ROUTES = GUIDE / 'content' / 'routes.json'
WORLD = GUIDE / 'print' / 'world'
PACK_V19 = GUIDE / 'print' / 'rear-pack-v19' / 'rear_pack-world.stl'
CAP_V18 = WORLD / 'head_cap.stl'
STUDY_CAP = STUDY_INT / 'study-solids' / 'head_cap-integrated-world.stl'
STUDY_CAP_SHA = '07862a0d0d7dc158cdd65be10e3a03aae0e380f1460fe328d51ad31554969b7c'   # integrated/cap-build.json
RUNNER = SIM / 'build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py'

# Release parts (robot frame at q = 0; the clips sit where they are fitted)
PARTS = {
    'head_cap_v19': OUT / 'head_cap_v19-world.stl',
    'speaker_retainer_v19': OUT / 'speaker_retainer_v19-world.stl',
    'clip_torso_v19': OUT / 'clip_torso_v19-world.stl',
    'clip_bracket_v19': OUT / 'clip_bracket_v19-world.stl',
    'clip_head_v19': OUT / 'clip_head_v19-world.stl',
    'clip_cap_v19': OUT / 'clip_cap_v19-world.stl',
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jdump(obj, path):
    def conv(o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, Path):
            return str(o)
        raise TypeError(type(o))
    Path(path).write_text(json.dumps(obj, indent=1, default=conv))


def rnd(x, n=3):
    if isinstance(x, dict):
        return {k: rnd(v, n) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rnd(v, n) for v in x]
    if isinstance(x, np.ndarray):
        return rnd(x.tolist(), n)
    if isinstance(x, (float, np.floating)):
        return round(float(x), n)
    if isinstance(x, np.integer):
        return int(x)
    return x


def load_man(key):
    v, f = ia_lib.load_solid(key)
    return ia_lib.to_manifold(v, f)


def stl_man(path):
    import trimesh
    m = trimesh.load(path, force='mesh')
    return ia_lib.to_manifold(np.asarray(m.vertices), np.asarray(m.faces))


def tm(M):
    import trimesh
    v, f = ia_lib.from_manifold(M)
    return trimesh.Trimesh(v, f, process=False)


def bbox(M):
    return np.array(M.bounding_box()).reshape(2, 3)


def near(a, b, pad):
    A, B = bbox(a), bbox(b)
    return bool(np.all(A[0] - pad <= B[1]) and np.all(B[0] - pad <= A[1]))


def fasteners():
    return {r['id']: r for r in json.loads(FASTENERS.read_text())['screws']}


def frame(ax):
    ax = np.asarray(ax, float)
    ax = ax / np.linalg.norm(ax)
    a = np.array([0, 0, 1.0]) if abs(ax[2]) < 0.9 else np.array([1.0, 0, 0])
    u = np.cross(ax, a)
    u /= np.linalg.norm(u)
    return u, np.cross(ax, u), ax


def cyl(p0, axis, length, r, seg=48):
    import manifold3d as m3
    u, v, a = frame(axis)
    return m3.Manifold.cylinder(float(length), float(r), float(r), seg).transform(np.c_[u, v, a, np.asarray(p0, float)])


def screw_solid(center, axis, length, d=2.0, head_d=4.0, head_h=1.5, seg=32):
    """Pan-head screw: head (head_d x head_h) outside the seat point, shank (d x length) along axis into the part."""
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    c = np.asarray(center, float)
    return cyl(c, a, length, d / 2, seg) + cyl(c - head_h * a, a, head_h, head_d / 2, seg)


def mesh_report(path):
    """Slicer-relevant mesh checks on the exported STL itself (reloaded with vertex merging, as slicers do)."""
    import trimesh
    m = trimesh.load(path, force='mesh')
    _, c = np.unique(m.edges_sorted, axis=0, return_counts=True)
    M = ia_lib.to_manifold(np.asarray(m.vertices), np.asarray(m.faces))
    return {'watertight': bool(m.is_watertight), 'windingConsistent': bool(m.is_winding_consistent),
            'bodies': len(m.split(only_watertight=False)), 'faces': int(len(m.faces)),
            'degenerateFaces': int((m.area_faces < 1e-10).sum()), 'edgesSharedByMoreThanTwoFaces': int((c > 2).sum()),
            'boundaryEdges': int((c == 1).sum()), 'volumeMm3': float(m.volume) if m.is_watertight else None,
            'manifold3d': {'status': str(M.status()), 'bodies': len(M.decompose()), 'volumeMm3': float(M.volume())},
            'eulerNumber': int(m.euler_number), 'sha256': sha(path)}
