"""Layout D renders on the as-built model at HOME (feet flat). One scene per process (memory):
  python render_layout_d.py frame | frame-solid | integrated | integrated-solid | c2 | b2 | compose
Printed parts orange; XL4015 blue (ROBOTIS mesh, decimated); 5991 black; USB-C plug grey (13 x 7.5 overmold) and cable.
Writes renders/D-<scene>-<view>.png, renders/layout-D-*.png and renders/compare-rear34.png."""
import sys, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = Path(__file__).resolve().parent; BP = HERE.parent; OUT = HERE / 'renders'; OUT.mkdir(exist_ok=True)
SCENE = sys.argv[1]
try:
    FONT = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 20)
except Exception:
    FONT = ImageFont.load_default()
ORANGE = (.93, .5, .1, 1); ORANGE_LID = (.98, .62, .2, 1); BLUE = (.12, .3, .9, 1); BLACK = (.03, .03, .03, 1); GREY = (.7, .7, .72, 1)
VIEWS = {'rear34': ('rear 3/4', -50, -8, 0.32, (-50, 0, 0)), 'side-minus-y': ('-y side: OUT windows, USB-C down', 90, 0, 0.36, (-45, -10, -10)),
         'iso': ('rear-top isometric', 30, -30, 0.32, (-55, 0, 0))}
TITLES = {'frame': 'D frame on V1.8 pack, skeletal lid', 'frame-solid': 'D frame on V1.8 pack, solid lid', 'integrated': 'D integrated pack (V1.9 + bay), skeletal lid',
          'integrated-solid': 'D integrated pack, solid lid', 'c2': 'C2 as built (orange)', 'b2': 'B2 sketch (candidates/back-box-20261014)'}


def label(img, text):
    dr = ImageDraw.Draw(img); dr.rectangle((0, 0, img.size[0], 30), fill=(0, 0, 0)); dr.text((8, 5), text, fill=(255, 255, 255), font=FONT); return img


if SCENE == 'compose':
    keys = ['b2', 'c2', 'frame', 'integrated']
    tiles = [label(Image.open(OUT / f'D-{k}-rear34.png').convert('RGB'), TITLES[k]) for k in keys]
    W, H = tiles[0].size; c = Image.new('RGB', (W * 4, H + 40), (0, 0, 0))
    for i, t in enumerate(tiles):
        c.paste(t, (i * W, 0))
    ImageDraw.Draw(c).text((8, H + 10), 'rear 3/4 view at HOME; same camera for all four; renders only (no wire routing)', fill=(230, 230, 230), font=FONT)
    c.save(OUT / 'compare-rear34.png')
    for k, views in (('frame', ['rear34', 'side-minus-y', 'iso']), ('integrated', ['rear34', 'side-minus-y', 'iso'])):
        ims = [label(Image.open(OUT / f'D-{k}-{v}.png').convert('RGB'), VIEWS[v][0]) for v in views]
        row = Image.fromarray(np.hstack([np.array(i) for i in ims])); W2, H2 = row.size
        cc = Image.new('RGB', (W2, H2 + 36), (0, 0, 0)); cc.paste(row, (0, 0)); ImageDraw.Draw(cc).text((8, H2 + 8), TITLES[k] + '; iso view with the lid removed', fill=(230, 230, 230), font=FONT)
        cc.save(OUT / f'layout-D-{k}.png')
    for k in ('frame-solid', 'integrated-solid'):
        label(Image.open(OUT / f'D-{k}-rear34.png').convert('RGB'), TITLES[k]).save(OUT / f'layout-D-{k}.png')
    print('composed'); sys.exit(0)

import mujoco
REAL = Path('/Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014')
sys.path.insert(0, str(REAL))
from static_gap import NAMES, HOME, feet_flat_rot, setup, sole_points
import evaluate_delay as ev
mm = 0.001
WORLD = BP.parent / 'world'
spec = mujoco.MjSpec.from_file(str(ev.MODEL_DIR / 'scene.xml'))
trunk = spec.body('trunk_base')
for g in list(spec.geoms):
    if g.name in ('power_support', 'np_f970'):
        spec.delete(g)
def add(f, rgba, tag):
    a = spec.add_mesh(name=f'm_{tag}', file=str(f), scale=[mm] * 3)
    trunk.add_geom(name=tag, type=mujoco.mjtGeom.mjGEOM_MESH, meshname=a.name, contype=0, conaffinity=0, mass=0, rgba=rgba, group=2)
def box(name, lo, hi, rgba):
    lo, hi = np.array(lo, float), np.array(hi, float)
    trunk.add_geom(name=name, type=mujoco.mjtGeom.mjGEOM_BOX, pos=(lo + hi) / 2 * mm, size=(hi - lo) / 2 * mm, rgba=rgba, contype=0, conaffinity=0, mass=0, group=2)
def wire(name, pts, rgba, r):
    for k in range(len(pts) - 1):
        trunk.add_geom(name=f'{name}{k}', type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=np.r_[np.array(pts[k]) * mm, np.array(pts[k + 1]) * mm],
                       size=[r * mm, 0, 0], rgba=rgba, contype=0, conaffinity=0, mass=0, group=2)
add(WORLD / 'openrb-board-upright.stl', (.15, .35, .2, 1), 'orb')
lid_tag = None
if SCENE in ('frame', 'frame-solid', 'integrated', 'integrated-solid'):
    if SCENE.startswith('frame'):
        add(WORLD / 'rear_pack-v18.stl', ORANGE, 'pack'); add(HERE / 'frame_D-world.stl', ORANGE, 'frame')
    else:
        add(HERE / 'pack_integrated_D-world.stl', ORANGE, 'pack')
    add(HERE / ('lid_solid-world.stl' if SCENE.endswith('solid') else 'lid_skeletal-world.stl'), ORANGE_LID, 'lid'); lid_tag = 'lid'
    for nm in ('upper', 'lower'):
        add(HERE / 'render' / f'xl4015_{nm}.stl', BLUE, f'xl_{nm}')
    add(HERE / 'pd5991_standing-world.stl', BLACK, 'pd')
    box('usb_plug', (-57.0, -6.5, -59.0), (-49.5, 6.5, -42.8), GREY)
    wire('usb_cable', [(-53.25, 0, -59.0), (-53.25, 0, -66.0), (-75.0, 0, -80.0)], GREY, 2.0)
elif SCENE == 'c2':
    add(WORLD / 'rear_pack-v18.stl', ORANGE, 'pack'); add(BP / 'rear_frame-world.stl', ORANGE, 'frame'); add(BP / 'rear_lid-world.stl', ORANGE_LID, 'lid'); lid_tag = 'lid'
    for nm in ('left', 'right'):
        add(BP / 'render' / f'xl4015_{nm}.stl', BLUE, f'xl_{nm}')
    add(BP / 'pd5991-world.stl', BLACK, 'pd')
    box('usb_plug', (-57.0, -52.05, -38.64), (-49.5, -15.05, -25.64), GREY)
elif SCENE == 'b2':
    add(WORLD / 'rear_pack-v18.stl', ORANGE, 'pack')
    box('b2_box', (-69, -28, -32), (-47, 28, 41), (1, 1, 1, 0.35))
    box('b2_xl1', (-65, -27, -6), (-49, 27, 17), BLUE); box('b2_xl2', (-65, -27, 18), (-49, 27, 41), BLUE); box('b2_pd', (-57, -16.5, -31), (-49, 16.5, -8), BLACK)
m = spec.compile(); m.vis.global_.offwidth = 800; m.vis.global_.offheight = 800
d = mujoco.MjData(m)
Rt = feet_flat_rot(m, d, NAMES, HOME); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel())
setup(m, d, NAMES, HOME, q); z = np.vstack(sole_points(m, d))[:, 2].min(); d.qpos[2] -= z; mujoco.mj_forward(m, d)
tb = m.body('trunk_base').id
world = lambda p: d.xpos[tb] + d.xmat[tb].reshape(3, 3) @ (np.array(p, float) * mm)
r = mujoco.Renderer(m, height=600, width=600)
def shot(az, el, dist, look, hide=()):
    cam = mujoco.MjvCamera(); cam.lookat = world(look); cam.distance = dist; cam.azimuth = az; cam.elevation = el
    r.update_scene(d, camera=cam); scn = r.scene
    for i in range(scn.ngeom):
        g = scn.geoms[i]
        if g.objtype == mujoco.mjtObj.mjOBJ_GEOM and m.geom(g.objid).name in hide:
            g.rgba[3] = 0.0
    return r.render()
views = ['rear34'] if SCENE in ('frame-solid', 'integrated-solid', 'c2', 'b2') else list(VIEWS)
for v in views:
    _, az, el, dist, look = VIEWS[v]
    hide = (lid_tag,) if (v == 'iso' and lid_tag) else ()
    Image.fromarray(shot(az, el, dist, look, hide)).save(OUT / f'D-{SCENE}-{v}.png')
print('ok', SCENE, views)
