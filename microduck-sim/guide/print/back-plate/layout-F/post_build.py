"""Layout F outputs after build_f.py (2026-10-14): release-named world and print STLs, print-pose contact, board insertion
and cap fitting path, the box-outline check and the wire-centreline penetration check. Real world, mm.
    python post_build.py   (CAD venv, bounded runner; after build_f.py F; before write_records.py)
Writes rear_frame-world.stl / rear_lid-world.stl (copies of frame_F / lid_F), rear_frame-print.stl / rear_lid-print.stl,
insertion_check.json and post_build.json."""
import sys, json, shutil
from pathlib import Path
import numpy as np, trimesh, manifold3d as m3, time
T0 = time.time(); stage = lambda m: print(f'[{time.time() - T0:6.1f}s] {m}', flush=True)
from shapely import contains_xy
from shapely.geometry import Point
HERE = Path(__file__).resolve().parent
sys.argv = ['build_f.py', 'F']; sys.path.insert(0, str(HERE))
import build_f as B
P = B.P
# print poses: world -> print transforms of the V1.11 rows (release-V1.11/scripts/rows.json sourceToPrint): frame rim (x -59.1)
# on the bed, x' = y, y' = z, z' = x; cap outer rear face (x -67.1) on the bed, same axes.
TO_PRINT = {'rear_frame': [[0, 1, 0, 32.05], [0, 0, 1, 44.0], [1, 0, 0, 59.1], [0, 0, 0, 1]],
            'rear_lid': [[0, 1, 0, 32.05], [0, 0, 1, 36.02], [1, 0, 0, 67.1], [0, 0, 0, 1]]}
def solid_stats(path):
    t = trimesh.load(str(path), force='mesh'); t.merge_vertices()
    return dict(watertight=bool(t.is_watertight), bodies=len(t.split(only_watertight=False)), volumeMm3=round(float(t.volume), 1), eulerNumber=int(t.euler_number))


out = {}
for key, src in (('rear_frame', 'frame_F-world.stl'), ('rear_lid', 'lid_F-world.stl')):
    shutil.copyfile(HERE / src, HERE / f'{key}-world.stl')
    w = trimesh.load(str(HERE / src), force='mesh', process=False); p = w.copy(); p.apply_transform(np.array(TO_PRINT[key], float))
    p.apply_translation([0.0, 0.0, -p.bounds[0][2]]); p.export(HERE / f'{key}-print.stl')
    at = np.max(np.abs(p.triangles[:, :, 2]), axis=1) <= 0.01
    n = p.face_normals; c = p.triangles_center
    over = (n[:, 2] < -np.cos(np.radians(60))) & (c[:, 2] > 0.05)
    out[key] = dict(printBounds=np.round(p.bounds, 2).tolist(), bedContactMm2=round(float(p.area_faces[at].sum()), 1), heightMm=round(float(p.bounds[1][2]), 2),
                    overhangOver60degFromVerticalMm2=round(float(p.area_faces[over].sum()), 1), **solid_stats(HERE / src))

stage('print poses'); fr = P.mesh_to_m(trimesh.load(str(HERE / 'rear_frame-world.stl'), force='mesh'))
cap = P.mesh_to_m(trimesh.load(str(HERE / 'rear_lid-world.stl'), force='mesh'))


def hulls(path):
    m = trimesh.load(str(path), force='mesh'); parts = []
    for q in m.split(only_watertight=False):
        if len(q.vertices) >= 4 and np.ptp(q.vertices, axis=0).min() > 1e-3:
            parts.append(m3.Manifold.hull_points(np.asarray(q.vertices, float)))
    return P.union(parts)


boards = {'xl4015_top_7V': hulls(HERE / 'xl4015_top_7V-world.stl'), 'xl4015_mid_5V': hulls(HERE / 'xl4015_mid_5V-world.stl'), 'pd5991': hulls(HERE / 'pd5991_F-world.stl')}
stage('board hulls'); ins = {}
for k, b in boards.items():                                  # each board along -x 0..25 mm with the cap off
    worst = (0.0, None)
    for d in np.arange(0, 25.01, 0.5):
        v = (fr ^ b.translate([-d, 0, 0])).volume()
        if v > worst[0]:
            worst = (v, float(d))
    ins[k] = dict(maxOverlapMm3=round(worst[0], 3), atOffsetMm=worst[1])
stage('insertion'); allb = P.union(list(boards.values()))
path = [np.array([-15.0, 0, -B.CAP_DROP]), np.array([0, 0, -B.CAP_DROP]), np.array([0, 0, 0.0])]
worst = {'frame': (0.0, None), 'boards': (0.0, None)}; before_final = (0.0, None)
for a, b_ in zip(path[:-1], path[1:]):
    for t in np.linspace(0, 1, 31):
        o = a + t * (b_ - a); c = cap.translate(o.tolist())
        for nm, S in (('frame', fr), ('boards', allb)):
            v = (S ^ c).volume()
            if v > worst[nm][0]:
                worst[nm] = (v, np.round(o, 2).tolist())
            if nm == 'frame' and np.linalg.norm(o) > 1e-9 and v > before_final[0]:
                before_final = (v, np.round(o, 3).tolist())
ins['cap_path'] = {k: dict(maxOverlapMm3=round(v[0], 3), atOffset=v[1]) for k, v in worst.items()}
ins['cap_path']['frame']['maxOverlapBeforeFinalSeatMm3'] = round(before_final[0], 3); ins['cap_path']['frame']['beforeFinalAt'] = before_final[1]
ins['cap_final_gap'] = dict(frame=round(float(fr.min_gap(cap, 2.0)), 3), boards=round(float(allb.min_gap(cap, 2.0)), 3))
(HERE / 'insertion_check.json').write_text(json.dumps(ins, indent=1) + '\n')

stage('cap path'); ol = B.outline(); ol.W.rc_top = 1.8; ol.W.rc_bot = 1.8; ol.N.rc_bot = 2.1; ol.rf = 3.0
POLY = B.outline_poly(ol)


def outside(path, tol=0.2):
    v = trimesh.load(str(path), force='mesh').vertices; v = v[v[:, 0] < B.X_IN - 0.05]
    o = ~contains_xy(POLY.buffer(tol), v[:, 1], v[:, 2])
    if not o.any():
        return dict(maxMm=0.0, count=0)
    d = np.array([POLY.exterior.distance(Point(q[1], q[2])) for q in v[o]]); i = int(np.argmax(d))
    return dict(maxMm=round(float(d[i]), 2), at=np.round(v[o][i], 2).tolist(), count=int(o.sum()))


out['outline'] = dict(rule='every vertex behind the front plate (x < -47.05) lies inside the y-z box outline (+0.2 mm mesh tolerance)',
                      frame=outside(HERE / 'rear_frame-world.stl'), lid=outside(HERE / 'rear_lid-world.stl'))
out['outline']['passed'] = out['outline']['frame']['maxMm'] == 0 and out['outline']['lid']['maxMm'] == 0
stage('outline done'); W = json.loads((HERE / 'wires_F.json').read_text()); pen = {}
for k, v in W.items():                                       # wire centreline inside a printed part = a wire through a wall
    p = np.array(v['points']); q = np.vstack([a + (b - a) * t for a, b in zip(p[:-1], p[1:]) for t in np.linspace(0, 1, 12)])
    row = {}
    for nm, man in (('frame', fr), ('lid', cap)):
        e = 0.02; inside = np.array([(man ^ P.box(tuple(x - e), tuple(x + e))).volume() > 0.5 * (2 * e) ** 3 for x in q])
        row[nm] = dict(centrelinePointsInside=int(inside.sum()), deepestPoint=None)
        if inside.any():
            qi = q[inside]; row[nm]['deepestPoint'] = np.round(qi[len(qi) // 2], 2).tolist()
    pen[k] = row
out['wireCentrelinePenetration'] = dict(rule='no wire centreline point inside the frame or the cap (the gap check uses manifold min_gap, which missed tubes passing right through the plate)',
                                        perWire=pen, passed=all(r['frame']['centrelinePointsInside'] == 0 and r['lid']['centrelinePointsInside'] == 0 for r in pen.values()))
out['insertion'] = ins
(HERE / 'post_build.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps({k: out[k] for k in ('rear_frame', 'rear_lid', 'outline')}, indent=1)); print(json.dumps(ins, indent=1))
print('penetrating wires:', [k for k, r in pen.items() if r['frame']['centrelinePointsInside'] or r['lid']['centrelinePointsInside']])
