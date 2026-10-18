#!/usr/bin/env python3
"""Release-mesh integrity check on an exported STL (what a slicer reads).

Topology (trimesh, vertices merged by position as slicers do): watertight, consistent winding, bodies, edges shared by
more than two faces, boundary edges, degenerate faces, Euler number.
Zero-volume fins and internal coincident faces: every face must separate inside from outside. For each face with
area > 1e-8 mm2 the generalized winding number of the whole mesh (Jacobson et al. 2013; exact sum of triangle solid
angles, Van Oosterom & Strackee) is evaluated at centroid + eps * normal and centroid - eps * normal. A real boundary
face gives w(+) ~ 0 (outside) and w(-) ~ 1 (inside). A zero-volume fin or a sheet spanning a cavity gives 0 / 0, an
internal face inside material gives 1 / 1, an inverted face 1 / 0. Membrane pairs cancel in the winding number, so the
test measures the true solid even when such faces exist. Two eps values (1e-3 and 1e-4 mm) are run; a face is a defect
only when it fails at both (a sliver triangle near a concave edge can fail at one eps without being a defect).
Needle faces (inradius < 1e-4 mm) are counted but not probed (the probe is meaningless at that size; they enclose no
volume). Duplicate faces: same three vertices after merging; coincident faces: same corner coordinates rounded to
1e-4 mm, either orientation (catches zero-thickness sheets whose two sides use different vertex indices).
clean = watertight, consistent winding, one body, no edge shared by more than two faces, no boundary edge, no duplicate
or coincident faces, and no probed face failing the separation test.
Usage: meshcheck.py file.stl [more.stl ...] [--json out.json]
"""
from __future__ import annotations

import json
import sys

import numba
import numpy as np
import trimesh


@numba.njit(parallel=True, fastmath=False, cache=False)
def winding(V0, V1, V2, P):
    n = P.shape[0]
    out = np.zeros(n)
    for i in numba.prange(n):
        px, py, pz = P[i, 0], P[i, 1], P[i, 2]
        s = 0.0
        for t in range(V0.shape[0]):
            ax, ay, az = V0[t, 0] - px, V0[t, 1] - py, V0[t, 2] - pz
            bx, by, bz = V1[t, 0] - px, V1[t, 1] - py, V1[t, 2] - pz
            cx, cy, cz = V2[t, 0] - px, V2[t, 1] - py, V2[t, 2] - pz
            la = np.sqrt(ax * ax + ay * ay + az * az)
            lb = np.sqrt(bx * bx + by * by + bz * bz)
            lc = np.sqrt(cx * cx + cy * cy + cz * cz)
            det = ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)
            den = la * lb * lc + (ax * bx + ay * by + az * bz) * lc + (ax * cx + ay * cy + az * cz) * lb \
                + (bx * cx + by * cy + bz * cz) * la
            s += 2.0 * np.arctan2(det, den)
        out[i] = s / (4.0 * np.pi)
    return out


def check(path, eps_list=(1e-3, 1e-4)):
    m = trimesh.load(path, force='mesh')            # process=True merges coincident vertices
    e = m.edges_sorted
    _, c = np.unique(e, axis=0, return_counts=True)
    area = m.area_faces
    res = {'path': str(path), 'faces': int(len(m.faces)), 'vertices': int(len(m.vertices)),
           'watertight': bool(m.is_watertight), 'windingConsistent': bool(m.is_winding_consistent),
           'bodies': len(m.split(only_watertight=False)), 'edgesSharedByMoreThanTwoFaces': int((c > 2).sum()),
           'boundaryEdges': int((c == 1).sum()), 'degenerateFacesArea<1e-8': int((area < 1e-8).sum()),
           'eulerNumber': int(m.euler_number), 'volumeMm3': float(m.volume) if m.is_watertight else None}
    fs = np.sort(m.faces, axis=1)
    _, cf = np.unique(fs, axis=0, return_counts=True)
    res['duplicateFaceGroups'] = int((cf > 1).sum())
    T = m.triangles
    V0, V1, V2 = (np.ascontiguousarray(T[:, i]) for i in range(3))
    # coincident faces by geometry (corner coordinates rounded to 1e-4 mm, any orientation)
    q = np.round(T * 1e4).astype(np.int64)                         # (n, 3 corners, 3)
    order = np.lexsort((q[:, :, 2], q[:, :, 1], q[:, :, 0]), axis=-1)
    key = np.take_along_axis(q, order[:, :, None], axis=1).reshape(len(T), 9)
    _, cg = np.unique(key, axis=0, return_counts=True)
    res['coincidentFaceGroupsByGeometry'] = int((cg > 1).sum())
    # needles: inradius < 1e-4 mm; the +-eps probe is meaningless for them, they enclose no volume and slicers drop them
    el = np.linalg.norm(T - np.roll(T, 1, 1), axis=2)
    inr = 2 * area / np.maximum(el.sum(1), 1e-12)
    res['needleFacesInradiusBelow1e-4'] = int((inr < 1e-4).sum())
    nd = inr < 1e-4
    res['needleTotalAreaMm2'] = float(area[nd].sum())
    res['needleMaxEdgeMm'] = float(el[nd].max()) if nd.any() else 0.0
    ok = inr >= 1e-4
    idx = np.flatnonzero(ok)
    cen = m.triangles_center[idx]
    nrm = m.face_normals[idx]
    fail_all = np.ones(len(idx), bool)
    per_eps = {}
    kinds = None
    for eps in eps_list:
        wp = winding(V0, V1, V2, np.ascontiguousarray(cen + eps * nrm))
        wm = winding(V0, V1, V2, np.ascontiguousarray(cen - eps * nrm))
        bad = ~((np.abs(wp) < 0.5) & (np.abs(wm - 1) < 0.5))
        per_eps[str(eps)] = int(bad.sum())
        fail_all &= bad
        if kinds is None:
            kinds = (wp, wm)
    wp, wm = kinds
    fb = np.flatnonzero(fail_all)
    out_p, out_m = np.abs(wp[fb]) < 0.5, np.abs(wm[fb]) < 0.5
    res['faceSeparationTest'] = {
        'facesTested': int(len(idx)), 'failingPerEps': per_eps, 'defectFacesFailingAllEps': int(len(fb)),
        'finBothSidesOutside': int((out_p & out_m).sum()), 'internalBothSidesInside': int((~out_p & ~out_m).sum()),
        'inverted': int((~out_p & out_m).sum()),
        'defectAreaMm2': float(area[idx[fb]].sum()),
        'defectBounds': [m.triangles_center[idx[fb]].min(0).round(3).tolist(),
                         m.triangles_center[idx[fb]].max(0).round(3).tolist()] if len(fb) else None,
        'windingNumberRangeOutsideSide': [float(wp.min()), float(wp.max())],
        'windingNumberRangeInsideSide': [float(wm.min()), float(wm.max())]}
    pv = m.vertices[np.unique(e, axis=0)[c > 2]].reshape(-1, 3)
    res['pinchedEdgeBounds'] = [pv.min(0).round(3).tolist(), pv.max(0).round(3).tolist()] if len(pv) else None
    res['clean'] = bool(res['watertight'] and res['windingConsistent'] and res['bodies'] == 1
                        and res['edgesSharedByMoreThanTwoFaces'] == 0 and res['boundaryEdges'] == 0
                        and res['duplicateFaceGroups'] == 0 and res['coincidentFaceGroupsByGeometry'] == 0
                        and len(fb) == 0)
    return res, (idx[fb] if len(fb) else np.array([], int))


def main():
    args = sys.argv[1:]
    out = None
    if '--json' in args:
        k = args.index('--json')
        out = args[k + 1]
        args = args[:k] + args[k + 2:]
    allr = []
    for p in args:
        r, _ = check(p)
        allr.append(r)
        print(json.dumps(r, indent=1), flush=True)
    if out:
        with open(out, 'w') as f:
            json.dump(allr, f, indent=1)


if __name__ == '__main__':
    main()
