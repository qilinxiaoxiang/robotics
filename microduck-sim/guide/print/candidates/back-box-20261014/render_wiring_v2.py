"""Layout B2 with measured boards: ROBOTIS XL4015 mesh (61.7 x 26.2, 18 mm stack) x2 and Adafruit 5991 (29.1 x 20.3 x 10.1).
Plate: replaces the pack cover; walls 1.2 mm; outer width 64.1 mm (flush with the torso shells); 20 mm behind the old cover face.
Trunk-frame mm. Board-local STL: X = PCB normal to the component face, Y = long axis, Z = short axis, origin at PCB centre.
"""
import sys
from pathlib import Path
import numpy as np, mujoco, imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont
REAL = Path('/Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014')
WORLD = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(REAL))
from static_gap import cfg, NAMES, HOME, feet_flat_rot, setup, sole_points
import evaluate_delay as ev
mm = 0.001

spec = mujoco.MjSpec.from_file(str(ev.MODEL_DIR / 'scene.xml'))
trunk = spec.body('trunk_base')
for g in list(spec.geoms):
    if g.name in ('power_support', 'np_f970'): spec.delete(g)
for i, (f, rgba) in enumerate([(WORLD / 'rear_pack.stl', (.93, .5, .1, 1)), (WORLD / 'openrb-board-upright.stl', (.15, .35, .2, 1))]):
    a = spec.add_mesh(name=f'pk{i}', file=str(f), scale=[mm] * 3)
    trunk.add_geom(name=f'pk{i}', type=mujoco.mjtGeom.mjGEOM_MESH, meshname=a.name, contype=0, conaffinity=0, mass=0, rgba=rgba, group=2)
xl = spec.add_mesh(name='xl4015', file=str(HERE / 'parts/xl4015_board_local_mm.stl'), scale=[mm] * 3)

def box(name, lo, hi, rgba):
    lo, hi = np.array(lo, float), np.array(hi, float)
    trunk.add_geom(name=name, type=mujoco.mjtGeom.mjGEOM_BOX, pos=(lo + hi) / 2 * mm, size=(hi - lo) / 2 * mm, rgba=rgba, contype=0, conaffinity=0, mass=0, group=2)
def wire(name, pts, rgba, r=1.3):
    for k in range(len(pts) - 1):
        a, b = np.array(pts[k], float) * mm, np.array(pts[k + 1], float) * mm
        trunk.add_geom(name=f'{name}{k}', type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=np.r_[a, b], size=[r * mm, 0, 0], rgba=rgba, contype=0, conaffinity=0, mass=0, group=2)

# plate envelope: x -67..-45 (old cover face was -47; plate front lip sits on the pack back wall at -45), y +-32.05, z -36..43
W = 32.05; T = 1.2
PLATE = (1, 1, 1, .3)
box('plate_back', (-67, -W, -36), (-67 + 2, W, 43), PLATE)
box('plate_l', (-67, -W, -36), (-47, -W + T, 43), PLATE); box('plate_r', (-67, W - T, -36), (-47, W, 43), PLATE)
box('plate_top', (-67, -W, 43 - T), (-47, W, 43), PLATE); box('plate_bot', (-67, -W, -36), (-47, W, -36 + T), PLATE)
# XL4015 boards: PCB centre at x = -47 - 4 - 0.75 = -51.75, component face towards -x
XC = -51.75
# board-local X (component normal) must map to trunk -x: rotate 180 deg about z -> quat (0,0,0,1)
for n, zc in (('xl1', 2.0), ('xl2', 29.4)):
    trunk.add_geom(name=n, type=mujoco.mjtGeom.mjGEOM_MESH, meshname='xl4015', pos=[XC * mm, 0, zc * mm], quat=[0, 0, 0, 1],
                   rgba=(.12, .3, .9, 1), contype=0, conaffinity=0, mass=0, group=2)
# 5991: 29.1 x 20.3 x 10.1, USB-C down at the plate bottom
box('pd', (-57.5, -14.55, -34), (-47.4, 14.55, -13.7), (.08, .08, .08, 1)); box('pd_usbc', (-55, -4.5, -36), (-51, 4.5, -32), (.75, .75, .75, 1))
box('pd_term', (-60, -8, -18), (-57.5, 0, -13.7), (.2, .6, .2, 1))
# wires (one line per pair)
wire('w15', [(-58, -4, -16), (-63, -31, -16), (-63, -31, 0), (-60, -28, 0)], (.9, .1, .1, 1))            # 15 V 5991 -> XL1 IN
wire('w15b', [(-63, -31, 0), (-63, -31, 27.4), (-60, -28, 27.4)], (.9, .1, .1, 1))                       # -> XL2 IN
wire('w7', [(-60, 28, 0), (-64, 31, 6), (-62, 14, 6), (-46, 8, 6), (-41, 8, 6), (-41, 6, 26), (-34, -4, 27), (-30, -6, 26)], (1, .55, .05, 1))
wire('w5', [(-60, 28, 27.4), (-64, 31, 33), (-62, 14, 33), (-46, 4, 31), (-41, 2, 31), (-30, 0, 34), (-20, 0, 36), (-12, 0, 44), (-8, 0, 56)], (.95, .85, .1, 1))
wire('usb_pwr', [(-53, 0, -36), (-53, 0, -60), (-60, 0, -95), (-75, 0, -118)], (.6, .6, .6, 1), r=2.0)
wire('usb_orb', [(-27, 0, -43), (-27, 0, -60), (-40, 0, -95), (-60, 0, -118)], (.3, .3, .3, 1), r=2.0)

m = spec.compile(); m.vis.global_.offwidth = 1200; m.vis.global_.offheight = 900
d = mujoco.MjData(m)
Rt = feet_flat_rot(m, d, NAMES, HOME); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel())
setup(m, d, NAMES, HOME, q); z = np.vstack(sole_points(m, d))[:, 2].min(); d.qpos[2] -= z; mujoco.mj_forward(m, d)
tb = m.body('trunk_base').id
def world(p): return d.xpos[tb] + d.xmat[tb].reshape(3, 3) @ (np.array(p, float) * mm)
r = mujoco.Renderer(m, height=600, width=600)
def shot(az, el, dist, look, hide=()):
    cam = mujoco.MjvCamera(); cam.lookat = world(look); cam.distance = dist; cam.azimuth = az; cam.elevation = el
    r.update_scene(d, camera=cam)
    scn = r.scene
    for i in range(scn.ngeom):
        g = scn.geoms[i]
        if g.objtype == mujoco.mjtObj.mjOBJ_GEOM and m.geom(g.objid).name in hide: g.rgba[3] = 0.0
    return r.render()
PL = ('plate_back', 'plate_l', 'plate_r', 'plate_top', 'plate_bot')
views = [('rear 3/4, plate on', 40, -15, 0.32, (-45, 0, 0), ()),
         ('rear, plate off (boards as measured)', 0, 0, 0.28, (-45, 0, 0), PL),
         ('side', 90, 0, 0.32, (-35, 0, 0), ()),
         ('whole, side', 90, 0, 0.55, (0, 0, -10), ())]
try: font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 22)
except Exception: font = ImageFont.load_default()
imgs = []
for label, az, el, dist, look, hide in views:
    img = Image.fromarray(shot(az, el, dist, look, hide)); dr = ImageDraw.Draw(img)
    dr.rectangle((0, 0, 600, 34), fill=(0, 0, 0)); dr.text((8, 6), label, fill=(255, 255, 255), font=font); imgs.append(np.array(img))
img = Image.fromarray(np.vstack([np.hstack(imgs[:2]), np.hstack(imgs[2:])])); dr = ImageDraw.Draw(img)
legend = ['XL4015 x2: ROBOTIS mesh, 61.7 x 26.2 mm, 18 mm stack', 'black: Adafruit 5991, 29.1 x 20.3 x 10.1 mm', 'plate 64.1 wide x 79 tall, 20 mm behind the old cover',
          'red 15 V in | orange 7 V -> J4 | yellow 5 V -> notch -> Pi', 'grey: USB-C power | dark grey: OpenRB USB data']
y0 = 1200 - 24 * len(legend) - 8; dr.rectangle((0, y0 - 6, 600, 1200), fill=(0, 0, 0))
for i, t in enumerate(legend): dr.text((8, y0 + 24 * i), t, fill=(255, 255, 255), font=font)
img.save(HERE / 'back-plate-B2-measured.png'); print('ok')
