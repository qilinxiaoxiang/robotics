"""Ray cast the hidden cap screw (M2 x 10, +x on y 11.367, z -16.667) on the regenerated layout-F meshes
(layout-F/rear_frame-world.stl, rear_lid-world.stl, pd5991_F-world.stl): solid intervals along the axis and on a
1.0 mm ring, and whether the head envelope (dia 4.0 x 1.5 from the seat x -56.1 backward) and the driver lane (dia 4.0
from the head to the cap back) are clear. Writes raycast_cap_screw.json.

    /tmp/microduck-cad-venv/bin/python raycast_cap_screw.py"""
import json
from pathlib import Path
import numpy as np, trimesh
LF = Path(__file__).resolve().parent.parent / 'layout-F'
Y, Z, SEAT, L = 11.367, -16.667, -56.1, 10.0
def load(n):
    t = trimesh.load(str(LF / n), force='mesh'); t.merge_vertices(); return t
parts = {k: load(n) for k, n in (('rear_lid', 'rear_lid-world.stl'), ('rear_frame', 'rear_frame-world.stl'), ('pd5991', 'pd5991_F-world.stl'))}
def intervals(m, y, z, x0=-70.0, x1=-40.0):
    loc, _, _ = m.ray.intersects_location([[x0, y, z]], [[1.0, 0, 0]], multiple_hits=True)
    if len(loc) == 0: return []
    xs = sorted(set(np.round(np.asarray(loc).reshape(-1, 3)[:, 0], 3).tolist()))
    return [xs[i:i + 2] for i in range(0, len(xs) - 1, 2)]
res = dict(axis=dict(y=Y, z=Z, seatX=SEAT, tipX=SEAT + L), centre={k: intervals(m, Y, Z) for k, m in parts.items()})
ring = {}
for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
    y, z = Y + np.cos(a), Z + np.sin(a)
    ring[f'{np.degrees(a):.0f}'] = {k: intervals(m, y, z) for k, m in parts.items()}
res['ring1mm'] = ring
pts = []
for x in np.linspace(SEAT - 1.5, SEAT - 0.05, 6):
    for r in (0.5, 1.0, 1.5, 2.0):
        for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
            pts.append([x, Y + r * np.cos(a), Z + r * np.sin(a)])
pts = np.array(pts)
res['headEnvelopeSamplesInside'] = {k: int(m.contains(pts).sum()) for k, m in parts.items()} | {'samples': len(pts)}
lane = np.array([[x, Y + r * np.cos(a), Z + r * np.sin(a)] for x in np.linspace(-67.2, SEAT - 1.6, 20) for r in (0.0, 1.0, 2.0) for a in np.linspace(0, 2 * np.pi, 12, endpoint=False)])
res['driverLaneDia4SamplesInside'] = {k: int(m.contains(lane).sum()) for k, m in parts.items()} | {'samples': len(lane)}
print(json.dumps({k: v for k, v in res.items() if k != 'ring1mm'}, indent=1))
print('ring 1 mm, rear_lid hits inside x -56.1..-55.1 floor:', {a: v['rear_lid'] for a, v in list(ring.items())[:3]})
print('ring 1 mm frame:', {a: v['rear_frame'] for a, v in list(ring.items())[:3]})
(Path(__file__).resolve().parent / 'raycast_cap_screw.json').write_text(json.dumps(res, indent=1) + '\n')
