"""Enumerate head_cap print poses: current (identity in the print-STL frame), rim-down (world open side on the bed),
and trimesh stable poses. Per pose: flat contact area within 0.02 mm (downward-facing triangles), contact convex-hull
area, height, centre-of-mass height, CoM margin inside the contact hull, and downward overhang area (>45 deg from vertical)."""
import json, sys, numpy as np, trimesh
from pathlib import Path
from shapely.geometry import MultiPoint, Point
P = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print')
OUT = P / 'release-V1.6-cap-pose'
rep = json.load(open(P / 'release-V1.6/evidence/cap-notch-report-snapshot.json'))
W2P = np.array(rep['worldToPrint']['matrix4x4'])

def load(p):
    m = trimesh.load(p, force='mesh', process=False)
    v, inv = np.unique(m.vertices, axis=0, return_inverse=True)
    return trimesh.Trimesh(v, inv[m.faces], process=False)

src = load(P / 'stl/head_cap.stl')
assert src.is_watertight

def metrics(T, name):
    m = src.copy(); m.apply_transform(T); m.apply_translation([0, 0, -m.bounds[0, 2]])
    tri = m.triangles
    near = (np.max(tri[:, :, 2], axis=1) <= 0.02) & (m.face_normals[:, 2] < -0.99)
    area = float(m.area_faces[near].sum())
    pts = tri[near].reshape(-1, 3)[:, :2]
    # hull over every vertex within 0.02 mm (also edge contacts)
    vz = m.vertices[m.vertices[:, 2] <= 0.02][:, :2]
    hull = MultiPoint([tuple(p) for p in vz]).convex_hull if len(vz) >= 3 else None
    com = m.center_mass
    margin = float(hull.exterior.distance(Point(com[:2]))) * (1 if hull.contains(Point(com[:2])) else -1) if hull is not None and hull.area > 0 else None
    # overhang: downward-facing faces steeper than 45 deg from vertical, not on the bed
    nz = m.face_normals[:, 2]; fz = tri[:, :, 2].mean(1)
    over = (nz < -np.cos(np.radians(45))) & (fz > 0.3)
    ext = m.extents
    return dict(name=name, flatContactMm2=round(area, 1), hullMm2=round(float(hull.area) if hull else 0.0, 1),
                heightMm=round(float(ext[2]), 1), footprintXY=[round(float(ext[0]), 1), round(float(ext[1]), 1)],
                comHeightMm=round(float(com[2]), 1), comHullMarginMm=None if margin is None else round(margin, 1),
                comHeightOverHullSqrt=round(float(com[2]) / max(np.sqrt(hull.area) if hull else 1e-9, 1e-9), 2),
                overhangOver45Mm2=round(float(m.area_faces[over].sum()), 0), sourceToPrint=T.tolist())

rows = [metrics(np.eye(4), 'current-side-down (identity)')]
# rim-down: world frame with open side (world -z) on the bed -> print = world pose expressed from the print source
P2W = np.linalg.inv(W2P)
rows.append(metrics(P2W, 'rim-down (robot frame upright, open side on bed)'))
# dome-down for completeness: world flipped about x
F = np.diag([1, -1, -1, 1.0])
rows.append(metrics(F @ P2W, 'dome-down (robot frame upside down)'))
# Stable poses: convex-hull facets whose polygon contains the CoM projection (same criterion as trimesh stable poses,
# computed directly on hull facets because compute_stable_poses sampling was too slow on this mesh).
hull = src.convex_hull; com = src.center_mass; cand = []
groups = list(hull.facets) + [[i] for i in range(len(hull.faces)) if not any(i in f for f in hull.facets)]
for g in groups:
    n = hull.face_normals[g[0]]; a = float(hull.area_faces[g].sum())
    if a < 50: continue
    z = -n; x = np.cross(z, [1, 0, 0] if abs(z[0]) < .9 else [0, 1, 0]); x /= np.linalg.norm(x); y = np.cross(z, x)
    R = np.eye(4); R[:3, :3] = np.vstack([x, y, z])
    vs = (R[:3, :3] @ hull.vertices[np.unique(hull.faces[g])].T).T; c = R[:3, :3] @ com
    poly = MultiPoint([tuple(p[:2]) for p in vs]).convex_hull
    if poly.area > 0 and poly.contains(Point(c[:2])):
        cand.append((poly.exterior.distance(Point(c[:2])) / max(c[2] - vs[:, 2].min(), 1e-6), a, R))
cand.sort(key=lambda t: -t[0])
for i, (q, a, T) in enumerate(cand[:12]):
    rows.append(metrics(T, f'stable-{i} hullFacet={a:.0f}mm2 tipRatio={q:.2f}'))
# express each pose's bed normal in the robot frame (which world direction points down)
for r in rows:
    T = np.array(r['sourceToPrint']); R = T[:3, :3] @ W2P[:3, :3]  # world->print rotation
    down_world = R.T @ np.array([0, 0, -1.0]); r['bedFacingWorldDir'] = np.round(down_world, 3).tolist()
json.dump(rows, open(OUT / 'pose-candidates.json', 'w'), indent=1)
for r in rows:
    print(r['name'][:46].ljust(46), 'flat', r['flatContactMm2'], 'hull', r['hullMm2'], 'H', r['heightMm'], 'CoMz', r['comHeightOverHullSqrt'] and r['comHeightMm'],
          'margin', r['comHullMarginMm'], 'over45', r['overhangOver45Mm2'], 'down(world)', r['bedFacingWorldDir'], 'xy', r['footprintXY'])
