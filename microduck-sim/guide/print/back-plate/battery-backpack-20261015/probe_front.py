"""Robot rear surface just in front of the backpack (2026-10-15): for every (y, z) on a 1 mm grid over the box outline, the
most rearward x of any guide solid (rear box parts excluded) between x -52 and -40 at HOME, from manifold slices every 1 mm
in z. Writes probe_front.json (rows of x per z) and prints a coarse map: '.' nothing before x -44, digits = how far the
robot reaches behind x -44 (1 = to -45, 2 = to -46, ...), '#' = reaches behind -50."""
import sys, json, numpy as np
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit'); import ia_lib
import manifold3d as m3
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
X0, X1, YH, Z0, Z1 = -52.0, -40.0, 33.0, -45.0, 44.0
BOX = m3.Manifold.cube([X1 - X0, 2 * YH, Z1 - Z0]).translate([X0, -YH, Z0])
man = ia_lib.manifest(); SKIP = {'rear_frame', 'rear_lid', 'xl4015_top', 'xl4015_mid', 'pd5991'}; parts = []; who = []
for k, rec in man.items():
    if k in SKIP: continue
    lo, hi = np.array(rec['bounds'])
    if np.any(hi < [X0, -YH, Z0]) or np.any(lo > [X1, YH, Z1]): continue
    s = ia_lib.to_manifold(*ia_lib.load_solid(k)) ^ BOX
    if not s.is_empty() and s.volume() > 1e-3: parts.append((k, s))
ys = np.arange(-32.0, 32.01, 1.0); zs = np.arange(-44.5, 43.6, 1.0); rows = {}
for z in zs:
    row = []
    geos = []
    for k, s in parts:
        cs = s.slice(z); ps = [Polygon(p).buffer(0) for p in cs.to_polygons() if len(p) > 2]
        if ps: geos.append((k, unary_union(ps)))
    for y in ys:
        L = LineString([(X0, y), (X1, y)]); best = (None, None)
        for k, g in geos:
            q = g.intersection(L)
            if not q.is_empty:
                xm = q.bounds[0]
                if best[0] is None or xm < best[0]: best = (round(xm, 2), k)
        row.append(best)
    rows[f'{z:.1f}'] = row
json.dump(dict(ys=ys.tolist(), rows=rows), open('probe_front.json', 'w'))
print('y: ' + ''.join('|' if abs(y) % 8 == 0 else ' ' for y in ys))
for z in zs[::-2]:
    s = ''
    for xm, k in rows[f'{z:.1f}']:
        s += '.' if xm is None or xm > -44 else ('#' if xm < -50 else str(int(min(9, -44 - xm + 1))))
    print(f'{z:6.1f} {s}')
