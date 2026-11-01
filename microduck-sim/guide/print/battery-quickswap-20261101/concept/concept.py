"""Concept: top-loading battery with a snap hatch on the battery-on-cap backpack (robot frame, mm).
Usage: python concept.py BATTERY_BACKPACK_DIR OUT_DIR"""
import sys, numpy as np, trimesh, manifold3d as mf, pyvista as pv
from pathlib import Path
BP, OUT = Path(sys.argv[1]), Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)

def load(p): m = trimesh.load(p, force='mesh', process=True); m.merge_vertices(); return m
def to_mf(m): return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
def to_tm(M): g = M.to_mesh(); return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), process=True)
def box(lo, hi): lo, hi = np.array(lo, float), np.array(hi, float); return mf.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))
U = lambda ms: mf.Manifold.batch_boolean(list(ms), mf.OpType.Add)

# battery seat from the redesign (build_cap_cradle.py): x -74.05..-62.05, |y| <= 15.5, z -22.51..34.49
BAT_LO, BAT_HI = (-74.05, -15.5, -22.51), (-62.05, 15.5, 34.49)
OPEN = box((-74.35, -16.0, 34.6), (-61.75, 16.0, 44.0))       # roof opening over the battery (also removes the roof tab)

frame = to_tm(to_mf(load(BP / 'stl/battery_backpack_frame-world.stl')) - OPEN)
cap = to_tm(to_mf(load(BP / 'stl/battery_backpack_cap-world.stl')) - OPEN)
bars = load(BP / 'stl/battery_backpack_bar-world.stl')
pack = load(BP / 'mating/rear_pack.stl')
switch = load(BP / 'envelopes/switch_swann-world.stl')
dfr = load(BP / 'envelopes/dfr1202-world.stl')

# hatch: 1.6 mm plate on the roof, front tabs under the frame roof edge, side latch tongue (-y) whose hook catches under
# the cap roof edge at the rear, lead notches open to the rear edge
Z0, T = 43.0, 1.6
plate = box((-75.35, -17.5, Z0), (-60.75, 17.5, Z0 + T))
slot = box((-75.5, -14.3, Z0 - 1), (-61.6, -13.5, Z0 + T + 1))          # frees the tongue (y -15.9..-14.3 side strip)
edge_cut = box((-75.5, -17.6, Z0 - 1), (-61.6, -15.9, Z0 + T + 1))      # tongue runs inboard of the opening edge
notch_main = box((-75.5, -11.0, Z0 - 1), (-66.0, -5.0, Z0 + T + 1))     # main lead (y about -8)
notch_bal = box((-75.5, 9.0, Z0 - 1), (-66.0, 15.0, Z0 + T + 1))        # balance lead (y about 12)
body = plate - slot - edge_cut - notch_main - notch_bal
tabs = U([box((-62.75, y - 3, 40.2), (-61.85, y + 3, Z0)) for y in (-6, 8)] +
         [box((-61.85, y - 3, 40.2), (-59.85, y + 3, 41.6)) for y in (-6, 8)])
tongue = U([box((-75.35, -15.9, Z0), (-61.6, -14.3, Z0 + T)),
            box((-75.0, -15.9, 40.0), (-71.5, -14.3, Z0)),               # hook block, drops into the opening
            box((-75.0, -17.0, 40.0), (-71.5, -15.9, 41.5)),             # lip under the cap roof edge
            box((-75.35, -15.9, Z0 + T), (-72.5, -14.3, Z0 + T + 2.5))]) # push knob
hatch_body = to_tm(body + tabs)
hatch_tongue = to_tm(tongue)

battery = trimesh.creation.box(bounds=[BAT_LO, BAT_HI])
def leads(dz):
    out = []
    for y, r in ((-8.0, 1.6), (12.0, 1.3)):
        c = trimesh.creation.cylinder(radius=r, segments=24, segment=[(-69.0, y, BAT_HI[2] + dz), (-69.0, y, 52 + dz)])
        out.append(c)
    out.append(trimesh.creation.box(bounds=[(-73, -12.5, 52 + dz), (-63, -3.5, 57 + dz)]))   # XT30 (plug 1 battery half)
    out.append(trimesh.creation.box(bounds=[(-72, 9, 52 + dz), (-66, 15, 56 + dz)]))         # balance plug
    return trimesh.util.concatenate(out)
def ribbon(dz):  # pull ribbon: under the battery, up its front face, folded over the top
    return trimesh.util.concatenate([
        trimesh.creation.box(bounds=[(-73.5, -4, BAT_LO[2] - 0.2 + dz), (-62.0, 4, BAT_LO[2] + dz)]),
        trimesh.creation.box(bounds=[(-62.05, -4, BAT_LO[2] + dz), (-61.9, 4, BAT_HI[2] + 4 + dz)])])

def T(m, d=(0, 0, 0), rot=None, about=None):
    m = m.copy()
    if rot is not None:
        m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot[0]), rot[1], about))
    m.apply_translation(d); return m

C = dict(frame='#f0a040', cap='#f6c27a', bars='#d35400', hatch='#2e86de', tongue='#e84393', bat='#27ae60',
         lead='#c0392b', ribbon='#f1c40f', pack='#bdc3c7', switch='#555555', dfr='#7f8c8d')

def scene(state, view, path, zoom=1.0):
    p = pv.Plotter(off_screen=True, window_size=(1100, 1100)); p.set_background('white')
    def add(m, col, op=1.0): p.add_mesh(pv.wrap(m), color=col, opacity=op, smooth_shading=False, specular=0.2)
    add(pack, C['pack'], 0.35); add(frame, C['frame']); add(cap, C['cap']); add(bars, C['bars'])
    add(switch, C['switch']); add(dfr, C['dfr'])
    if state == 'closed':
        add(hatch_body, C['hatch']); add(hatch_tongue, C['tongue'])
        add(battery, C['bat']); add(leads(0), C['lead']); add(ribbon(0), C['ribbon'])
    elif state == 'open':
        piv = (-60.75, 0, 44.6); rot = (25, (0, 1, 0), piv)         # rear lifted about the front tabs, then off
        add(T(hatch_body, (4, 0, 18), rot), C['hatch']); add(T(hatch_tongue, (4, 0, 18), rot), C['tongue'])
        add(battery, C['bat']); add(leads(0), C['lead']); add(ribbon(0), C['ribbon'])
    elif state == 'lift':
        add(T(battery, (0, 0, 62)), C['bat']); add(leads(62), C['lead']); add(ribbon(62), C['ribbon'])
    p.camera_position = view; p.camera.zoom(zoom)
    p.screenshot(str(path)); p.close()

ctr = (-62, 0, 20)
iso = [(-190, -140, 240), (-62, 0, 35), (0, 0, 1)]       # from behind, left, above
for s in ('closed', 'open', 'lift'):
    scene(s, iso, OUT / f'{s}.png', 1.05)
# latch close-up: from behind-left-low through the opening corner
scene('closed', [(-130, -95, 75), (-70, -12, 40), (0, 0, 1)], OUT / 'latch.png', 1.6)
# section through the battery at y = -2 (cap and frame cut to show the empty column above the battery)
print('ok', frame.is_watertight, cap.is_watertight, hatch_body.bounds.round(2).tolist())
