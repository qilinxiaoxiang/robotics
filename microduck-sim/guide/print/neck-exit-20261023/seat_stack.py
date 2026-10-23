"""Screw stack of the moved jaw-support seat H-jaw_support-01 (M2.6 x 6 TAP, axis -z) on the rebuilt parts, measured the way
fasteners.json records it: along the axis from the head seat, each part's extent and the hole diameter range in it, the thread
engagement in the head floor boss and the solid margin past the tip. Writes seat-stack.json.
    /tmp/microduck-cad-venv/bin/python seat_stack.py"""
import json
from pathlib import Path
import numpy as np, trimesh
from shapely.geometry import Point, Polygon
HERE = Path(__file__).resolve().parent
P = json.loads((HERE / 'checks.json').read_text())['params']
X, Y = P['NEW_SEAT']; L = 6.0
M = {'jaw_support': trimesh.load(HERE / 'jaw_support_exit.stl'), 'head_bottom': trimesh.load(HERE / 'head_bottom_exit.stl')}
seat = M['jaw_support'].ray.intersects_location([[X + 2.0, Y, 140.0]], [[0, 0, -1.0]])[0][:, 2].max()   # top face of the pad beside the hole
def hole_r(m, z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None: return None
    g = Polygon()
    for e in s.discrete:
        if len(e) >= 4:
            p = Polygon(e[:, :2]).buffer(0)
            if not p.is_empty: g = g.symmetric_difference(p)
    pt = Point(X, Y)   # the smallest hole ring round the axis (a hole can sit inside a larger opening of the same section)
    rings = [Polygon(ring) for poly in getattr(g, 'geoms', [g]) for ring in poly.interiors if Polygon(ring).contains(pt)]
    if rings: return float(min(rings, key=lambda q: q.area).exterior.distance(pt))
    return None if not g.contains(pt) else 0.0
stack, zs = [], np.arange(seat - 0.02, seat - L - 6.0, -0.05)
for z in zs:
    for k, m in M.items():
        if m.bounds[0, 2] <= z <= m.bounds[1, 2]:
            r = hole_r(m, z)
            if r is not None: stack.append((round(seat - z, 2), k, r)); break
    else:
        stack.append((round(seat - z, 2), None, None))
runs = []
for d, k, r in stack:
    if runs and runs[-1]['part'] == k and (r == 0.0) == runs[-1]['solid'] and (r is None or abs((r or 0) - (runs[-1]['r'][-1] or 0)) < 0.12):
        runs[-1]['toMm'] = d; runs[-1]['r'].append(r)
    else:
        runs.append(dict(part=k, solid=(r == 0.0), fromMm=d, toMm=d, r=[r]))
out = dict(seatZ=round(float(seat), 3), center=[X, Y, round(float(seat), 3)], screwLengthMm=L, runs=[])
for u in runs:
    rr = [r for r in u['r'] if r]
    out['runs'].append(dict(part=u['part'], solid=u['solid'], fromMm=u['fromMm'], toMm=u['toMm'],
                            holeDiameterRangeMm=[round(2 * min(rr), 2), round(2 * max(rr), 2)] if rr and not u['solid'] else None))
hb = [u for u in out['runs'] if u['part'] == 'head_bottom' and not u['solid'] and u['holeDiameterRangeMm'] and u['holeDiameterRangeMm'][1] <= 2.4]   # pilot (M2.6 tap range 2.0..2.4)
pilot_from = min(u['fromMm'] for u in hb); pilot_to = max(u['toMm'] for u in hb)
out['engagementMm'] = round(min(L, pilot_to) - pilot_from, 2)
out['tipMarginMm'] = round(pilot_to - L, 2)   # pilot depth left past the tip before the boss floor
print(json.dumps(out, indent=1)); (HERE / 'seat-stack.json').write_text(json.dumps(out, indent=1) + '\n')
