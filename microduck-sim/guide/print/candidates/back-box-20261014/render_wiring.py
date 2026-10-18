"""Layout B2 with wiring: three converter boards on a new rear plate (replaces the pack cover), wires drawn as capsules.
Trunk-frame mm (pack coordinates). Board sizes: XL4015 54 x 23 x 16 (common module, kit unit unmeasured), 5991 33 x 23 x 8.
"""
import sys
from pathlib import Path
import numpy as np, mujoco, imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont
REAL = Path('/Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014')
WORLD = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world')
sys.path.insert(0, str(REAL))
from static_gap import cfg, NAMES, HOME, feet_flat_rot, setup, sole_points
import evaluate_delay as ev
OUT = Path(__file__).resolve().parent
mm = 0.001

spec = mujoco.MjSpec.from_file(str(ev.MODEL_DIR / 'scene.xml'))
trunk = spec.body('trunk_base')
for g in list(spec.geoms):
    if g.name in ('power_support', 'np_f970'):
        spec.delete(g)
for i, (f, rgba) in enumerate([('rear_pack.stl', (.93, .5, .1, 1)), ('openrb-board-upright.stl', (.15, .35, .2, 1))]):
    a = spec.add_mesh(name=f'pk{i}', file=str(WORLD / f), scale=[mm] * 3)
    trunk.add_geom(name=f'pk{i}', type=mujoco.mjtGeom.mjGEOM_MESH, meshname=a.name, contype=0, conaffinity=0, mass=0, rgba=rgba, group=2)

def box(name, lo, hi, rgba):
    lo, hi = np.array(lo, float), np.array(hi, float)
    trunk.add_geom(name=name, type=mujoco.mjtGeom.mjGEOM_BOX, pos=(lo + hi) / 2 * mm, size=(hi - lo) / 2 * mm,
                   rgba=rgba, contype=0, conaffinity=0, mass=0, group=2)
def wire(name, pts, rgba, r=1.3):
    for k in range(len(pts) - 1):
        a, b = np.array(pts[k], float) * mm, np.array(pts[k + 1], float) * mm
        trunk.add_geom(name=f'{name}{k}', type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=np.r_[a, b], size=[r * mm, 0, 0],
                       rgba=rgba, contype=0, conaffinity=0, mass=0, group=2)

PLATE = (1, 1, 1, .28); BLUE = (.12, .3, .9, 1); BLK = (.08, .08, .08, 1); CU = (.75, .75, .75, 1)
# plate: 2 mm back wall, side walls, open towards the pack cover plane
box('plate_back', (-69, -28, -32), (-67, 28, 41), PLATE)
box('plate_l', (-69, -28, -32), (-47, -26, 41), PLATE); box('plate_r', (-69, 26, -32), (-47, 28, 41), PLATE)
box('plate_top', (-69, -28, 39), (-47, 28, 41), PLATE); box('plate_bot', (-69, -28, -32), (-47, 28, -30), PLATE)
box('xl1', (-65, -27, -6), (-49, 27, 17), BLUE); box('xl2', (-65, -27, 18), (-49, 27, 41), BLUE)
box('xl1_pot', (-66, 20, -4), (-62, 26, 2), (.2, .2, .2, 1)); box('xl2_pot', (-66, 20, 20), (-62, 26, 26), (.2, .2, .2, 1))
for n, y in (('xl1_in', -27), ('xl1_out', 27)):
    box(n, (-60, y - 1 if y < 0 else y - 7, -5), (-53, y + 7 if y < 0 else y + 1, 3), (.2, .6, .2, 1))
    box(n + '2', (-60, y - 1 if y < 0 else y - 7, 19), (-53, y + 7 if y < 0 else y + 1, 27), (.2, .6, .2, 1))
box('pd', (-57, -16.5, -31), (-49, 16.5, -8), BLK); box('pd_term', (-60, -12, -12), (-55, -2, -8), (.2, .6, .2, 1))
box('pd_usbc', (-55, -4.5, -33), (-51, 4.5, -29), CU)
# wires (one line per pair)
wire('w15', [(-57, -7, -10), (-62, -27, -10), (-62, -27, -1), (-57, -27, -1)], (.9, .1, .1, 1))      # 15 V 5991 -> XL1 IN
wire('w15b', [(-62, -27, -1), (-62, -27, 23), (-57, -27, 23)], (.9, .1, .1, 1))                       # -> XL2 IN
wire('w7', [(-57, 27, -1), (-62, 27, 6), (-60, 12, 6), (-46, 8, 6), (-41, 8, 6), (-41, 6, 26), (-34, -4, 27), (-30, -6, 26)],
     (1, .55, .05, 1))                                                                                 # 7 V XL1 OUT -> J4
wire('w5', [(-57, 27, 23), (-62, 27, 30), (-60, 12, 30), (-46, 4, 30), (-41, 2, 31), (-30, 0, 34), (-20, 0, 36), (-12, 0, 44), (-8, 0, 56)],
     (.95, .85, .1, 1))                                                                                # 5 V XL2 OUT -> notch -> Pi
wire('usb_pwr', [(-53, 0, -33), (-53, 0, -60), (-60, 0, -95), (-75, 0, -118)], (.6, .6, .6, 1), r=2.0)  # USB-C power to the 5991
wire('usb_orb', [(-27, 0, -43), (-27, 0, -60), (-40, 0, -95), (-60, 0, -118)], (.3, .3, .3, 1), r=2.0)  # OpenRB USB data to the Mac

bam = None
m = spec.compile(); m.vis.global_.offwidth = 1200; m.vis.global_.offheight = 900
d = mujoco.MjData(m)
# HOME pose, feet flat, like render_ref.py
names = NAMES
Rt = feet_flat_rot(m, d, names, HOME); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel())
setup(m, d, names, HOME, q); z = np.vstack(sole_points(m, d))[:, 2].min(); d.qpos[2] -= z; mujoco.mj_forward(m, d)
tb = m.body('trunk_base').id
def world(p):
    return d.xpos[tb] + d.xmat[tb].reshape(3, 3) @ (np.array(p, float) * mm)

r = mujoco.Renderer(m, height=600, width=600)
def shot(az, el, dist, look, hide=()):
    opt = mujoco.MjvOption()
    cam = mujoco.MjvCamera(); cam.lookat = world(look); cam.distance = dist; cam.azimuth = az; cam.elevation = el
    r.update_scene(d, camera=cam, scene_option=opt)
    if hide:
        scn = r.scene
        for i in range(scn.ngeom):
            gid = scn.geoms[i].objid
            if scn.geoms[i].objtype == mujoco.mjtObj.mjOBJ_GEOM and m.geom(gid).name in hide:
                scn.geoms[i].rgba[3] = 0.0
    return r.render()

PL = ('plate_back', 'plate_l', 'plate_r', 'plate_top', 'plate_bot')
views = [('rear 3/4, plate on', 40, -15, 0.30, (-45, 0, 0), ()),
         ('rear, plate off', 0, 0, 0.26, (-45, 0, 0), PL),
         ('side 3/4, plate + pack hidden: route to J4 and notch', 60, 20, 0.26, (-40, 0, 5), PL + ('pk0',)),
         ('whole, side', 90, 0, 0.55, (0, 0, -10), ())]
try: font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 22)
except Exception: font = ImageFont.load_default()
imgs = []
for label, az, el, dist, look, hide in views:
    img = Image.fromarray(shot(az, el, dist, look, hide)); dr = ImageDraw.Draw(img)
    dr.rectangle((0, 0, 600, 34), fill=(0, 0, 0)); dr.text((8, 6), label, fill=(255, 255, 255), font=font); imgs.append(np.array(img))
grid = np.vstack([np.hstack(imgs[:2]), np.hstack(imgs[2:])])
img = Image.fromarray(grid); dr = ImageDraw.Draw(img)
legend = ['blue: XL4015 x2 (7 V servos, 5 V Pi)', 'black: Adafruit 5991 (USB-C PD, 15 V)', 'red: 15 V in', 'orange: 7 V -> OpenRB J4',
          'yellow: 5 V -> plate notch -> neck -> Pi', 'grey: USB-C power (down)', 'dark grey: OpenRB USB data to the Mac (existing floor slot)']
y0 = 1200 - 24 * len(legend) - 8
dr.rectangle((0, y0 - 6, 600, 1200), fill=(0, 0, 0))
for i, t in enumerate(legend): dr.text((8, y0 + 24 * i), t, fill=(255, 255, 255), font=font)
img.save(OUT / 'back-plate-B2-wiring.png'); print('ok')
