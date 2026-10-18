"""Shared helpers for the pack-UART study (robot frame, mm: x forward, y left, z up). Read-only on the repo.

Inputs: guide/print/world/openrb-board-upright.stl (ROBOTIS-derived OpenRB mesh placed in the V1.8 pack), the interference-audit
solid cache (ia_lib.load_solid), guide/content/routes.json (cable centrelines) and guide/print/rear-pack/pack_lib.py (pack rooms).
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as m3

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
GUIDE = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide')
IA = GUIDE / 'content' / 'interference-audit'
PACK = GUIDE / 'print' / 'rear-pack'
WORLD = GUIDE / 'print' / 'world'
for p in (str(IA), str(IA / 'power-support-origin'), str(PACK)):
    if p not in sys.path:
        sys.path.insert(0, p)
import ia_lib  # noqa: E402

ROUTES = json.loads((GUIDE / 'content' / 'routes.json').read_text())['routes']
# Cable radii as drawn by guide/content/build_guide_data.py (build_cables); orb-pwr and pi-trunk have no explicit radius there,
# 20 AWG / 22 AWG pair: 0.9 / 0.8 mm used here (inference).
CABLE_R = {'dxl5': 1.1, 'dxl10': 1.1, 'dxl12': 1.1, 'vin20': 1.2, 'openrbpwr': 0.9, 'trunk': 0.8, 'uart_lower': 0.7, 'imu': 0.8}

# Dupont 2.54 mm single-way crimp housing (inference: common 2.54 x 2.54 x 14 mm body; male pin about 6 mm out of the housing).
DUP = dict(w=2.54, housing=14.0, pin=6.0)
WIRE_R = 0.65            # one jumper wire, 26-28 AWG PVC, about 1.3 mm across (inference)
BEND_ROOM = 3.0          # straight wire out of the housing before it may turn (inference, about 2 x wire OD)

NEIGHBOURS = ['rear_pack', 'rear_pack_cover', 'regulator', 'openrb_board', 'imu_board', 'imu_sh4_receiving',
              'motor5', 'motor10', 'shell_left', 'shell_right', 'torso_base']


def tm(key):
    v, f = ia_lib.load_solid(key)
    return trimesh.Trimesh(v, f, process=False)


def man(key):
    v, f = ia_lib.load_solid(key)
    return ia_lib.to_manifold(np.asarray(v, float), np.asarray(f, np.int64))


def to_m(mesh):
    return ia_lib.to_manifold(np.asarray(mesh.vertices, float), np.asarray(mesh.faces, np.int64))


def from_m(mm):
    v, f = ia_lib.from_manifold(mm)
    return trimesh.Trimesh(v, f, process=False)


def box(lo, hi):
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    return m3.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())


def tube(pts, r, seg=16):
    """Union of capsules along a polyline (manifold)."""
    parts = []
    pts = [np.asarray(p, float) for p in pts]
    for a, b in zip(pts, pts[1:]):
        d = b - a; L = float(np.linalg.norm(d))
        if L < 1e-6:
            continue
        c = m3.Manifold.cylinder(L, r, r, seg)
        z = np.array([0, 0, 1.0]); u = d / L
        v = np.cross(z, u); s = np.linalg.norm(v); cth = float(z @ u)
        if s < 1e-9:
            R = np.eye(3) if cth > 0 else np.diag([1, -1, -1.0])
        else:
            vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
            R = np.eye(3) + vx + vx @ vx * ((1 - cth) / s ** 2)
        T = np.hstack([R, a.reshape(3, 1)])
        parts.append(c.transform(T.tolist()))
    for p in pts:
        parts.append(m3.Manifold.sphere(r, seg).translate(p.tolist()))
    return m3.Manifold.batch_boolean(parts, m3.OpType.Add)


def gap(a, b, search=10.0):
    """Exact minimum gap (manifold3d min_gap), 0 if they overlap; returns (gap, overlap volume)."""
    ov = float((a ^ b).volume())
    if ov > 1e-6:
        return 0.0, ov
    return float(a.min_gap(b, search)), 0.0


def r3(x, n=2):
    if isinstance(x, (list, tuple, np.ndarray)):
        return [r3(v, n) for v in x]
    return round(float(x), n)


def jdump(obj, path):
    Path(path).write_text(json.dumps(obj, indent=1))
