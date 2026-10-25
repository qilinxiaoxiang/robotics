"""Saddle V2 renders on the as-built model at HOME (feet flat): rear 3/4 with the lid on (port window, camera plug), +y side
(pigtail bulge, lid screw), rear-top view with the lid hidden (6530B heatsink, blower, Dupont housings in the open strip,
antenna on the front wall), front 3/4 lid off (open header strip, floor cut). Colours: saddle body, lid and tray orange
(interim filament, white is out), PCB dark green, 6530B light grey, Dupont housings black, antenna light blue, plug grey.
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
add(BUILD / 'saddle_body-world.stl', (.95, .5, .1, 1), 'saddle'); add(BUILD / 'saddle_lid-world.stl', (.98, .55, .12, 1), 'lid'); add(BUILD / 'saddle_tray-world.stl', (.9, .45, .08, 1), 'tray')
COL = dict(a7z_pcb=(.05, .3, .12, 1), soc_a733=(.05, .05, .05, 1), ram=(.1, .1, .1, 1), pmic_area=(.1, .1, .1, 1), wifi_module_fcu760k=(.6, .6, .62, 1),
           usb_c_otg_dp=(.7, .7, .72, 1), usb_c_power=(.7, .7, .72, 1), micro_hdmi=(.7, .7, .72, 1), fan_connector=(.9, .9, .9, 1), ipex_socket=(.8, .7, .2, 1),
           microsd_card=(.1, .1, .5, 1), heatsink_6530b=(.78, .8, .82, 1), thermal_pad_6530b=(.5, .5, .55, 1), dupont_housings=(.08, .08, .08, 1),
           antenna=(.5, .7, .95, 1), usb_c_plug=(.6, .6, .62, 1))
for n, c in COL.items():
    add(BUILD / f'{n}-world.stl', c, n)


def wire(name, pts, rgba, r):
    for k in range(len(pts) - 1):
        trunk.add_geom(name=f'{name}{k}', type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=np.r_[np.array(pts[k]) * mm, np.array(pts[k + 1]) * mm],
                       size=[r * mm, 0, 0], rgba=rgba, contype=0, conaffinity=0, mass=0, group=2)


# camera leads from the right-angle plug's +y end up the left side of the neck with the head bundle; IMU/UART/5 V Dupont leads up through the floor cut
wire('cam_cable', [(-52.0, 7.0, 53.0), (-52.0, 30.0, 56.0), (-30.0, 38.0, 60.0), (-8.0, 38.0, 66.0), (6.0, 30.0, 72.0), (10.0, 16.0, 80.0), (13.0, 13.0, 98.0)], (.55, .55, .58, 1), 1.0)   # D-023: the four thin camera leads leave the pigtail's +y end and go up the left (+y) side of the neck with the head bundle (as built, no clips) into the floor opening
for i, (y, col) in enumerate(((-9.0, (.9, .1, .1, 1)), (-6.0, (.1, .1, .1, 1)), (-3.0, (.95, .85, .1, 1)), (0.0, (.1, .6, .2, 1)))):
    wire(f'lead{i}', [(-14.0, y, 40.0), (-14.0, y, 56.0), (-15.5 if i % 2 else -13.0, y - 12.0, 64.5)], col, 0.6)
m = spec.compile(); m.vis.global_.offwidth = 1800; m.vis.global_.offheight = 700
d = mujoco.MjData(m)
Rt = feet_flat_rot(m, d, NAMES, HOME); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel())
setup(m, d, NAMES, HOME, q); z = np.vstack(sole_points(m, d))[:, 2].min(); d.qpos[2] -= z; mujoco.mj_forward(m, d)
tb = m.body('trunk_base').id
world = lambda p: d.xpos[tb] + d.xmat[tb].reshape(3, 3) @ (np.array(p, float) * mm)
yaw = float(np.degrees(np.arctan2(d.xmat[tb].reshape(3, 3)[1, 0], d.xmat[tb].reshape(3, 3)[0, 0])))
r = mujoco.Renderer(m, height=600, width=600)


def shot(az, el, dist, look, hide=(), hide_above=None):
    cam = mujoco.MjvCamera(); cam.lookat = world(look); cam.distance = dist; cam.azimuth = az + yaw; cam.elevation = el
    r.update_scene(d, camera=cam); scn = r.scene
    zcut = None if hide_above is None else world((0, 0, hide_above))[2]
    for i in range(scn.ngeom):
        g = scn.geoms[i]
        if g.objtype == mujoco.mjtObj.mjOBJ_GEOM and (m.geom(g.objid).name in hide or (zcut is not None and g.pos[2] > zcut)):
            g.rgba[3] = 0.0
    return r.render()


try:
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 15)
except Exception:
    font = ImageFont.load_default()
(HERE / 'renders').mkdir(exist_ok=True)
PR = B['params']
views = [('rear', f"rear 3/4, lid on: port window in the rear wall, camera plug, lid top z {PR['LID']['z1']}", -50, -15, 0.19, (-30, 0, 52), (), None),
         ('side-minus-y', '-y side: exhaust slots (fin end), microSD slot, lid screw, open header strip at the front (head hidden)', 90, -5, 0.19, (-26, 0, 54), (), 80),
         ('side-plus-y', '+y side: pigtail bulge beside the IPEX socket, lid screw (head hidden)', -90, -5, 0.19, (-26, 0, 54), (), 80),
         ('top-lid-off', 'top view, lid off: 6530B heatsink + blower, housings in the open strip, antenna on the front wall (head hidden)', 180, -88, 0.17, (-25, 0, 58), ('lid',), 80),
         ('front-lid-off', 'front 3/4, lid off: header strip open, torso leads up the floor cut (head hidden)', 140, -40, 0.19, (-24, 0, 54), ('lid',), 80)]
tiles = []
for key, label, az, el, dist, look, hide, ha in views:
    img = Image.fromarray(shot(az, el, dist, look, hide, ha)); img.save(HERE / 'renders' / f'saddle-{key}.png')
    dr = ImageDraw.Draw(img); dr.rectangle((0, 0, 600, 30), fill=(0, 0, 0)); dr.text((8, 5), label, fill=(255, 255, 255), font=font); tiles.append(np.array(img))
img = Image.fromarray(np.hstack(tiles)); W, H = img.size
c = B['checks']
leg = [f"A7Z saddle V2 (D-028): body {B['parts']['saddle_body']['volume_mm3'] / 1000:.1f} cm3, lid {B['parts']['saddle_lid']['volume_mm3'] / 1000:.1f} cm3, tray {B['parts']['saddle_tray']['volume_mm3'] / 1000:.1f} cm3; board underside z {PR['ZU']}, 6530B on the board, lid over the heatsink only",
       f"antenna to fin block {c['antenna_to_heatsink_fin_block_mm']} mm (to the nearest boss {c['antenna_to_heatsink_boss_mm']}), roof-screw head to tray {c['gap_roof_screw_head_to_tray_mm']} mm, port faces {c['port_face_inside_rear_outer_face_mm']} mm inside the rear wall; zero overlap with shells, pack, rear box, head at HOME",
       'orange saddle (interim colour) | green PCB | light-grey 6530B heatsink | black Dupont housings (open strip) | light-blue antenna on the front wall | grey USB-C camera plug behind the rear wall']
canvas = Image.new('RGB', (W, H + 24 * len(leg) + 12), (0, 0, 0)); canvas.paste(img, (0, 0)); dr = ImageDraw.Draw(canvas)
for i, t in enumerate(leg):
    dr.text((8, H + 6 + 24 * i), t, fill=(230, 230, 230), font=font)
canvas.save(HERE / 'renders' / 'saddle.png'); print('ok yaw', round(yaw, 2))
