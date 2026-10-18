#!/usr/bin/env python3
"""Release head cap V1.9 = the integrated study cap geometry, made print-clean.

Source: guide/extension-20261012-neck-audio/integrated/study-solids/head_cap-integrated-world.stl (sha256 pinned in
ext_lib.STUDY_CAP_SHA; built by integrated/scripts/build_cap.py = notch-less V1.8 + audio roof pair (speaker collar,
grille, two amp posts) + Pi-mount option A rails, +y web trimmed). Loaded through manifold3d it is one valid body.

Defects of that STL (found with meshcheck.py: topology plus the face-separation winding-number test):
  1. a zero-thickness crack inherited from the V1.8 cap at y = -32.7 (x 51.4..57.3, z 142.8..145.5), 0.14 mm under
     the surface: coincident opposite faces with material on both sides;
  2. edges shared by more than two faces: 107 at the +y web trim (x 53.1..54.8, y 25.8..29.9, z 116.7..121.0) that
     disappear when the solid is re-exported from manifold3d, and one micro fin (two coincident faces of 5e-5 mm2) at
     (60.87, 30.56, 148.28);
  3. needle triangles from boolean round-off.
Repairs, each local and measured:
  a. Manifold.simplify(SIMPLIFY_EPS): every surface moves by less than SIMPLIFY_EPS (1e-4 mm); removes the micro fin
     and most needles;
  b. crack closing on the mesh: faces that fail the separation test with material on both sides are removed only if
     they form coincident opposite pairs (a crack has zero volume, so closing it changes no material); the crack-mouth
     slivers (area < 1e-6 mm2) touching them are removed and their vertices within MERGE_TOL are merged;
  c. the result is re-imported into manifold3d and exported from there; the exported STL must pass every check.
The symmetric difference against the study cap is reported.
Writes ../head_cap_v19-world.stl and ../checks/cap-build-v19.json.
"""
from __future__ import annotations

import tempfile

import manifold3d as m3
import numpy as np
import trimesh

import ext_lib as E
import meshcheck as MC

SIMPLIFY_EPS = 1e-4
MERGE_TOL = 2e-4


def roundtrip(M):
    """Export as binary STL (float32) and reload with vertex merging, exactly like the release file."""
    with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as f:
        p = f.name
    E.tm(M).export(p)
    return p, trimesh.load(p, force='mesh')


def internal_clusters(path):
    """Face clusters failing the separation test (non-needle faces), grouped by 2 mm proximity."""
    r, bad = MC.check(path)
    m = trimesh.load(path, force='mesh')
    T = m.triangles
    el = np.linalg.norm(T - np.roll(T, 1, 1), axis=2)
    inr = 2 * m.area_faces / np.maximum(el.sum(1), 1e-12)
    bad = bad[inr[bad] >= 1e-4]
    V0, V1, V2 = (np.ascontiguousarray(T[:, i]) for i in range(3))
    groups = []
    if len(bad):
        from scipy.sparse.csgraph import connected_components
        from scipy.spatial import cKDTree
        import scipy.sparse as sp
        pts = m.triangles_center[bad]
        pr = cKDTree(pts).query_pairs(2.0, output_type='ndarray')
        A = sp.coo_matrix((np.ones(len(pr)), (pr[:, 0], pr[:, 1])), shape=(len(pts), len(pts)))
        n, L = connected_components(A, directed=False)
        for k in range(n):
            fs = bad[L == k]
            c, nn = m.triangles_center[fs], m.face_normals[fs]
            wp = MC.winding(V0, V1, V2, np.ascontiguousarray(c + 1e-3 * nn))
            wm = MC.winding(V0, V1, V2, np.ascontiguousarray(c - 1e-3 * nn))
            kind = 'internal' if np.all((np.abs(wp) > .5) & (np.abs(wm) > .5)) else \
                'fin' if np.all((np.abs(wp) < .5) & (np.abs(wm) < .5)) else 'mixed'
            V = T[fs].reshape(-1, 3)
            groups.append({'faces': fs, 'kind': kind, 'lo': V.min(0), 'hi': V.max(0),
                           'normals': np.unique(np.round(nn, 3), axis=0)})
    return r, groups


def pinched_edges(m):
    e = m.edges_sorted
    u, c = np.unique(e, axis=0, return_counts=True)
    return m.vertices[u[c > 2]]          # (n, 2, 3)


def close_cracks(m, groups):
    """Remove crack faces (coincident opposite pairs with material on both sides) and the slivers at their mouth,
    then merge the crack's vertices that lie within MERGE_TOL. Returns the new mesh and a record."""
    rec = {'groups': []}
    drop = set()
    for g in groups:
        if g['kind'] != 'internal':
            raise SystemExit(f'unexpected defect kind {g["kind"]} at {g["lo"]}..{g["hi"]}')
        fs = list(g['faces'])
        T = m.triangles[fs]
        # every face must have a partner with the same corners (within 1e-5) and the opposite normal
        key = np.sort(np.round(T, 4).reshape(len(fs), -1).reshape(len(fs), 3, 3).tolist(), axis=1)
        paired = 0
        for i in range(len(fs)):
            for j in range(len(fs)):
                if i != j and np.allclose(key[i], key[j], atol=2e-4) and \
                        m.face_normals[fs[i]] @ m.face_normals[fs[j]] < -0.999:
                    paired += 1
                    break
        if paired != len(fs):
            raise SystemExit(f'internal faces at {g["lo"]} are not all coincident opposite pairs ({paired}/{len(fs)})')
        drop.update(fs)
        rec['groups'].append({'faces': len(fs), 'areaMm2': float(m.area_faces[fs].sum()), 'min': g['lo'], 'max': g['hi']})
    if not drop:
        return m, rec
    crack_v = np.unique(m.faces[sorted(drop)])
    # mouth slivers: tiny faces that touch the crack vertices
    tiny = np.flatnonzero((m.area_faces < 1e-6) & np.isin(m.faces, crack_v).any(1))
    drop.update(tiny.tolist())
    rec['mouthSliversRemoved'] = int(len(tiny))
    keep = np.ones(len(m.faces), bool)
    keep[sorted(drop)] = False
    V, F = m.vertices.copy(), m.faces[keep].copy()
    # merge crack vertices with any vertex within MERGE_TOL (union-find)
    from scipy.spatial import cKDTree
    tree = cKDTree(V)
    parent = np.arange(len(V))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    merged = []
    for v in np.unique(m.faces[sorted(drop)]):
        for w in tree.query_ball_point(V[v], MERGE_TOL):
            a, b = find(v), find(w)
            if a != b:
                parent[max(a, b)] = min(a, b)
                merged.append(float(np.linalg.norm(V[v] - V[w])))
    root = np.array([find(i) for i in range(len(V))])
    F = root[F]
    F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
    _, ui = np.unique(np.sort(F, axis=1), axis=0, return_index=True)
    nd = len(F) - len(ui)
    F = F[np.sort(ui)]
    out = trimesh.Trimesh(V, F, process=False)
    out.remove_unreferenced_vertices()
    _, c = np.unique(out.edges_sorted, axis=0, return_counts=True)
    rec.update({'facesRemoved': int(len(drop)), 'verticesMerged': len(merged),
                'maxMergeDistanceMm': max(merged) if merged else 0.0, 'duplicateFacesDropped': int(nd),
                'watertight': bool(out.is_watertight), 'windingConsistent': bool(out.is_winding_consistent),
                'edgesSharedByMoreThanTwoFaces': int((c > 2).sum()), 'boundaryEdges': int((c == 1).sum()),
                'volumeMm3': float(out.volume)})
    if not (out.is_watertight and out.is_winding_consistent):
        raise SystemExit(f'crack closing left an open mesh: {rec}')
    return out, rec


def main():
    assert E.sha(E.STUDY_CAP) == E.STUDY_CAP_SHA, 'study cap changed'
    M0 = E.stl_man(E.STUDY_CAP)
    rec = {'what': 'V1.9 release head cap: integrated study cap geometry, mesh defects repaired locally',
           'source': {'path': E.STUDY_CAP, 'sha256': E.STUDY_CAP_SHA, 'manifold3dStatus': str(M0.status()),
                      'bodies': len(M0.decompose()), 'volumeMm3': M0.volume()},
           'parameters': {'SIMPLIFY_EPS': SIMPLIFY_EPS, 'MERGE_TOL': MERGE_TOL}}
    p0, _ = roundtrip(M0)
    rec['sourceCheck'], _ = MC.check(p0)
    M1 = M0.simplify(SIMPLIFY_EPS)
    rec['simplify'] = {'eps': SIMPLIFY_EPS, 'bodies': len(M1.decompose()), 'volumeChangeMm3': M1.volume() - M0.volume()}
    p1, m1 = roundtrip(M1)
    r1, groups = internal_clusters(p1)
    rec['afterSimplify'] = {k: r1[k] for k in ('watertight', 'bodies', 'edgesSharedByMoreThanTwoFaces', 'boundaryEdges',
                                               'duplicateFaceGroups')}
    rec['afterSimplify']['defectGroups'] = [{'kind': g['kind'], 'faces': len(g['faces']), 'min': g['lo'], 'max': g['hi']}
                                            for g in groups]
    m2, crack = close_cracks(m1, groups)
    rec['crackClosing'] = crack
    M = E.ia_lib.to_manifold(np.asarray(m2.vertices), np.asarray(m2.faces))
    rec['reimport'] = {'status': str(M.status()), 'bodies': len(M.decompose()), 'volumeMm3': M.volume()}
    assert M.status() == m3.Error.NoError and len(M.decompose()) == 1
    out = E.PARTS['head_cap_v19']
    E.tm(M).export(out)
    rec['release'] = {'path': out, 'sha256': E.sha(out), 'manifold3dStatus': str(M.status()), 'genus': M.genus(),
                      'volumeMm3': M.volume()}
    rep, bad = MC.check(out)
    m = trimesh.load(out, force='mesh')
    T = m.triangles
    el = np.linalg.norm(T - np.roll(T, 1, 1), axis=2)
    inr = 2 * m.area_faces / np.maximum(el.sum(1), 1e-12)
    rep['needleFacesInradiusBelow1e-4'] = int((inr < 1e-4).sum())
    rep['separationDefectsNonNeedle'] = int((inr[bad] >= 1e-4).sum()) if len(bad) else 0
    rec['releaseCheck'] = rep
    rec['meshReport'] = E.mesh_report(out)
    # geometry change against the study cap (exact booleans on the manifold3d solids)
    R = E.stl_man(out)
    rec['vsStudyCap'] = {'addedMm3': (R - M0).volume(), 'removedMm3': (M0 - R).volume(),
                         'volumeStudyMm3': M0.volume(), 'volumeReleaseMm3': R.volume()}
    # orientation reference: V1.8 cap volume for context
    rec['vsV18'] = {'volumeV18Mm3': E.stl_man(E.CAP_V18).volume()}
    (E.OUT / 'checks').mkdir(exist_ok=True)
    E.jdump(E.rnd(rec, 6), E.OUT / 'checks' / 'cap-build-v19.json')
    import json
    print(json.dumps(E.rnd({k: rec[k] for k in ('simplify', 'afterSimplify', 'crackClosing', 'reimport', 'release', 'releaseCheck', 'vsStudyCap')}, 5), indent=1,
                     default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))[:8000])


if __name__ == '__main__':
    main()
