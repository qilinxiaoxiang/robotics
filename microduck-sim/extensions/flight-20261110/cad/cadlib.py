"""Small manifold3d helpers for the flight-pack parts (mm)."""
import math
import numpy as np
import manifold3d as m3
import trimesh

SEG = 96


def box(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return m3.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())


def union(parts):
    parts = [p for p in parts if p is not None]
    return m3.Manifold.batch_boolean(parts, m3.OpType.Add) if len(parts) > 1 else parts[0]


def _frame(axis):
    a = np.asarray(axis, float); a /= np.linalg.norm(a)
    ref = np.array([0, 0, 1.0]) if abs(a[2]) < 0.9 else np.array([1.0, 0, 0])
    u = np.cross(ref, a); u /= np.linalg.norm(u); v = np.cross(a, u)
    return u, v, a


def place(m, origin, axis, up=None):
    """Map local frame (z = axis, x = 'up' tip direction when given) onto the world."""
    a = np.asarray(axis, float); a /= np.linalg.norm(a)
    if up is None:
        u, v, a = _frame(a)
    else:
        u = np.asarray(up, float); u = u - a * (u @ a); u /= np.linalg.norm(u); v = np.cross(a, u)
    M = np.column_stack([u, v, a, np.asarray(origin, float)])
    return m.transform(M)


def cyl(r, p0, axis, length, r2=None, seg=SEG):
    c = m3.Manifold.cylinder(length, r, r if r2 is None else r2, seg)
    return place(c, p0, axis)


def tube(r_in, r_out, p0, axis, length):
    return cyl(r_out, p0, axis, length) - cyl(r_in, np.asarray(p0) - np.asarray(axis) / np.linalg.norm(axis) * 0.01, axis, length + 0.02)


def teardrop(d, p0, axis, length, up):
    """Full circle of diameter d plus a 45 deg tip toward `up` (PRINT-FIT teardrop rule: never narrows the hole)."""
    r = d / 2
    tip = r * math.sqrt(2)
    cs = m3.CrossSection([[(r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for a in range(135, 406, 5)]
                          + [(0.0, tip)]])
    # local: y is the tip direction; rotate so local +x = up for place(): swap via cross-section built with tip on +y
    m = cs.extrude(length)
    m = m.rotate([0, 0, -90])           # tip now on local +x
    return place(m, p0, axis, up)


def to_trimesh(man):
    mesh = man.to_mesh()
    t = trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=True)
    return t


def from_trimesh(t):
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))


def mirror_y(man):
    return man.mirror([0, 1, 0])


def rot_matrix(print_rot):
    """3x3 matrix of print_fit's print_rot list (applied in order)."""
    import print_fit as F
    R = np.eye(3)
    for ax, deg in print_rot:
        R = np.array(F._rot(ax, deg)) @ R
    return R


def to_print(t, print_rot):
    """Rotate a world mesh into its print pose and put it on the bed (z min 0), centred in x/y."""
    m = t.copy()
    T = np.eye(4); T[:3, :3] = rot_matrix(print_rot)
    m.apply_transform(T)
    lo, hi = m.bounds
    m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    return m
