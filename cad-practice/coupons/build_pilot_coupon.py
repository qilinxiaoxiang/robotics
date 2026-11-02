"""Pilot coupon: one plate that measures a printer's pilot shrink against print_fit.PILOT.

Row A: vertical blind pilots 1.5 to 2.2 mm (0.1 steps), mouths on the top face (away from the bed), 8 mm deep.
Row B: the same diameters as vertical through holes, so their bed mouths show the first-layer flare.
Row C: horizontal teardrop pilots 1.7 to 2.4 mm (0.1 steps), 11 mm deep from the front face, tip to +Z.
Print it on each printer with the same .3mf, drive one M2 x 8 (machine and thread-forming) into each, and write the
smallest diameter that takes each screw by hand driver into PRINT-FIT.md and print_fit.PRINTER_OFFSET.
Run: uv run -q --python 3.12 --with trimesh --with manifold3d python build_pilot_coupon.py
"""
import math
from pathlib import Path
import trimesh

DIAS = [1.5 + 0.1 * i for i in range(8)]
HDIAS = [1.7 + 0.1 * i for i in range(8)]
PITCH, W, H = 6.0, 6.0 * 8 + 4, 10.0


def cyl(d, h, x, y, z0):
    c = trimesh.creation.cylinder(radius=d / 2, height=h, sections=96)
    c.apply_translation((x, y, z0 + h / 2))
    return c


def teardrop(d, x, z, length):
    r = d / 2
    pts = [(r * math.cos(a), r * math.sin(a)) for a in [math.radians(t) for t in range(-225, 46, 5)]]
    pts.append((0.0, r * math.sqrt(2)))                                     # 45 deg tip to +Z
    from shapely.geometry import Polygon
    prism = trimesh.creation.extrude_polygon(Polygon(pts), length)         # profile in XY, extruded along Z
    prism.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (1, 0, 0)))   # profile Y -> +Z, extrusion -> -Y
    prism.apply_translation((x, length - 1.0, z))
    return prism


body = trimesh.creation.box((W, 30.0, H))
body.apply_translation((W / 2, 15.0, H / 2))
cuts = []
for i, d in enumerate(DIAS):
    x = 4 + PITCH * i
    cuts.append(cyl(d, 8.0 + 0.01, x, 24.0, H - 8.0))          # row A blind from top
    cuts.append(cyl(d, H + 2, x, 16.0, -1))                    # row B through
for i, d in enumerate(HDIAS):
    cuts.append(teardrop(d, 4 + PITCH * i, 5.0, 12.0))         # row C, blind from the y = 0 face
out = body.difference(trimesh.util.concatenate(cuts))
# engraved-free labels: one notch per 0.1 step is not printed; row order is the label (left = smallest)
p = Path(__file__).with_name("pilot-coupon.stl")
out.export(p)
print(p, out.is_watertight, out.bounds.tolist())
