#!/usr/bin/env python3
"""Step 3b: proposed routes.json waypoint moves that clear the class (b) cable/part penetrations.

For each cable with a route shortcut, the movable waypoints (route points that are not a connector end and not
shared with another cable) are pushed out iteratively. At every drawn-spline sample (the viewer's centripetal
Catmull-Rom, cables.catmull_centripetal) closer than radius + MARGIN to a part solid, the outward direction from
the closest surface point is applied to the segment's two control points, weighted by the local spline
parameter; the raw polyline is pushed out the same way so both clear. Samples within END_MM of either cable end are terminal entries (class c) and are not pushed.
The result is re-verified on the whole cable against every audit solid with the same test as cables.py, for
both the drawn spline and the polyline. Writes cable-fix.json; routes.json is not edited.
"""
from __future__ import annotations

import gc
import json
import sys

import numpy as np
import trimesh

from cables import THRESH, arclen, catmull_centripetal, polyline_samples, runs, spline_samples
from ia_lib import GUIDE, HERE, aabb_overlap, load_guide, load_solid, manifest, rnd

MARGIN = 0.5
END_MM = 8.0
ROUTES = GUIDE / 'content' / 'routes.json'


class Meshes:
    def __init__(self, cap=10):
        self.c, self.cap = {}, cap

    def get(self, k):
        if k not in self.c:
            if len(self.c) >= self.cap:
                self.c.clear()
                gc.collect()
            v, f = load_solid(k)
            self.c[k] = trimesh.Trimesh(v, f, process=False)
        return self.c[k]


def guide_index_map(cid, R):
    """Guide cable path index -> (route key, route index, offset) for movable points, else None."""
    if cid in ('dxl-r5', 'dxl-l10', 'dxl-n12'):
        rid = {'dxl-r5': 'dxl5', 'dxl-l10': 'dxl10', 'dxl-n12': 'dxl12'}[cid]
        n = len(R[rid])
        # path[0] = OpenRB port mouth, path[i] = R[rid][i-1]; R[0] (plug exit) and R[-1] (servo socket) stay put
        return {i: (rid, i - 1, (0, 0, 0)) for i in range(2, n)}
    if cid == 'uart':
        n = len(R['uart_lower'])
        # path[0] = J12 pad, path[1..n] = uart_lower; the trunk/neck/head points after it are shared with pi-trunk/imu
        return {i: ('uart_lower', i - 1, (0, 0, 0)) for i in range(1, n + 1)}
    simple = {'orb-pwr': 'openrbpwr', 'i2s': 'head_i2s', 'dxl-14-15': 'ttl-15-14', 'dxl-11-13': 'ttl-13-11'}
    if cid in simple:
        rid = simple[cid]
        n = len(R[rid])
        return {i: (rid, i, (0, 0, 0)) for i in range(1, n - 1)}
    return {}


def spline_with_weights(P, step=0.4):
    """Drawn-spline samples plus raw-polyline samples, each with its segment index and local parameter."""
    L = sum(np.linalg.norm(P[i + 1] - P[i]) for i in range(len(P) - 1))
    n = max(100, int(L / step))
    t = np.linspace(0, 1, n)
    x, seg = catmull_centripetal(P, t)
    w = (len(P) - 1) * t - seg
    xp, sp, wp = [], [], []
    for i in range(len(P) - 1):
        m = max(2, int(np.ceil(np.linalg.norm(P[i + 1] - P[i]) / step)) + 1)
        tt = np.linspace(0, 1, m)
        xp.append(P[i] + (P[i + 1] - P[i]) * tt[:, None])
        sp.append(np.full(m, i))
        wp.append(tt)
    return np.vstack([x] + xp), np.concatenate([seg] + sp), np.clip(np.concatenate([w] + wp), 0, 1), len(x)


def probe(meshes, man, x, r, skip=()):
    """Signed distance (+ inside) and outward unit direction to the nearest violating part at each sample."""
    lo, hi = x.min(0) - r - 1, x.max(0) + r + 1
    best_sd = np.full(len(x), -np.inf)
    best_dir = np.zeros_like(x)
    best_part = np.array([''] * len(x), dtype=object)
    for k, m in man.items():
        if k in skip or not aabb_overlap(m['bounds'], [lo, hi]):
            continue
        b = np.array(m['bounds'])
        near = np.all((x >= b[0] - r - 1) & (x <= b[1] + r + 1), axis=1)
        if not near.any():
            continue
        mesh = meshes.get(k)
        idx = np.flatnonzero(near)
        for q in range(0, len(idx), 64):
            ii = idx[q:q + 64]
            cp, d, tid = trimesh.proximity.closest_point(mesh, x[ii])
            inside = mesh.contains(x[ii])
            sd = np.where(inside, d, -d)
            vec = x[ii] - cp
            nrm = np.linalg.norm(vec, axis=1)
            fn = mesh.face_normals[tid]
            dirs = np.where((nrm > 1e-6)[:, None], vec / np.maximum(nrm, 1e-9)[:, None], fn)
            # inside: x - cp points inward, so the outward push is cp - x
            dirs = np.where(inside[:, None] & (nrm > 1e-6)[:, None], -vec / np.maximum(nrm, 1e-9)[:, None], dirs)
            upd = sd > best_sd[ii]
            best_sd[ii[upd]] = sd[upd]
            best_dir[ii[upd]] = dirs[upd]
            best_part[ii[upd]] = k
    return best_sd, best_dir, best_part


def verify(meshes, man, path, r):
    out = []
    for mode, (x, seg) in (('drawn-spline', spline_samples(path)), ('polyline', polyline_samples(path))):
        s = arclen(x)
        lo, hi = x.min(0) - r - 0.2, x.max(0) + r + 0.2
        for k, m in man.items():
            if not aabb_overlap(m['bounds'], [lo, hi]):
                continue
            b = np.array(m['bounds'])
            near = np.all((x >= b[0] - r - 0.2) & (x <= b[1] + r + 0.2), axis=1)
            if not near.any():
                continue
            mesh = meshes.get(k)
            sd = np.full(len(x), -np.inf)
            idx = np.flatnonzero(near)
            for q in range(0, len(idx), 64):
                sd[idx[q:q + 64]] = trimesh.proximity.signed_distance(mesh, x[idx[q:q + 64]])
            depth = sd + r
            for i, j in runs(depth > THRESH):
                kk = i + int(np.argmax(depth[i:j + 1]))
                out.append({'mode': mode, 'part': k, 'segments': sorted({int(v) for v in seg[i:j + 1]}),
                            'depthMm': rnd(depth[kk], 3), 'deepestPoint': rnd(x[kk], 2),
                            'atEnd': 'start' if s[i] < END_MM else ('end' if s[-1] - s[j] < END_MM else None)})
    return out


def optimise(meshes, man, path, r, movable, iters=40):
    P = np.array(path, float)
    mov = np.zeros(len(P), bool)
    mov[list(movable)] = True
    hist = []
    active = None  # segments to probe after the first full pass: those that violated, and their neighbours
    for it in range(iters):
        x, seg, w, ns = spline_with_weights(P)
        s = np.concatenate([arclen(x[:ns]), arclen(x[ns:])])  # arc length along the spline, then along the polyline
        s_end = np.r_[np.full(ns, arclen(x[:ns])[-1]), np.full(len(x) - ns, arclen(x[ns:])[-1])]
        sel = np.ones(len(x), bool) if active is None else np.isin(seg, sorted(active))
        sd = np.full(len(x), -np.inf)
        d = np.zeros_like(x)
        if sel.any():
            sd[sel], d[sel], _ = probe(meshes, man, x[sel], r)
        need = sd + r + MARGIN
        ok_end = (s > END_MM) & (s < s_end - END_MM)
        viol = (need > 0) & ok_end
        hist.append({'iter': it, 'violatingSamples': int(viol.sum()), 'worstMm': rnd(float(need[ok_end].max()), 3)})
        if not viol.any():
            if active is None:
                break
            active = None  # confirm on the whole cable before stopping
            continue
        vs = {int(q) for q in seg[viol]}
        active = (active or set()) | {q + dq for q in vs for dq in (-1, 0, 1) if 0 <= q + dq < len(P) - 1}
        acc = np.zeros_like(P)
        wsum = np.zeros(len(P))
        for k in np.flatnonzero(viol):
            i = int(seg[k])
            for j, b in ((i, 1 - w[k]), (i + 1, w[k])):
                if mov[j] and b > 0.05:
                    acc[j] += b * need[k] * d[k]
                    wsum[j] += b
        moved = False
        for j in np.flatnonzero(wsum > 0):
            step = acc[j] / wsum[j] * 1.3
            n = np.linalg.norm(step)
            if n > 1.5:
                step *= 1.5 / n
            P[j] += step
            moved = True
        if not moved:
            break
    return P, hist


TARGETS = ['dxl-r5', 'dxl-l10', 'dxl-n12', 'uart', 'orb-pwr', 'i2s', 'dxl-14-15', 'dxl-11-13']


def main():
    g = load_guide()
    man = manifest()
    R = json.loads(ROUTES.read_text())['routes']
    meshes = Meshes()
    only = sys.argv[1:] or TARGETS
    res = []
    for c in g['cables']:
        if c['id'] not in only:
            continue
        r = float(c.get('radius') or 0.9)
        path = np.array(c['path'], float)
        imap = guide_index_map(c['id'], R)
        P, hist = optimise(meshes, man, path, r, imap.keys())
        before = [f for f in verify(meshes, man, path, r)]
        after = verify(meshes, man, P, r)
        moves = []
        for i, (rid, ri, off) in sorted(imap.items()):
            old = R[rid][ri]
            new = [round(float(v) - o, 1) for v, o in zip(P[i], off)]
            if max(abs(a - b) for a, b in zip(old, new)) >= 0.1:
                moves.append({'route': rid, 'index': ri, 'from': old, 'to': new, 'moveMm': rnd(float(np.linalg.norm(np.subtract(new, old))), 2)})
        L0 = float(np.sum(np.linalg.norm(np.diff(path, axis=0), axis=1)))
        L1 = float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1)))
        mid = lambda fs: [f for f in fs if f['atEnd'] is None]
        rec = {'cable': c['id'], 'radius': r, 'iterations': hist[-1]['iter'] + 1, 'converged': hist[-1]['violatingSamples'] == 0,
               'lastIteration': hist[-1], 'waypointMoves': moves, 'polylineLengthMm': [rnd(L0, 1), rnd(L1, 1)],
               'midRouteFindingsBefore': mid(before), 'midRouteFindingsAfter': mid(after),
               'endFindingsAfter': [f for f in after if f['atEnd']]}
        res.append(rec)
        print(c['id'], 'converged', rec['converged'], 'moves', len(moves), 'mid before', len(mid(before)), 'after', len(mid(after)),
              file=sys.stderr, flush=True)
    out = HERE / 'cable-fix.json'
    prev = json.loads(out.read_text()) if out.exists() else {'margin': MARGIN, 'endWindowMm': END_MM, 'cables': []}
    done = {r['cable'] for r in res}
    prev['cables'] = [r for r in prev['cables'] if r['cable'] not in done] + res
    out.write_text(json.dumps(prev, indent=1))


if __name__ == '__main__':
    main()
