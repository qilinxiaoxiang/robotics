"""Free space in the rear pack's empty channel behind the OpenRB (x -45..-36.7, |y| <= 13.6) at HOME. Solids: guide
solids (rear box parts excluded) intersected with the channel box by manifold3d and sliced every 1 mm in z; a (y, z)
column is free when the line x -45..-36.7 misses every slice polygon and every guide cable tube (+0.5 mm). The bench
box wires are excluded (the battery backpack replaces them). Prints a y-z map: '.' free through the whole depth."""
import sys, json, numpy as np
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit'); import ia_lib
from cables import spline_samples
from scipy.spatial import cKDTree
import manifold3d as m3
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
X0, X1, YH, Z0, Z1 = -45.0, -36.7, 13.6, -42.8, 32.0
BOX = m3.Manifold.cube([X1 - X0, 2 * YH, Z1 - Z0]).translate([X0, -YH, Z0])
man = ia_lib.manifest(); SKIP = {'rear_frame', 'rear_lid', 'xl4015_top', 'xl4015_mid', 'pd5991'}; parts = []; who = []
for k, rec in man.items():
    if k in SKIP: continue
    lo, hi = np.array(rec['bounds'])
    if np.any(hi < [X0, -YH, Z0]) or np.any(lo > [X1, YH, Z1]): continue
    s = ia_lib.to_manifold(*ia_lib.load_solid(k)) ^ BOX
    if not s.is_empty() and s.volume() > 1e-3: parts.append(s); who.append((k, round(s.volume(), 1)))
occ = m3.Manifold.batch_boolean(parts, m3.OpType.Add) if parts else m3.Manifold()
print('solids in the channel:', who)
ys = np.arange(-13.0, 13.01, 1.0); zs = np.arange(-42.0, 31.6, 1.0)
gd = ia_lib.load_guide(); cab = []
for c in gd['cables']:
    if c['id'] in ('pw-15v', 'pw-15v-link', 'pw-7v', 'pi-lead'): continue
    x, _ = spline_samples(c['path']); x = np.asarray(x); r = float(c.get('radius') or 0.9)
    sel = x[(x[:, 0] > X0 - 3) & (x[:, 0] < X1 + 3) & (np.abs(x[:, 1]) < YH + 3) & (x[:, 2] > Z0 - 3) & (x[:, 2] < Z1 + 3)]
    if len(sel): cab.append((c['id'], cKDTree(sel), r))
rows = {}; free = np.zeros((len(ys), len(zs)), bool)
for j, z in enumerate(zs):
    cs = occ.slice(z) if parts else None
    polys = [Polygon(p) for p in cs.to_polygons()] if cs is not None else []
    geo = unary_union([p.buffer(0) for p in polys if len(p.exterior.coords) > 3]) if polys else None
    for i, y in enumerate(ys):
        ok = geo is None or geo.is_empty or not geo.intersects(LineString([(X0, y), (X1, y)]))
        if ok:
            P = np.c_[np.linspace(X0, X1, 9), np.full(9, y), np.full(9, z)]
            for cid, tr, r in cab:
                if tr.query(P)[0].min() < r + 0.5: ok = False; break
        free[i, j] = ok
for j in range(len(zs) - 1, -1, -1):
    print(f'z {zs[j]:6.1f} ' + ''.join('.' if free[i, j] else '#' for i in range(len(ys))))
json.dump(dict(y=ys.tolist(), z=zs.tolist(), free=free.astype(int).tolist(), solids=who), open('probe_channel.json', 'w'))
