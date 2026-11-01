"""Renders of the built quick-swap parts (build/*.stl) for review: closed, rear lifted, battery out, a section at y = 0 and the
hatch print pose. Writes renders/*.png.

    uv run --with trimesh --with pyvista --with manifold3d python render_quickswap.py BATTERY_BACKPACK_DIR
"""
import sys
from pathlib import Path
import numpy as np, trimesh, pyvista as pv

HERE = Path(__file__).resolve().parent; B = HERE / 'build'; OUT = HERE / 'renders'; OUT.mkdir(exist_ok=True)
BP = Path(sys.argv[1])
ld = lambda p: trimesh.load(p, force='mesh')
frame, cap, hatch = (ld(B / f'{n}-world.stl') for n in ('battery_backpack_frame', 'battery_backpack_cap', 'battery_hatch'))
bars = ld(BP / 'stl/battery_backpack_bar-world.stl'); pack = ld(BP / 'mating/rear_pack.stl')
switch = ld(BP / 'envelopes/switch_swann-world.stl'); dfr = ld(BP / 'envelopes/dfr1202-world.stl')
battery = trimesh.creation.box(bounds=[(-74.05, -15.5, -22.51), (-62.05, 15.5, 34.49)])
PIV = np.array([-61.75, 0, 41.8])

def posed(m, deg, back=0.0, up=0.0):
    m = m.copy(); m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(deg), (0, -1, 0), PIV))
    m.apply_translation((-back, 0, up)); return m

def leads(dz):
    out = [trimesh.creation.cylinder(radius=r, segments=20, segment=[(-69.0, y, 34.49 + dz), (-69.0, y, 52 + dz)]) for y, r in ((-8.0, 1.6), (11.5, 1.3))]
    out += [trimesh.creation.box(bounds=[(-73, -12.5, 52 + dz), (-63, -3.5, 57 + dz)]), trimesh.creation.box(bounds=[(-72, 8.5, 52 + dz), (-66, 14.5, 56 + dz)])]
    return trimesh.util.concatenate(out)

C = dict(frame='#f0a040', cap='#f6c27a', hatch='#2e86de', bars='#d35400', bat='#27ae60', lead='#c0392b', pack='#bdc3c7', grey='#555555')

def shot(items, cam, name, zoom=1.0, size=(1100, 1000)):
    p = pv.Plotter(off_screen=True, window_size=size); p.set_background('white')
    for m, col, op in items: p.add_mesh(pv.wrap(m), color=col, opacity=op, specular=0.2)
    p.camera_position = cam; p.camera.zoom(zoom); p.screenshot(str(OUT / name)); p.close()

base = [(pack, C['pack'], 0.3), (frame, C['frame'], 1), (cap, C['cap'], 1), (bars, C['bars'], 1), (switch, C['grey'], 1), (dfr, C['grey'], 1)]
cam = [(-215, -150, 175), (-64, 0, 22), (0, 0, 1)]
shot(base + [(hatch, C['hatch'], 1), (battery, C['bat'], 1), (leads(0), C['lead'], 1)], cam, '1-closed.png', 1.15)
shot(base + [(posed(hatch, 15), C['hatch'], 1), (battery, C['bat'], 1), (leads(0), C['lead'], 1)], cam, '2-rear-lifted.png', 1.15)
off = posed(hatch, 15, back=2.0, up=30.0)
shot(base + [(off, C['hatch'], 0.35), (battery.copy().apply_translation((0, 0, 66)), C['bat'], 1), (leads(66), C['lead'], 1)],
     [(-260, -170, 230), (-64, 0, 45), (0, 0, 1)], '3-battery-out.png', 1.05)
# back view: the flap and its bump slot
shot(base + [(hatch, C['hatch'], 1)], [(-230, -60, 40), (-70, 0, 20), (0, 0, 1)], '4-back.png', 1.4)
# section at y = 0 (seen from -y): cap, frame, hatch, battery cut
def cut(m):
    try: return m.slice_plane((0, 0.01, 0), (0, 1, 0), cap=True)
    except Exception: return m.slice_plane((0, 0.01, 0), (0, 1, 0))
shot([(cut(frame), C['frame'], 1), (cut(cap), C['cap'], 1), (cut(hatch), C['hatch'], 1), (cut(battery), C['bat'], 1), (cut(bars), C['bars'], 1)],
     [(-68, -220, 25), (-68, 0, 25), (0, 0, 1)], '5-section.png', 2.2, (1000, 1200))
# print pose of the hatch
hp = ld(B / 'battery_hatch-print.stl')
bed = trimesh.creation.box(bounds=[(-5, -5, -0.6), (hp.bounds[1, 0] + 5, hp.bounds[1, 1] + 5, 0)])
c = hp.bounds.mean(axis=0)
shot([(bed, '#dddddd', 1), (hp, C['hatch'], 1)], [tuple(c + (-60, -80, 70)), tuple(c), (0, 0, 1)], '6-hatch-print.png', 1.3)
print('ok', sorted(p.name for p in OUT.glob('*.png')))
