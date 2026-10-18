"""Establish the amplifier's board-local frame in the guide world from its mesh features (holes, terminal, SMD parts)
against the EAGLE board (adafruit-3006.brd)."""
import numpy as np, trimesh
from scene import load
M, src, nb = load()
m = M['amplifier']
parts = m.split(only_watertight=False)
for p in sorted(parts, key=lambda q: q.bounds[0][2]):
    b = p.bounds
    if p.area < 400:
        print('comp area %.1f  x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f  centre %s' % (p.area, b[0][0], b[1][0], b[0][1], b[1][1], b[0][2], b[1][2], np.round(b.mean(0), 2)))
    else:
        print('BIG area %.1f bounds %s' % (p.area, np.round(b, 2).tolist()))
# holes: board section at mid-thickness
s = m.section(plane_origin=[0, 0, 133.3], plane_normal=[0, 0, 1])
for e in s.entities:
    pts = s.vertices[e.points]; lo, hi = pts.min(0), pts.max(0)
    if (hi - lo).max() < 4: print('hole/cut centre', np.round((lo + hi) / 2, 2), 'size', np.round(hi - lo, 2))
