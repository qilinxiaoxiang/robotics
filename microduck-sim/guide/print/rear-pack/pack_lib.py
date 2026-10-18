"""Shared helpers for the MicroDuck rear pack (world = guide = MuJoCo trunk_base frame, mm, x forward, y left, z up).

Everything here is read-only on the repo. Geometry is built with manifold3d (exact booleans) and exported with trimesh.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as m3

IA = '/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit'
PSO = IA + '/power-support-origin'
FIT = Path('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/e281f88a-117d-47f8-a4cc-4faadc6be94a/scratchpad/torso-fit')
OUT = Path(__file__).resolve().parent   # guide/print/rear-pack: scripts, checks and renders; the STLs are copied to print/world as rear_pack.stl / rear_pack_cover.stl
for p in (IA, PSO):
    if p not in sys.path:
        sys.path.insert(0, p)
import ia_lib  # noqa: E402

RETIRED = ['power_support', 'regulator_insert', 'openrb_tray', 'fuse_main', 'imu_clamp', 'imu_cover', 'junction_j',
           'regulator', 'openrb_board', 'imu_board', 'xt30_robot',
           'imu_sh4_receiving']   # the old IMU's SH4 plug room at the retired IMU position (x -57.5..-54.7, y -14.6..-9.6, z 11.5..18.5)


# ---------------------------------------------------------------- manifold / mesh conversion
def to_m(v, f):
    return ia_lib.to_manifold(np.asarray(v, float), np.asarray(f, np.int64))


def mesh_to_m(mesh: trimesh.Trimesh):
    return to_m(mesh.vertices, mesh.faces)


def from_m(man) -> trimesh.Trimesh:
    v, f = ia_lib.from_manifold(man)
    return trimesh.Trimesh(v, f, process=False)


def box(lo, hi):
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    return m3.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())


def cyl_x(r, x0, x1, y, z, seg=48):
    """Cylinder with its axis along +x from x0 to x1 at (y, z)."""
    c = m3.Manifold.cylinder(x1 - x0, r, r, seg)                 # along +z, base at z=0
    # rotate: z -> x  (rotate about y by +90 deg maps +z to +x)
    return c.rotate([0.0, 90.0, 0.0]).translate([x0, y, z])


def cyl_y(r, y0, y1, x, z, seg=48):
    c = m3.Manifold.cylinder(y1 - y0, r, r, seg)
    return c.rotate([-90.0, 0.0, 0.0]).translate([x, y0, z])      # +z -> +y


def cyl_z(r, z0, z1, x, y, seg=48):
    return m3.Manifold.cylinder(z1 - z0, r, r, seg).translate([x, y, z0])


def cone_x(r0, r1, x0, x1, y, z, seg=48):
    """Cone/frustum along +x: radius r0 at x0, r1 at x1."""
    c = m3.Manifold.cylinder(x1 - x0, r0, r1, seg)
    return c.rotate([0.0, 90.0, 0.0]).translate([x0, y, z])


def polys_from_shapely(geom):
    """shapely (Multi)Polygon -> list of rings for manifold3d CrossSection (exterior + holes)."""
    from shapely.geometry import Polygon, MultiPolygon
    rings = []
    gs = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    for g in gs:
        if g.is_empty:
            continue
        rings.append([(float(x), float(y)) for x, y in list(g.exterior.coords)[:-1]])
        for h in g.interiors:
            rings.append([(float(x), float(y)) for x, y in list(h.coords)[:-1]])
    return rings


def extrude_yz(geom, x0, x1):
    """Extrude a shapely polygon drawn in (y, z) coordinates over x0..x1 (world)."""
    cs = m3.CrossSection(polys_from_shapely(geom), m3.FillRule.EvenOdd)
    man = cs.extrude(x1 - x0)                                     # local: (u=y, v=z, w=0..h)
    T = np.array([[0.0, 0.0, 1.0, x0],                            # x = w + x0
                  [1.0, 0.0, 0.0, 0.0],                           # y = u
                  [0.0, 1.0, 0.0, 0.0]])                          # z = v   (det +1)
    return man.transform(T)


def extrude_xy(geom, z0, z1):
    cs = m3.CrossSection(polys_from_shapely(geom), m3.FillRule.EvenOdd)
    return cs.extrude(z1 - z0).translate([0.0, 0.0, z0])


def union(mans):
    mans = [m for m in mans if m is not None and not m.is_empty()]
    return m3.Manifold.batch_boolean(mans, m3.OpType.Add) if mans else m3.Manifold()


def volume(man):
    return float(man.volume())


# ---------------------------------------------------------------- guide parts
_solid_cache = {}


def solid_mesh(key) -> trimesh.Trimesh:
    if key not in _solid_cache:
        v, f = ia_lib.load_solid(key)
        _solid_cache[key] = trimesh.Trimesh(v, f, process=False)
    return _solid_cache[key]


def solid_m(key):
    return mesh_to_m(solid_mesh(key))


def all_solid_keys():
    return list(ia_lib.manifest().keys())


# ---------------------------------------------------------------- board poses (Layout L, fit study spec_final.json)
# OpenRB-150: guide board (bounds x -78.95..-12.06, y -12.71..12.69, z -52.9..-40.31) -> world via local = v - bounds_min,
# R = [[0,0,-1],[0,1,0],[1,0,0]], t = (-22.4, -13, -42)   (fit study spec_final.json, rot 22)
OPENRB_R = np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]], float)
OPENRB_T = np.array([-22.4, -13.0, -42.0])
OPENRB_GUIDE_MIN = np.array([-78.95, -12.71, -52.9])

# BNO085: guide board (x -57.53..-53.0, y -12.7..12.7, z 3.57..26.43) -> local = v - bounds_min; R_I = [[0,0,1],[-1,0,0],[0,-1,0]];
# body box x -18..4.86, y +-2.265, z 5.5..30.9 => t = (-18.0, 2.265, 30.9)
IMU_R = np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0]], float)
IMU_T = np.array([-18.0, 2.265, 30.9])
IMU_GUIDE_MIN = np.array([-57.53, -12.7, 3.57])

DFR_BOX = (np.array([-45.0, -13.0, -3.0]), np.array([-37.0, 13.0, 27.0]))
DFR_PAD_ROOM = (np.array([-45.0, -13.0, -11.0]), np.array([-37.0, 13.0, -3.0]))
ROOM_LEG_PLUGS = (np.array([-42.45, -4.3, -27.75]), np.array([-32.45, 3.6, -17.75]))
ROOM_NECK_PLUG = (np.array([-30.65, 12.4, -27.75]), np.array([-26.45, 22.4, -17.75]))
ROOM_TERMINAL = (np.array([-34.7, -4.7, 24.9]), np.array([-22.4, 4.8, 32.9]))
ROOM_USB = (np.array([-31.4, -7.3, -57.0]), np.array([-23.9, 6.7, -42.0]))
ROOM_IMU_PLUG_TOP = (np.array([-9.57, -2.265, 32.83]), np.array([-3.57, 2.265, 42.83]))
ROOM_IMU_SOCKET_TOP = (np.array([-10.07, -2.265, 30.9]), np.array([-3.07, 2.265, 32.83]))


def placed_board(key, R, t, guide_min) -> trimesh.Trimesh:
    m = solid_mesh(key).copy()
    v = (m.vertices - guide_min) @ R.T + t
    out = trimesh.Trimesh(v, m.faces, process=False)
    if out.volume < 0:
        out.invert()
    return out


# The audit's solid cache now serves the placed boards (ia_lib.WORLD_FILE -> print/world), so the placement is read from
# those files instead of being applied a second time to the cached solids.
WORLD = OUT.parent / 'world'
# Keys this pack's own checks model themselves (the pack, its cover and its contents); never environment obstacles.
SELF_KEYS = {'rear_pack', 'rear_pack_cover', 'openrb_board', 'imu_board', 'imu_sh4_receiving', 'regulator', 'xt30_robot'}


def openrb_mesh():
    return load_stl(WORLD / 'openrb-board-upright.stl')


def imu_mesh():
    return load_stl(WORLD / 'imu_board.stl')


def openrb_holes_world():
    """Hole axes (along x) of the placed OpenRB: fitted guide hole centres (x_g, y_g) = (-15.2 | -76.7, +-10.25), dia 2.5."""
    out = []
    for xg in (-76.7, -15.2):
        for yg in (-10.25, 10.25):
            p = OPENRB_R @ (np.array([xg, yg, -52.9]) - OPENRB_GUIDE_MIN) + OPENRB_T
            out.append((round(float(p[1]), 3), round(float(p[2]), 3)))
    return out  # (y, z)


def clean_mesh(man) -> trimesh.Trimesh:
    """manifold3d result -> indexed trimesh without duplicate vertices or zero-area faces; raises if not watertight."""
    m = from_m(man)
    for _ in range(12):
        m.merge_vertices()
        m.update_faces(m.area_faces > 1e-9)
        m.merge_vertices()
        edges = m.edges_sorted
        u, first, cnt = np.unique(edges, axis=0, return_index=True, return_counts=True)
        open_e = u[cnt == 1]; open_rows = first[cnt == 1]
        if len(open_e) == 0:
            break
        # T-junctions left by coplanar seams: an open long edge (a,c) carries a vertex b of two shorter open edges; split its face at b
        V = m.vertices; cand = np.unique(open_e.ravel())
        new_faces = []; drop = []
        for (a, c), row in zip(open_e, open_rows):
            f = row // 3
            if f in drop:
                continue
            seg = V[c] - V[a]; L2 = seg @ seg
            best = None
            for b in cand:
                if b == a or b == c:
                    continue
                t = (V[b] - V[a]) @ seg / L2
                if 1e-6 < t < 1 - 1e-6 and np.linalg.norm(V[b] - (V[a] + t * seg)) < 1e-6:
                    best = b; break
            if best is None:
                continue
            tri = list(m.faces[f]); x = [v for v in tri if v not in (a, c)][0]
            ia, ic = tri.index(a), tri.index(c)
            if (ic - ia) % 3 == 1:          # order a -> c in the face winding
                new_faces += [[a, best, x], [best, c, x]]
            else:
                new_faces += [[c, best, x], [best, a, x]]
            drop.append(f)
        if not new_faces:
            break
        keep = np.ones(len(m.faces), bool); keep[drop] = False
        m = trimesh.Trimesh(m.vertices, np.vstack([m.faces[keep], np.array(new_faces)]), process=False)
    if not m.is_watertight or not m.is_winding_consistent:
        e = m.edges_sorted; _, c = np.unique(e, axis=0, return_counts=True)
        raise RuntimeError(f'cleaned mesh not watertight: edge-face counts {dict(zip(*np.unique(c, return_counts=True)))}')
    return m


def load_stl(path) -> trimesh.Trimesh:
    """Load one of the pack STLs with shared vertices (STL files store loose triangles; manifold3d needs an indexed mesh)."""
    m = trimesh.load(str(path), force='mesh', process=True)
    m.merge_vertices(merge_tex=True, merge_norm=True)
    man = mesh_to_m(m)
    if man.status() != m3.Error.NoError or man.is_empty():
        raise RuntimeError(f'{path}: not a manifold after vertex merge: {man.status()}')
    return m


def jdump(obj, path):
    def conv(o):
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (np.bool_,)):
            return bool(o)
        raise TypeError(type(o))
    Path(path).write_text(json.dumps(obj, indent=1, default=conv))
