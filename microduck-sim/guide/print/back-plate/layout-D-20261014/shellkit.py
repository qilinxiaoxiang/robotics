"""Rounded rear-box shells and wire tubes for the layout E-round / F / G studies (renders and numbers only, 2026-10-14).

Outline (y-z): a wide rectangle W (full width, rounded top / step corners) united with a narrow rectangle N (5991 tier,
rounded bottom corners) through a circular concave blend of radius rf (a straight step with rounded corners). The rear
edges (the outline edges at the back face x = X_LID) are rounded with a radius that depends on the edge class:
W side / W top / W step underside, N side / N bottom. The inner cavity is the offset of the outer surface by the wall
thickness T, so every inner rounding is concentric with the outer one (inner radius = outer - T).
The solid is meshed from the signed distance with manifold3d level_set; every number below comes from the same SDF.
World = guide frame (mm, x forward, y left, z up)."""
import math
from dataclasses import dataclass, field
import numpy as np
import manifold3d as m3


class _S:   # scalar backend
    mx = staticmethod(max); mn = staticmethod(min); ab = staticmethod(abs); hyp = staticmethod(math.hypot)
    @staticmethod
    def where(c, a, b):
        return a if c else b


class _V:   # numpy backend
    mx = staticmethod(np.maximum); mn = staticmethod(np.minimum); ab = staticmethod(np.abs); hyp = staticmethod(np.hypot)
    where = staticmethod(np.where)


def _clamp01(B, v):
    return B.mn(B.mx(v, 0.0), 1.0)


@dataclass
class Rect:
    y0: float; y1: float; z0: float; z1: float
    rc_top: float = 0.0          # y-z corner radius of the two top corners
    rc_bot: float = 0.0          # ... of the two bottom corners
    cls_side: str = 'side'; cls_top: str = 'top'; cls_bot: str = 'bot'


@dataclass
class Outline:
    W: Rect
    N: Rect = None
    rf: float = 0.0               # concave blend (fillet) radius at the step corners
    R: dict = field(default_factory=dict)   # rear-edge radius per class
    X_LID: float = -67.1
    X_IN: float = -47.0
    T: float = 1.2

    def _rect(self, B, y, z, r):
        cy, cz = 0.5 * (r.y0 + r.y1), 0.5 * (r.z0 + r.z1); hy, hz = 0.5 * (r.y1 - r.y0), 0.5 * (r.z1 - r.z0)
        top = z > cz
        rc = B.where(top, r.rc_top, r.rc_bot)
        dy, dz = B.ab(y - cy), B.ab(z - cz)
        qy, qz = dy - hy + rc, dz - hz + rc
        d = B.mn(B.mx(qy, qz), 0.0) + B.hyp(B.mx(qy, 0.0), B.mx(qz, 0.0)) - rc
        t = _clamp01(B, 0.5 + ((dy - hy) - (dz - hz)) / 3.0)          # 1 = nearest edge is a side edge
        Rr = t * self.R[r.cls_side] + (1 - t) * B.where(top, self.R[r.cls_top], self.R[r.cls_bot])
        return d, Rr

    def d2R(self, B, y, z):
        a, Ra = self._rect(B, y, z, self.W)
        if self.N is None:
            return a, Ra
        b, Rb = self._rect(B, y, z, self.N)
        r = self.rf
        if r <= 0:
            d = B.mn(a, b)
        else:
            d = B.mx(B.mn(a, b), r) - B.hyp(B.mx(r - a, 0.0), B.mx(r - b, 0.0))
            d = B.mn(d, B.mn(a, b))
        h = _clamp01(B, 0.5 + 0.5 * (b - a) / max(r, 1.0))
        return d, Ra * h + Rb * (1 - h)

    def sdf(self, B, x, y, z):
        """outer signed distance (negative inside), no front cut."""
        d2, R = self.d2R(B, y, z)
        dx = self.X_LID - x
        a, b = d2 + R, dx + R
        return B.mn(B.mx(a, b), 0.0) + B.hyp(B.mx(a, 0.0), B.mx(b, 0.0)) - R

    def sdf_np(self, P):
        P = np.atleast_2d(P)
        return self.sdf(_V, P[:, 0], P[:, 1], P[:, 2])

    def inner_np(self, P):
        """inner-cavity signed distance (negative inside the cavity)."""
        return self.sdf_np(P) + self.T

    def bounds(self):
        ys = [self.W.y0, self.W.y1] + ([self.N.y0, self.N.y1] if self.N else [])
        zs = [self.W.z0, self.W.z1] + ([self.N.z0, self.N.z1] if self.N else [])
        return min(ys), max(ys), min(zs), max(zs)

    def solids(self, h=0.3, faces=40000, x_shift=0.0):
        """outer solid (front cut at X_IN) and inner cavity (open through the front), marching cubes on an h grid.
        x_shift moves the grid planes along x, so a later planar cut (a cap seam) does not fall on a grid plane, where the
        marching-cubes vertices lie exactly on the cut and the boolean leaves pinched (non-manifold) edges."""
        y0, y1, z0, z1 = self.bounds(); X_IN, T = self.X_IN, self.T
        def mesh(fn, lo, hi):
            xs = np.arange(lo[0], hi[0] + h, h); ys = np.arange(lo[1], hi[1] + h, h); zs = np.arange(lo[2], hi[2] + h, h)
            vol = np.empty((len(xs), len(ys), len(zs)), np.float32)
            Y, Z = np.meshgrid(ys, zs, indexing='ij')
            for i, x in enumerate(xs):
                vol[i] = fn(np.full_like(Y, x), Y, Z)
            vol[0] = vol[-1] = -1; vol[:, 0] = vol[:, -1] = -1; vol[:, :, 0] = vol[:, :, -1] = -1
            from skimage.measure import marching_cubes
            v, f, _, _ = marching_cubes(vol, 0.0, spacing=(h, h, h))
            v = v + np.array([xs[0], ys[0], zs[0]])
            if faces:
                import trimesh
                tm = trimesh.Trimesh(v, f, process=True).simplify_quadric_decimation(face_count=faces)
                v, f = tm.vertices, tm.faces
            man = m3.Manifold(m3.Mesh(vert_properties=np.asarray(v, np.float32), tri_verts=np.asarray(f, np.uint32)))
            if man.volume() < 0 or man.is_empty():
                man = m3.Manifold(m3.Mesh(vert_properties=np.asarray(v, np.float32), tri_verts=np.asarray(f[:, ::-1], np.uint32)))
            return man
        S = lambda x, y, z: self.sdf(_V, x, y, z)
        fo = lambda x, y, z: -np.maximum(S(x, y, z), x - X_IN)
        fi = lambda x, y, z: -np.maximum(S(x, y, z) + T, x - (X_IN + 1.0))
        outer = mesh(fo, (self.X_LID - 1 + x_shift, y0 - 1, z0 - 1), (X_IN + 1, y1 + 1, z1 + 1))
        inner = mesh(fi, (self.X_LID + T - 1 + x_shift, y0 + T - 1, z0 + T - 1), (X_IN + 2, y1 - T + 1, z1 - T + 1))
        return outer, inner

    def flat_ok(self, y, z, head_r=2.1):
        """lid screw head seat lies on the flat back face: inside the outline by R + head radius."""
        d2, R = self.d2R(_S, y, z)
        return -d2 - R - head_r


# ------------------------------------------------------------------ radius search
def max_radius(ol, cls, pts, clr, lo=1.3, hi=10.0, step=0.1, extra=None):
    """largest radius of one edge class (others fixed) with every point at least clr inside the inner cavity.
    pts: (n,3) body points; extra: callable(ol) -> bool for other constraints. Returns (R, limiting point index, list)."""
    keep = ol.R[cls]; best = None; lim = None
    for R in np.arange(hi, lo - 1e-9, -step):
        ol.R[cls] = float(R)
        s = ol.inner_np(pts)
        ok = bool(np.all(s <= -clr)) and (extra is None or extra(ol))
        if ok:
            best = round(float(R), 2); break
        lim = int(np.argmax(s))
    ol.R[cls] = keep if best is None else best
    return best, lim


# ------------------------------------------------------------------ wires
def fillet_path(wp, R=3.0, n=8):
    """polyline through waypoints wp with every interior corner replaced by a circular arc of radius R (a corner gets less
    only when its two segments are too short for both neighbouring arcs)."""
    wp = [np.asarray(p, float) for p in wp]
    keep = [wp[0]]
    for p in wp[1:]:
        if np.linalg.norm(p - keep[-1]) > 1e-9:
            keep.append(p)
    wp = keep; m = len(wp)
    ang = [0.0] * m; treq = [0.0] * m
    for i in range(1, m - 1):
        u, v = wp[i - 1] - wp[i], wp[i + 1] - wp[i]
        u, v = u / np.linalg.norm(u), v / np.linalg.norm(v)
        a = math.acos(float(np.clip(u @ v, -1, 1))); ang[i] = a
        treq[i] = 0.0 if a > math.pi - 1e-3 else R / math.tan(a / 2)
    t = list(treq)
    for i in range(m - 1):
        L = np.linalg.norm(wp[i + 1] - wp[i]); need = t[i] + t[i + 1]
        if need > L:
            f = L / need; t[i] *= f; t[i + 1] *= f
    out = [wp[0]]
    for i in range(1, m - 1):
        b = wp[i]
        if treq[i] == 0.0:
            out.append(b); continue
        u, v = wp[i - 1] - b, wp[i + 1] - b; u, v = u / np.linalg.norm(u), v / np.linalg.norm(v)
        a = ang[i]; Re = t[i] * math.tan(a / 2)
        p0, p1 = b + u * t[i], b + v * t[i]
        bis = (u + v) / np.linalg.norm(u + v); ctr = b + bis * (Re / math.sin(a / 2))
        e0, e1 = p0 - ctr, p1 - ctr; th = math.acos(float(np.clip(e0 @ e1 / (Re * Re), -1, 1)))
        for k in range(n + 1):
            s_ = k / n
            q = (math.sin((1 - s_) * th) * e0 + math.sin(s_ * th) * e1) / math.sin(th) if th > 1e-6 else e0
            out.append(ctr + q)
    out.append(wp[-1])
    return np.array(out)


def min_bend_radius(pts):
    """smallest circumradius over consecutive point triples (straight runs ignored)."""
    r = np.inf
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        ab_, bc, ca = np.linalg.norm(b - a), np.linalg.norm(c - b), np.linalg.norm(a - c)
        area2 = np.linalg.norm(np.cross(b - a, c - a))
        if area2 > 1e-6 and min(ab_, bc) < 2.0:
            r = min(r, ab_ * bc * ca / (2 * area2))
    return r


def tube(pts, r=0.9, seg=14):
    sph = [m3.Manifold.sphere(r, seg).translate(list(map(float, p))) for p in pts]
    caps = [m3.Manifold.batch_hull([sph[i], sph[i + 1]]) for i in range(len(pts) - 1)]
    return m3.Manifold.batch_boolean(caps, m3.OpType.Add)


def path_length(pts):
    return float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))


def nearest(path, tm, r=0.9, step=0.3):
    """closest approach of a tube (centreline path, radius r) to a trimesh surface: (gap, centreline point, surface point)."""
    import trimesh
    P_ = [path[0]]
    for a, b in zip(path[:-1], path[1:]):
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
        P_ += [a + (b - a) * (k / n) for k in range(1, n + 1)]
    P_ = np.array(P_); q, d, _ = trimesh.proximity.closest_point(tm, P_)
    i = int(np.argmin(d)); return round(float(d[i] - r), 3), np.round(P_[i], 2).tolist(), np.round(q[i], 2).tolist()
