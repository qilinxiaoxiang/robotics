"""Layout C renders on the as-built model at HOME (feet flat): rear (lid on), -y side (USB-C plug), rear-top isometric with
the lid hidden. Black frame and lid, blue XL4015 (ROBOTIS mesh, decimated copies in render/), dark 5991, grey USB-C plug
(13 x 7.5 overmold envelope) and cable, orange 7 V and yellow 5 V pairs leaving the top slots.
Run with ~/.venvs/microduck-dyn/bin/python under the bounded runner. Writes renders/layout-C-*.png and renders/layout-C.png."""
import sys, json
from pathlib import Path
import numpy as np, mujoco
from PIL import Image, ImageDraw, ImageFont
HERE = Path(__file__).resolve().parent
REAL = Path('/Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014')
WORLD = HERE.parent / 'world'
sys.path.insert(0, str(REAL))
from static_gap import NAMES, HOME, feet_flat_rot, setup, sole_points
import evaluate_delay as ev
mm = 0.001
B = json.loads((HERE / 'build.json').read_text()); M = json.loads((HERE / 'mass_estimate.json').read_text())
spec = mujoco.MjSpec.from_file(str(ev.MODEL_DIR / 'scene.xml'))
trunk = spec.body('trunk_base')
for g in list(spec.geoms):
    if g.name in ('power_support', 'np_f970'):
        spec.delete(g)
def add(f, rgba, tag):
    a = spec.add_mesh(name=f'm_{tag}', file=str(f), scale=[mm] * 3)
    trunk.add_geom(name=tag, type=mujoco.mjtGeom.mjGEOM_MESH, meshname=a.name, contype=0, conaffinity=0, mass=0, rgba=rgba, group=2)
add(WORLD / 'rear_pack-v18.stl', (.93, .5, .1, 1), 'pack'); add(WORLD / 'openrb-board-upright.stl', (.15, .35, .2, 1), 'orb')
add(HERE / 'rear_frame-world.stl', (.12, .12, .13, 1), 'frame'); add(HERE / 'rear_lid-world.stl', (.2, .2, .22, 1), 'lid')
for nm in ('left', 'right'):
    add(HERE / 'render' / f'xl4015_{nm}.stl', (.12, .3, .9, 1), f'xl_{nm}')
add(HERE / 'pd5991-world.stl', (.03, .03, .03, 1), 'pd')
def box(name, lo, hi, rgba):
    lo, hi = np.array(lo, float), np.array(hi, float)
    trunk.add_geom(name=name, type=mujoco.mjtGeom.mjGEOM_BOX, pos=(lo + hi) / 2 * mm, size=(hi - lo) / 2 * mm, rgba=rgba, contype=0, conaffinity=0, mass=0, group=2)
def wire(name, pts, rgba, r):
    for k in range(len(pts) - 1):
        trunk.add_geom(name=f'{name}{k}', type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=np.r_[np.array(pts[k]) * mm, np.array(pts[k + 1]) * mm],
                       size=[r * mm, 0, 0], rgba=rgba, contype=0, conaffinity=0, mass=0, group=2)
box('usb_plug', (-57.0, -52.05, -38.64), (-49.5, -15.05, -25.64), (.7, .7, .72, 1))
wire('usb_cable', [(-53.25, -52.0, -32.1), (-53.25, -62.0, -32.1), (-58.0, -70.0, -60.0)], (.55, .55, .58, 1), 2.0)
# OUT pairs inside the box (checks.json 4_wireRoom.outRoute): up, over the board top, centre lane, passage; then 7 V to J4, 5 V to the notch
for nm, col, dy, dz, tail in (('left', (1, .55, .05, 1), 0.8, 0.8, [(-37.0, 0.0, 25.8), (-30.0, -6.0, 26.0)]),
                              ('right', (.95, .85, .1, 1), -0.8, -0.8, [(-37.0, 0.0, 24.2), (-30.0, 0.0, 30.0), (-20.0, 0.0, 34.5)])):
    e = np.array(B['boards'][nm]['outEntries']); xe, ym = e[0][0], float(e[:, 1].mean())
    wire(f'out_{nm}', [(xe, ym, e[0][2]), (xe, ym, 43.3), (xe, dy, 43.3), (xe, dy, 25.0 + dz), (-45.0, 0.0, 25.0 + dz)] + tail, col, 0.8)
m = spec.compile(); m.vis.global_.offwidth = 1800; m.vis.global_.offheight = 700
d = mujoco.MjData(m)
Rt = feet_flat_rot(m, d, NAMES, HOME); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel())
setup(m, d, NAMES, HOME, q); z = np.vstack(sole_points(m, d))[:, 2].min(); d.qpos[2] -= z; mujoco.mj_forward(m, d)
tb = m.body('trunk_base').id
world = lambda p: d.xpos[tb] + d.xmat[tb].reshape(3, 3) @ (np.array(p, float) * mm)
yaw = float(np.degrees(np.arctan2(d.xmat[tb].reshape(3, 3)[1, 0], d.xmat[tb].reshape(3, 3)[0, 0])))
r = mujoco.Renderer(m, height=600, width=600)
def shot(az, el, dist, look, hide=()):
    cam = mujoco.MjvCamera(); cam.lookat = world(look); cam.distance = dist; cam.azimuth = az + yaw; cam.elevation = el
    r.update_scene(d, camera=cam); scn = r.scene
    for i in range(scn.ngeom):
        g = scn.geoms[i]
        if g.objtype == mujoco.mjtObj.mjOBJ_GEOM and m.geom(g.objid).name in hide:
            g.rgba[3] = 0.0
    return r.render()
try:
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 20)
except Exception:
    font = ImageFont.load_default()
views = [('rear', 'rear 3/4 (lid on): box top z 46.5, shell top z 42', -50, -6, 0.26, (-45, 0, 15), ()),
         ('side-minus-y', '-y side: USB-C plug through the -y wall', 90, 0, 0.36, (-45, -10, -15), ()),
         ('iso-lid-off', 'rear-top isometric, lid removed (OUT pairs in the centre lane)', 25, -40, 0.28, (-55, 0, 5), ('lid',))]
tiles = []
for key, label, az, el, dist, look, hide in views:
    img = Image.fromarray(shot(az, el, dist, look, hide)); img.save(HERE / 'renders' / f'layout-C-{key}.png')
    dr = ImageDraw.Draw(img); dr.rectangle((0, 0, 600, 30), fill=(0, 0, 0)); dr.text((8, 5), label, fill=(255, 255, 255), font=font); tiles.append(np.array(img))
img = Image.fromarray(np.hstack(tiles)); W, H = img.size
leg = ['Layout C2: box x -67.1..-45, |y| <= 32.05 (flush), z -44..46.5; two XL4015 vertical at y +-17.2 (IN down, OUT up); 5991 flat at the bottom, USB-C to -y',
       f"printed {M['printedG']} g; robot +{M['netAddedG']} g -> {M['newTotalG']} g (estimate); whole-robot COM shift {M['comShiftMm']} mm",
       'blue XL4015 | black 5991 | grey USB-C plug | OUT pairs inside: centre lane -> 7 x 4 front-plate passage (z 23..27) | orange 7 V -> J4 | yellow 5 V -> notch']
canvas = Image.new('RGB', (W, H + 24 * len(leg) + 12), (0, 0, 0)); canvas.paste(img, (0, 0)); dr = ImageDraw.Draw(canvas)
for i, t in enumerate(leg):
    dr.text((8, H + 6 + 24 * i), t, fill=(230, 230, 230), font=font)
canvas.save(HERE / 'renders' / 'layout-C.png'); print('ok yaw', round(yaw, 2))
