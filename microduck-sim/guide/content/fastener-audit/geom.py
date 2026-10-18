"""Shared geometry helpers for the fastener audit (robot frame, mm; x forward, y left, z up)."""
from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize, unary_union

CACHE = Path(os.environ.get('FA_MESHES', '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/fa/meshes'))
_MESH: dict = {}


def mesh(key: str, kind: str = 'full') -> trimesh.Trimesh:
    k = (kind, key)
    if k not in _MESH:
        d = np.load(CACHE / kind / f'{key}.npz')
        _MESH[k] = trimesh.Trimesh(d['v'], d['f'], process=False)
    return _MESH[k]


def available(kind: str = 'full') -> list[str]:
    return sorted(p.stem for p in (CACHE / kind).glob('*.npz'))


def frame(axis):
    a = np.asarray(axis, float); a = a / np.linalg.norm(a)
    h = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(a, h); u /= np.linalg.norm(u)
    v = np.cross(a, u)
    return u, v, a


# ---------------------------------------------------------------- ray intervals
def _depth_intervals(ts, ss):
    """Depth-count entries (normal against the ray) and exits along one ray that starts outside every solid.
    Manufacturer CAD exports hold touching or nested solids whose coincident faces are not always both hit, so an
    exit at depth 0 is ignored and an unclosed interval ends at the last hit."""
    order = np.argsort(ts)
    ts, ss = ts[order], ss[order]
    keep = [0]
    for i in range(1, len(ts)):
        if ts[i] - ts[keep[-1]] > 1e-4 or np.sign(ss[i]) != np.sign(ss[keep[-1]]):
            keep.append(i)
    ts, ss = ts[keep], ss[keep]
    out, depth, start = [], 0, None
    for ti, si in zip(ts, ss):
        if si < 0:
            if depth == 0:
                start = ti
            depth += 1
        elif si > 0 and depth > 0:
            depth -= 1
            if depth == 0:
                out.append([float(start), float(ti)])
    if depth > 0:
        out.append([float(start), float(ts[-1])])
    merged = []
    for a, b in out:
        if merged and a <= merged[-1][1] + 1e-4:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def solid_intervals(m: trimesh.Trimesh, origins, direction):
    """For rays (origins outside all solids, shared direction) return per ray the solid intervals [t_in, t_out]."""
    origins = np.atleast_2d(np.asarray(origins, float))
    d = np.asarray(direction, float); d = d / np.linalg.norm(d)
    dirs = np.repeat(d[None], len(origins), 0)
    locs, ray_idx, tri_idx = m.ray.intersects_location(origins, dirs, multiple_hits=True)
    out = [[] for _ in range(len(origins))]
    if len(locs) == 0:
        return out
    t = np.einsum('ij,j->i', locs - origins[ray_idx], d)
    sgn = np.einsum('ij,j->i', m.face_normals[tri_idx], d)
    for r in np.unique(ray_idx):
        sel = ray_idx == r
        out[r] = _depth_intervals(t[sel], sgn[sel])
    return out


def clip_len(intervals, lo, hi):
    s = 0.0
    for a, b in intervals:
        s += max(0.0, min(b, hi) - max(a, lo))
    return s


def first_solid(intervals, lo=-1e9):
    xs = [max(a, lo) for a, b in intervals if b > lo]
    return min(xs) if xs else math.inf


# ---------------------------------------------------------------- sections
def section_polys(m: trimesh.Trimesh, origin, normal, heights, u, v):
    """Planar sections of m at origin+h*normal; returns list (per height) of shapely polygons in (u,v) coordinates
    plus a containment-depth for each polygon (even depth = solid region, odd depth = void inside solid)."""
    res = []
    for h in heights:
        seg = trimesh.intersections.mesh_plane(m, normal, np.asarray(origin) + h * np.asarray(normal))
        if len(seg) == 0:
            res.append([]); continue
        uv = np.stack([seg @ u, seg @ v], -1)
        ls = [LineString(s) for s in uv.round(5) if np.linalg.norm(s[0] - s[1]) > 1e-6]
        polys = list(polygonize(unary_union(ls)))
        exts = [Polygon(p.exterior) for p in polys]
        out = []
        for i, p in enumerate(polys):
            rp = p.representative_point()
            depth = sum(1 for j, e in enumerate(exts) if j != i and e.area > exts[i].area and e.contains(rp))
            out.append((p, depth))
        res.append(out)
    return res
