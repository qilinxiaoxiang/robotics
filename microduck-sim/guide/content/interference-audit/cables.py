#!/usr/bin/env python3
"""Step 3: cable tubes against part solids, in the final scene.

The viewer draws each cable as a THREE.TubeGeometry of radius r (default 0.9 mm) around a centripetal
Catmull-Rom curve through the route points (viewer/app.js). Both that drawn curve and the raw polyline are
sampled at <= 0.25 mm spacing. At each sample the signed distance to every nearby audit solid is computed
(exact closest point on the closed mesh; inside/outside by ray parity), giving tube penetration
depth = r + (distance inside, negative outside). A run of samples with depth > 0.1 mm is one finding; the run
records the route segment index i (between path[i] and path[i+1]), the deepest point, whether the centreline
itself is inside the solid (the cable passes through material) and the length of centreline inside.
Writes cables-raw.json.
"""
from __future__ import annotations

import json
import math
import sys

import numpy as np
import trimesh

from ia_lib import HERE, aabb_overlap, alternate_of, apart, load_guide, load_solid, manifest, rnd

THRESH = 0.1


def catmull_centripetal(points: np.ndarray, t: np.ndarray):
    """THREE.CatmullRomCurve3(points, false, 'centripetal').getPoint(t), vectorised. Returns (xyz, segment index)."""
    P = np.asarray(points, float)
    l = len(P)
    p = (l - 1) * t
    ip = np.floor(p).astype(int)
    w = p - ip
    end = (w == 0) & (ip == l - 1)
    ip[end] = l - 2
    w[end] = 1.0
    ip = np.clip(ip, 0, l - 2)
    p1, p2 = P[ip], P[ip + 1]
    p0 = np.where((ip > 0)[:, None], P[np.maximum(ip - 1, 0)], 2 * P[0] - P[1])
    p3 = np.where((ip + 2 < l)[:, None], P[np.minimum(ip + 2, l - 1)], 2 * P[-1] - P[-2])
    dt0 = np.sum((p1 - p0) ** 2, 1) ** 0.25
    dt1 = np.sum((p2 - p1) ** 2, 1) ** 0.25
    dt2 = np.sum((p3 - p2) ** 2, 1) ** 0.25
    dt1 = np.where(dt1 < 1e-4, 1.0, dt1)
    dt0 = np.where(dt0 < 1e-4, dt1, dt0)
    dt2 = np.where(dt2 < 1e-4, dt1, dt2)
    dt0, dt1, dt2 = dt0[:, None], dt1[:, None], dt2[:, None]
    t1 = ((p1 - p0) / dt0 - (p2 - p0) / (dt0 + dt1) + (p2 - p1) / dt1) * dt1
    t2 = ((p2 - p1) / dt1 - (p3 - p1) / (dt1 + dt2) + (p3 - p2) / dt2) * dt1
    c0, c1 = p1, t1
    c2 = -3 * p1 + 3 * p2 - 2 * t1 - t2
    c3 = 2 * p1 - 2 * p2 + t1 + t2
    ww = w[:, None]
    return c0 + c1 * ww + c2 * ww ** 2 + c3 * ww ** 3, ip


def polyline_samples(points, step=0.25):
    P = np.asarray(points, float)
    xs, segs = [], []
    for i in range(len(P) - 1):
        n = max(2, int(math.ceil(np.linalg.norm(P[i + 1] - P[i]) / step)) + 1)
        tt = np.linspace(0, 1, n)[:-1] if i < len(P) - 2 else np.linspace(0, 1, n)
        xs.append(P[i] + (P[i + 1] - P[i]) * tt[:, None])
        segs.append(np.full(len(tt), i))
    return np.vstack(xs), np.concatenate(segs)


def spline_samples(points, step=0.25):
    P = np.asarray(points, float)
    L = sum(np.linalg.norm(P[i + 1] - P[i]) for i in range(len(P) - 1))
    n = max(200, int(L / step) * 3)
    t = np.linspace(0, 1, n)
    return catmull_centripetal(P, t)


def runs(mask):
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j + 1 < len(mask) and mask[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def arclen(x):
    return np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(x, axis=0), axis=1))])


def main():
    g = load_guide()
    man = manifest()
    alt = alternate_of(g)   # a bench-box cable never meets the battery backpack
    meshes = {}

    def mesh(k):
        if k not in meshes:
            if len(meshes) > 12:
                meshes.clear()
                import gc; gc.collect()
            v, f = load_solid(k)
            meshes[k] = trimesh.Trimesh(v, f, process=False)
        return meshes[k]

    findings, coverage = [], []
    for c in g['cables']:
        r = float(c.get('radius') or 0.9)
        rec_cov = {'cable': c['id'], 'radius': r, 'points': len(c['path'])}
        for mode, (x, seg) in (('drawn-spline', spline_samples(c['path'])), ('polyline', polyline_samples(c['path']))):
            s = arclen(x)
            lo, hi = x.min(0) - r - 0.2, x.max(0) + r + 0.2
            cand = [k for k, m in man.items() if aabb_overlap(m['bounds'], [lo, hi]) and not apart(alt, c['id'], k)]
            rec_cov[mode + 'Samples'] = int(len(x))
            rec_cov[mode + 'CandidateParts'] = len(cand)
            for k in cand:
                b = np.array(man[k]['bounds'])
                near = np.all((x >= b[0] - r - 0.2) & (x <= b[1] + r + 0.2), axis=1)
                if not near.any():
                    continue
                m = mesh(k)
                sd = np.full(len(x), -np.inf)
                idx = np.flatnonzero(near)
                for q in range(0, len(idx), 64):  # small batches keep trimesh's candidate lists bounded
                    sd[idx[q:q + 64]] = trimesh.proximity.signed_distance(m, x[idx[q:q + 64]])  # + inside
                depth = sd + r
                for i, j in runs(depth > THRESH):
                    kk = i + int(np.argmax(depth[i:j + 1]))
                    inside = sd[i:j + 1] > 0
                    findings.append({
                        'cable': c['id'], 'mode': mode, 'part': k, 'radius': r,
                        'segments': sorted({int(q) for q in seg[i:j + 1]}),
                        'depthMm': rnd(depth[kk], 3), 'centrelineInside': bool(inside.any()),
                        'centrelineInsideMm': rnd(float(np.sum(np.diff(s[i:j + 1])[inside[:-1]])) if j > i else 0.0, 2),
                        'runLengthMm': rnd(s[j] - s[i], 2), 'startArcMm': rnd(s[i], 1), 'endArcMm': rnd(s[j], 1),
                        'cableLengthMm': rnd(s[-1], 1),
                        'deepestPoint': rnd(x[kk], 2), 'runStart': rnd(x[i], 2), 'runEnd': rnd(x[j], 2),
                        'atEnd': 'start' if s[i] < 8 else ('end' if s[-1] - s[j] < 8 else None),
                    })
        coverage.append(rec_cov)
        print(c['id'], 'done', file=sys.stderr, flush=True)
    (HERE / 'cables-raw.json').write_text(json.dumps({'threshold': THRESH, 'coverage': coverage, 'findings': findings}, indent=1))
    print(json.dumps({'cables': len(coverage), 'findings': len(findings)}))


if __name__ == '__main__':
    main()
