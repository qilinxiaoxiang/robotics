"""Saddle renders on the as-built model at HOME (feet flat): rear 3/4 with the lid on, +y side (microSD slot, exhaust
slots), rear-top isometric with the lid hidden (board, Dupont housings, copper, antenna strip), front 3/4 lid off (fan
pocket is on the lid, so the fan is shown as its envelope). Colours: saddle body and lid white (scheme C shells), PCB
dark green, A733 black, copper orange, fan dark grey, Dupont housings black, antenna strip light blue, USB-C plug grey.
Run with ~/.venvs/microduck-dyn/bin/python render_views.py (writes renders/saddle-*.png and renders/saddle.png)."""
import sys, json
from pathlib import Path
import numpy as np, mujoco
from PIL import Image, ImageDraw, ImageFont
HERE = Path(__file__).resolve().parent; MS = HERE.parents[2]
REAL = MS / 'hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014'
WORLD = MS / 'guide/print/world'; BP = MS / 'guide/print/back-plate'; BUILD = HERE / 'build'
sys.path.insert(0, str(REAL))
from static_gap import NAMES, HOME, feet_flat_rot, setup, sole_points
import evaluate_delay as ev
mm = 0.001
B = json.loads((BUILD / 'build.json').read_text())
spec = mujoco.MjSpec.from_file(str(ev.MODEL_DIR / 'scene.xml'))
trunk = spec.body('trunk_base')
for g in list(spec.geoms):
    if g.name in ('power_support', 'np_f970'):
        spec.delete(g)


def add(f, rgba, tag):
    a = spec.add_mesh(name=f'm_{tag}', file=str(f), scale=[mm] * 3)
    trunk.add_geom(name=tag, type=mujoco.mjtGeom.mjGEOM_MESH, meshname=a.name, contype=0, conaffinity=0, mass=0, rgba=rgba, group=2)


add(WORLD / 'rear_pack.stl', (.93, .5, .1, 1), 'pack'); add(WORLD / 'openrb-board-upright.stl', (.15, .35, .2, 1), 'orb')
add(BP / 'rear_frame-world.stl', (.12, .12, .13, 1), 'frame'); add(BP / 'rear_lid-world.stl', (.2, .2, .22, 1), 'rlid')
add(BUILD / 'saddle_body-world.stl', (.92, .92, .9, 1), 'saddle'); add(BUILD / 'saddle_lid-world.stl', (.95, .95, .93, 1), 'lid')
COL = dict(a7z_pcb=(.05, .3, .12, 1), soc_a733=(.05, .05, .05, 1), ram=(.1, .1, .1, 1), pmic_area=(.1, .1, .1, 1), wifi_module_fcu760k=(.6, .6, .62, 1),
           usb_c_otg_dp=(.7, .7, .72, 1), usb_c_power=(.7, .7, .72, 1), micro_hdmi=(.7, .7, .72, 1), fan_connector=(.9, .9, .9, 1), ipex_socket=(.8, .7, .2, 1),
           microsd_card=(.1, .1, .5, 1), heatsink=(.85, .45, .1, 1), thermal_pad=(.5, .5, .55, 1), fan=(.25, .25, .27, 1), dupont_housings=(.08, .08, .08, 1),
           antenna=(.5, .7, .95, 1), usb_c_plug=(.6, .6, .62, 1))
for n, c in COL.items():
    add(BUILD / f'{n}-world.stl', c, n)


def wire(name, pts, rgba, r):
    for k in range(len(pts) - 1):
        trunk.add_geom(name=f'{name}{k}', type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=np.r_[np.array(pts[k]) * mm, np.array(pts[k + 1]) * mm],
                       size=[r * mm, 0, 0], rgba=rgba, contype=0, conaffinity=0, mass=0, group=2)


# USB-C camera cable from the plug forward and down to the neck bundle; IMU/UART/5 V Dupont leads up through the floor cut
wire('cam_cable', [(-6.0, 9.0, 51.0), (0.0, 7.0, 48.0), (-8.0, 4.0, 43.0), (-16.0, 3.0, 41.0)], (.55, .55, .58, 1), 1.8)
for i, (y, col) in enumerate(((-9.0, (.9, .1, .1, 1)), (-6.0, (.1, .1, .1, 1)), (-3.0, (.95, .85, .1, 1)), (0.0, (.1, .6, .2, 1)))):
    wire(f'lead{i}', [(-14.0, y, 40.0), (-14.0, y, 50.0), (-30.0, y - 12.0, 64.0), (-40.4 if i % 2 else -37.9, y - 12.0, 63.5)], col, 0.6)
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
(HERE / 'renders').mkdir(exist_ok=True)
PR = B['params']
views = [('rear', f"rear 3/4, lid on: saddle x {PR['X0']}..{PR['X1']}, top z {PR['Z_LID1']} (shell roof 42)", -50, -12, 0.30, (-30, 0, 45), ()),
         ('side-plus-y', '+y side: microSD slot, exhaust slots, lid screw', -90, 0, 0.30, (-26, 0, 50), ()),
         ('iso-lid-off', 'rear-top view, lid off: board, Dupont housings, copper, antenna', 20, -60, 0.24, (-25, 0, 58), ('lid',)),
         ('front-lid-off', 'front 3/4, lid off: USB-C plug notch, floor cut over the neck exit', 140, -35, 0.26, (-24, 0, 52), ('lid',))]
tiles = []
for key, label, az, el, dist, look, hide in views:
    img = Image.fromarray(shot(az, el, dist, look, hide)); img.save(HERE / 'renders' / f'saddle-{key}.png')
    dr = ImageDraw.Draw(img); dr.rectangle((0, 0, 600, 30), fill=(0, 0, 0)); dr.text((8, 5), label, fill=(255, 255, 255), font=font); tiles.append(np.array(img))
img = Image.fromarray(np.hstack(tiles)); W, H = img.size
c = B['checks']
leg = [f"A7Z saddle: body {B['parts']['saddle_body']['volume_mm3'] / 1000:.1f} cm3, lid {B['parts']['saddle_lid']['volume_mm3'] / 1000:.1f} cm3 (PETG ~1.27 g/cm3); board underside z {PR['ZU']}, fan 30x30x8 at z {PR['FAN']['z0']}..{PR['FAN']['z0'] + 8} in front of the Dupont housings",
       f"fan to copper {c['gap_fan_to_heatsink_mm']} mm, fan to Dupont {c['gap_fan_to_dupont_mm']} mm, roof-screw head to microSD socket {c['gap_roof_screw_head_to_microsd_socket_mm']} mm; zero overlap with shells, pack, rear box, head at HOME",
       'white saddle | green PCB | orange copper | grey fan (in the lid pocket) | black Dupont housings | light-blue antenna strip on the rear wall | grey USB-C camera plug']
canvas = Image.new('RGB', (W, H + 24 * len(leg) + 12), (0, 0, 0)); canvas.paste(img, (0, 0)); dr = ImageDraw.Draw(canvas)
for i, t in enumerate(leg):
    dr.text((8, H + 6 + 24 * i), t, fill=(230, 230, 230), font=font)
canvas.save(HERE / 'renders' / 'saddle.png'); print('ok yaw', round(yaw, 2))
