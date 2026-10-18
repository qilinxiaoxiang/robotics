"""Candidate trim of the integrated power support (robot frame and printed frame). Candidate only: not released.

Usage: build_candidate.py <name> <edge_chamfer_mm> <bottom_chamfer_mm> [z_top] [deck_chamfer_mm]
  edge_chamfer_mm: 45 deg chamfer of the front-outer vertical edge of each deck hanger post (x -33.5, |y| 20.4),
                   from the deck bottom (z -57.5) up to z_top (default -37.5, the underside of the cross bar).
  bottom_chamfer_mm: 45 deg chamfer of the bottom-outer edge of each post foot (|y| 20.4, z -57.5), x -37.5..-33.5.
  deck_chamfer_mm: 45 deg chamfer of the bottom-outer edge of the deck (|y| 17.9, z -57.5) over x -31..-22, where the
                   shin passes the deck edge; at most 2 mm so the deck top face (tray seat) keeps its full width.
Writes candidates/<name>-robot-frame.stl, candidates/<name>-print-frame.stl (= robot frame + z 57.5, the frame of the
printed file build-pack-20260913/assembly/print-parts/current/power-support-integrated-print.stl) and
candidates/<name>-build.json (removed volume, mounting-feature checks).
"""
import json
import sys
from pathlib import Path

import manifold3d as m3
import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pso_lib as L

name = sys.argv[1]; c = float(sys.argv[2]); b = float(sys.argv[3]); ztop = float(sys.argv[4]) if len(sys.argv) > 4 else -37.5
dch = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
assert dch <= 2.0
OUT = Path(__file__).with_name('candidates'); OUT.mkdir(exist_ok=True)
body = L.tm_load(L.CB / 'power-support-integrated-body.stl')
B = L.mesh_to_m(body)
X0, Y0, ZB = -33.5, 20.4, -57.5  # front-outer edge of the left post; bottom of the deck
E = 6.0  # outward extension of the cutters (well outside the part)


def hull(pts):
    return m3.Manifold.hull_points(np.asarray(pts, np.float64).tolist())


cut = None
for s in (1.0, -1.0):
    parts = []
    if c > 0:
        prof = [(X0 - c, Y0), (X0, Y0 - c), (X0 + E, Y0 - c), (X0 + E, Y0 + E), (X0 - c, Y0 + E)]
        pts = [(x, s * y, z) for x, y in prof for z in (ZB - 1.0, ztop)]
        keep = L.box_m([-60, 17.95, -60], [0, 40, 0]) if s > 0 else L.box_m([-60, -40, -60], [0, -17.95, 0])
        parts.append(hull(pts) ^ keep)  # never cut the deck (|y| <= 17.9) or anything inboard of the post
    if b > 0:
        prof = [(Y0 - b, ZB - E), (Y0 - b, ZB), (Y0, ZB + b), (Y0 + E, ZB + b), (Y0 + E, ZB - E)]
        pts = [(x, s * y, z) for y, z in prof for x in (-37.5 - 1.0, X0 + 1.0)]
        parts.append(hull(pts))
    if dch > 0:
        Y1 = 17.9
        prof = [(Y1 - dch, ZB - E), (Y1 - dch, ZB), (Y1, ZB + dch), (Y1 + 0.3, ZB + dch), (Y1 + 0.3, ZB - E)]
        pts = [(x, s * y, z) for y, z in prof for x in (-31.0, -22.0)]
        parts.append(hull(pts))
    for p in parts:
        cut = p if cut is None else cut + p
C = B - cut if cut is not None else B
comps = C.decompose()
removed = B - C
v, f = L.ia_lib.from_manifold(C)
mesh = trimesh.Trimesh(v, f, process=True)
mesh.export(OUT / f'{name}-robot-frame.stl')
pm = mesh.copy(); pm.apply_translation([0, 0, 57.5]); pm.export(OUT / f'{name}-print-frame.stl')

# mounting features: bosses, deck tie slots, tray seat, post sections, connectivity
rep = dict(name=name, edgeChamfer=c, bottomChamfer=b, zTop=ztop, deckChamfer=dch, volume_mm3=C.volume(), removed_mm3=removed.volume(),
           removed_g_PLA=removed.volume() * 0.00124, solids=len(comps), watertight=bool(mesh.is_watertight),
           removedBounds=[list(np.round(removed.bounding_box()[:3], 3)), list(np.round(removed.bounding_box()[3:], 3))] if not removed.is_empty() else None)
chk = {}
for (x, y) in [(-54.931, 12.7), (-54.931, -12.7), (-16.069, 12.7), (-16.069, -12.7)]:
    bx = L.box_m([x - 3, y - 3, -55.5], [x + 3, y + 3, -53.5])
    chk[f'boss({x},{y})_mm3'] = [round((B ^ bx).volume(), 4), round((C ^ bx).volume(), 4)]
for y0, y1 in [(-8.5, -2), (2, 8.5)]:
    bx = L.box_m([-50, y0 - 0.5, -58], [-21, y1 + 0.5, -55.5])
    chk[f'deckSlotZone_y{y0}..{y1}_mm3'] = [round((B ^ bx).volume(), 4), round((C ^ bx).volume(), 4)]
seat = L.box_m([-59.2, -17.3, -55.6], [-11.8, 17.3, -55.4])
chk['traySeatBand_mm3'] = [round((B ^ seat).volume(), 4), round((C ^ seat).volume(), 4)]
for side, s in (('left', 1), ('right', -1)):
    for z in (-57.0, -54.0, -50.0, -46.0, -42.0, -38.5):
        bx = L.box_m([-38, min(s * 17.95, s * 21), z - 0.05], [-33, max(s * 17.95, s * 21), z + 0.05])
        chk[f'{side}PostSection_z{z}_mm2'] = [round((B ^ bx).volume() / 0.1, 3), round((C ^ bx).volume() / 0.1, 3)]
tray = L.to_m(*L.solid('openrb_tray'))
chk['trayGap_mm'] = [round(B.min_gap(tray, 5), 4), round(C.min_gap(tray, 5), 4)]
chk['trayContactUnchanged'] = bool(abs((B ^ seat).volume() - (C ^ seat).volume()) < 1e-6)
rep['checks'] = chk
# changes are confined to the cutter regions
rep['removedOnlyInsidePostAndDeckEdgeZones'] = bool((removed - L.box_m([-39, 15.8, -59], [-21.9, 27, ztop + 0.01])
                                                     - L.box_m([-39, -27, -59], [-21.9, -15.8, ztop + 0.01])).volume() < 1e-6)
L.jdump(rep, OUT / f'{name}-build.json')
print(json.dumps(rep, indent=1))
