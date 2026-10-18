"""Ray cast the four hidden M2 x 10 cap screws on the layout-F world meshes (rear_lid, rear_frame, pd5991_F,
xl4015_top_7V, xl4015_mid_5V): solid intervals along each axis and on a 1.0 mm ring (the M2 minor radius),
and whether the head envelope (dia 4.0 x 1.5 behind the seat) and the dia 4.0 driver lane from the cap back are clear.
Axes, seats and tips come from layout_f.json (capScrew, capScrew2, capTopScrews). Writes raycast_cap_screws.json.

    /tmp/microduck-cad-venv/bin/python raycast_cap_screws.py"""
import json
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent
L = json.loads((HERE / 'layout_f.json').read_text())
def load(n):
    t = trimesh.load(str(HERE / n), force='mesh'); t.merge_vertices(); return t
parts = {k: load(n) for k, n in (('rear_lid', 'rear_lid-world.stl'), ('rear_frame', 'rear_frame-world.stl'), ('pd5991', 'pd5991_F-world.stl'),
                                 ('xl4015_top', 'xl4015_top_7V-world.stl'), ('xl4015_mid', 'xl4015_mid_5V-world.stl'))}
screws = [('pd5991_plus_y', L['capScrew']['axisYZ'], L['capScrew']['seatX'], L['capScrew']['tipX']),
          ('pd5991_minus_y', L['capScrew2']['axisYZ'], L['capScrew2']['seatX'], L['capScrew2']['tipX'])]
screws += [('top_%s_y' % ('plus' if a[0] > 0 else 'minus'), a, L['capTopScrews']['seatX'], L['capTopScrews']['tipX']) for a in L['capTopScrews']['axesYZ']]
def intervals(m, y, z, x0=-70.0, x1=-40.0):
    loc, _, _ = m.ray.intersects_location([[x0, y, z]], [[1.0, 0, 0]], multiple_hits=True)
    if len(loc) == 0: return []
    xs = sorted(set(np.round(np.asarray(loc).reshape(-1, 3)[:, 0], 3).tolist()))
    return [xs[i:i + 2] for i in range(0, len(xs) - 1, 2)]
def ring_pts(x0, x1, nx, Y, Z, radii):
    return np.array([[x, Y + r * np.cos(a), Z + r * np.sin(a)] for x in np.linspace(x0, x1, nx) for r in radii for a in np.linspace(0, 2 * np.pi, 12, endpoint=False)])
out = {}
for name, (Y, Z), seat, tip in screws:
    r = dict(axisYZ=[Y, Z], seatX=seat, tipX=tip, centre={k: intervals(m, Y, Z) for k, m in parts.items()})
    # material the 1.0 mm thread ring passes through between the seat and the tip, per part (mm along x)
    eng = {}
    for k, m in parts.items():
        lens = []
        for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
            iv = intervals(m, Y + np.cos(a), Z + np.sin(a))
            lens.append(sum(max(0.0, min(b, tip) - max(a_, seat)) for a_, b in iv))
        eng[k] = round(float(np.min(lens)), 2)
    r['ringMaterialSeatToTipMm'] = eng
    head = ring_pts(seat - 1.5, seat - 0.05, 6, Y, Z, (0.5, 1.0, 1.5, 2.0))
    r['headEnvelopeSamplesInside'] = {k: int(m.contains(head).sum()) for k, m in parts.items()} | {'samples': len(head)}
    lane = ring_pts(-67.2, seat - 1.6, 20, Y, Z, (0.0, 1.0, 2.0))
    r['driverLaneDia4SamplesInside'] = {k: int(m.contains(lane).sum()) for k, m in parts.items()} | {'samples': len(lane)}
    out[name] = r
(HERE / 'raycast_cap_screws.json').write_text(json.dumps(out, indent=1) + '\n')
for n, r in out.items():
    print(n, r['axisYZ'], 'ring material', r['ringMaterialSeatToTipMm'], 'head', {k: v for k, v in r['headEnvelopeSamplesInside'].items() if v and k != 'samples'}, 'lane', {k: v for k, v in r['driverLaneDia4SamplesInside'].items() if v and k != 'samples'})
