"""Candidate print poses for the V1.12 White plate, written to pose-sources.json (read by make_manifest.py and the
orientation check). Read-only on every source.

    /tmp/microduck-cad-venv/bin/python scripts/pose_sources.py

- shell_left_v20 / shell_right_v20 (world frame): the 10/1 pose is the rigid transform that maps the printed shell as the
  guide drew it before V1.12 (full-build export, the same solid v20-source was built from) onto the 10/1 print STL
  community-8.stl / community-10.stl. Found by ICP on the unique vertices and re-orthonormalised; the residual is
  recorded (float32 export rounding). 'outer face down' turns that pose by the smallest rotation that lays the largest flat
  facet within 5 degrees of the bed exactly on it: the 10/1 left shell stood on one edge of its flat outer side face
  (8.8 mm2 contact, not self-standing), 2 degrees off.
- head_cap_v19_white (world frame, the V1.9 cap STL reprinted white): the V1.9 cap pose, release-V1.9/manifest-V1.9.json head_cap_v19.sourceToPrint.
- thigh_left / thigh_right (stock STL, already in the 10/1 print pose): identity. The 10-SURFACE-QUALITY side pose
  (59.4 mm tall, about 466 mm2 first layer, rear-centre seats off support) is among the poses orientation_check.py generates
  ('stable p=0.06'), so it needs no entry here.
"""
import base64, hashlib, itertools, json
from pathlib import Path
import numpy as np, trimesh
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
PRINT = HERE.parents[1]
SIM = PRINT.parents[1]
BP = SIM / 'build-pack-20260913'
STOCK = BP / 'assembly/print-parts'
V19 = json.loads((PRINT / 'release-V1.9/manifest-V1.9.json').read_text())
# The guide data before V1.12 (sha256 aaf3d6ba..., gate receipt 2026-10-14 17:30) drew the printed 10/1 shells from the
# full-build export. Its copy is kept with the release so the registration stays reproducible.
OLD_GUIDE = HERE / 'guide-data-aaf3d6ba-shells.json'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def orthonormal(T):
    U, _, Vt = np.linalg.svd(T[:3, :3]); R = U @ Vt
    out = np.eye(4); out[:3, :3] = R; out[:3, 3] = T[:3, 3]
    return out


def register(world_v, stock_v):
    cw, cs = world_v.mean(0), stock_v.mean(0)
    Uw = np.linalg.svd((world_v - cw).T @ (world_v - cw))[0]; Us = np.linalg.svd((stock_v - cs).T @ (stock_v - cs))[0]
    best = None
    for sg in itertools.product([1, -1], repeat=3):
        R = Us @ np.diag(sg) @ Uw.T
        if np.linalg.det(R) < 0:
            continue
        T = np.eye(4); T[:3, :3] = R; T[:3, 3] = cs - R @ cw
        M, _, cost = trimesh.registration.icp(world_v, stock_v, initial=T, max_iterations=80, threshold=1e-10)
        if best is None or cost < best[1]:
            best = (M, cost)
    M = orthonormal(best[0])
    tree = cKDTree(stock_v)
    for _ in range(5):   # translation refinement after orthonormalising
        tw = trimesh.transform_points(world_v, M); M[:3, 3] += (stock_v[tree.query(tw)[1]] - tw).mean(0)
    tw = trimesh.transform_points(world_v, M)
    return M, float(max(tree.query(tw)[0].max(), cKDTree(tw).query(stock_v)[0].max()))


def face_down(path, T, max_deg=5.0):
    m = trimesh.load(path, force='mesh'); R = np.array(T)[:3, :3]
    near = [(a, n) for n, a in zip(m.facets_normal, m.facets_area) if np.degrees(np.arccos(np.clip(R @ n @ [0, 0, -1], -1, 1))) < max_deg]
    area, n = max(near, key=lambda x: x[0])
    a = R @ n; b = np.array([0, 0, -1.]); v = np.cross(a, b); c = float(a @ b)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    out = np.array(T, float); out[:3, :3] = (np.eye(3) + K + K @ K / (1 + c)) @ R
    return orthonormal(out), float(np.degrees(np.arccos(np.clip(c, -1, 1)))), float(area), n.round(4).tolist()


def main():
    old = json.loads(OLD_GUIDE.read_text())
    out = {'_doc': __doc__.strip(), 'oldGuideShells': {'path': str(OLD_GUIDE), 'sha256': sha(OLD_GUIDE)}, 'poses': {}}
    for key, stock in (('shell_left_v20', 'community-8.stl'), ('shell_right_v20', 'community-10.stl')):
        p = old['parts'][key.replace('_v20', '')]
        wv = np.unique(np.frombuffer(base64.b64decode(p['positionB64']), '<f4').reshape(-1, 3).astype(float), axis=0)
        sv = np.unique(trimesh.load(STOCK / stock, process=False).vertices, axis=0)
        M, dev = register(wv, sv)
        out['poses'][key] = {'10/1 pose': {'sourceToPrint': M.tolist(), 'registeredTo': str(STOCK / stock), 'registeredToSha256': sha(STOCK / stock),
                                            'maxVertexDeviationMm': dev, 'worldVertices': len(wv), 'stockVertices': len(sv)}}
        F, deg, area, n = face_down(PRINT / f'v20-source/{key}-world.stl', M)
        out['poses'][key]['outer face down'] = {'sourceToPrint': F.tolist(), 'from': '10/1 pose', 'turnDeg': deg, 'facetAreaMm2': area, 'facetNormalWorld': n}
    cap = next(p for p in V19['parts'] if p['key'] == 'head_cap_v19')
    out['poses']['head_cap_v19_white'] = {'V1.9 pose': {'sourceToPrint': cap['sourceToPrint'], 'from': 'release-V1.9/manifest-V1.9.json head_cap_v19',
                                                  'poseOrigin': cap['poseOrigin'], 'flatContactMinimumMm2': cap['flatContact']['minimumAreaMm2']}}
    for key in ('thigh_left', 'thigh_right'):
        out['poses'][key] = {'10/1 pose': {'sourceToPrint': np.eye(4).tolist(), 'note': 'the stock STL is the 10/1 print pose'}}
    (HERE / 'pose-sources.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: {n: v.get('maxVertexDeviationMm') for n, v in d.items()} for k, d in out['poses'].items()}, indent=1))


if __name__ == '__main__':
    main()
