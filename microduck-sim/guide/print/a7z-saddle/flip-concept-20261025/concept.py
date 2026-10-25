"""Concept only (no CAD change): A7Z turned 180 deg in the saddle, USB/HDMI at the rear wall, header at the front."""
import sys, json
from pathlib import Path
import numpy as np, mujoco, trimesh
from PIL import Image, ImageDraw, ImageFont
SAD = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/a7z-saddle'); MS = SAD.parents[2]; BUILD = SAD / 'build'
OUT = Path(__file__).resolve().parent; TMP = Path('/tmp/flip-concept-stl'); TMP.mkdir(exist_ok=True)
REAL = MS / 'hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014'
WORLD = MS / 'guide/print/world'; BP = MS / 'guide/print/back-plate'
sys.path.insert(0, str(REAL))
from static_gap import NAMES, HOME, feet_flat_rot, setup, sole_points
import evaluate_delay as ev
mm = 0.001
FAN = sys.argv[1] if len(sys.argv) > 1 else 'A'      # A: 30 mm fan, lid 7 mm over the rear; B: 25 mm fan
spec = mujoco.MjSpec.from_file(str(ev.MODEL_DIR / 'scene.xml')); trunk = spec.body('trunk_base')
for g in list(spec.geoms):
    if g.name in ('power_support', 'np_f970'): spec.delete(g)
def addm(f, rgba, tag):
    a = spec.add_mesh(name=f'm_{tag}', file=str(f), scale=[mm] * 3)
    trunk.add_geom(name=tag, type=mujoco.mjtGeom.mjGEOM_MESH, meshname=a.name, contype=0, conaffinity=0, mass=0, rgba=rgba, group=2)
def box(tag, lo, hi, rgba):
    lo, hi = np.array(lo, float), np.array(hi, float)
    trunk.add_geom(name=tag, type=mujoco.mjtGeom.mjGEOM_BOX, pos=(lo + hi) / 2 * mm, size=(hi - lo) / 2 * mm, rgba=rgba, contype=0, conaffinity=0, mass=0, group=2)
def wire(name, pts, rgba, r):
    for k in range(len(pts) - 1):
        trunk.add_geom(name=f'{name}{k}', type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=np.r_[np.array(pts[k]) * mm, np.array(pts[k + 1]) * mm],
                       size=[r * mm, 0, 0], rgba=rgba, contype=0, conaffinity=0, mass=0, group=2)
addm(WORLD / 'rear_pack.stl', (.93, .5, .1, 1), 'pack'); addm(BP / 'rear_frame-world.stl', (.12, .12, .13, 1), 'frame'); addm(BP / 'rear_lid-world.stl', (.2, .2, .22, 1), 'rlid')
COL = dict(a7z_pcb=(.05, .3, .12, 1), soc_a733=(.05, .05, .05, 1), ram=(.1, .1, .1, 1), pmic_area=(.1, .1, .1, 1), wifi_module_fcu760k=(.6, .6, .62, 1),
           usb_c_otg_dp=(.75, .75, .78, 1), usb_c_power=(.75, .75, .78, 1), micro_hdmi=(.75, .75, .78, 1), fan_connector=(.9, .9, .9, 1), ipex_socket=(.8, .7, .2, 1),
           microsd_card=(.1, .1, .5, 1), heatsink=(.85, .45, .1, 1), dupont_housings=(.08, .08, .08, 1))
for n, c in COL.items():
    m = trimesh.load(BUILD / f'{n}-world.stl'); v = m.vertices.copy(); v[:, 0] = -55.9 - v[:, 0]; v[:, 1] *= -1
    t = trimesh.Trimesh(v, m.faces[:, ::-1]); t.export(TMP / f'{n}.stl'); addm(TMP / f'{n}.stl', c, n)
W = (.92, .92, .9, .28); WL = (.95, .95, .93, .22)
X0, X1, HW, T, ZB, ZL0 = -45.0, -5.0, 34.4, 1.6, 43.0, 63.8
XR = {'A': -52.0, 'B': -47.0}[FAN]          # lid / fan-pocket rear face
box('wall_l', (X0, HW - T, ZB), (X1, HW, ZL0), W); box('wall_r', (X0, -HW, ZB), (X1, -HW + T, ZL0), W)
box('wall_f', (X1 - T, -HW, 46.5), (X1, HW, ZL0), W)
box('wall_b_lo', (X0, -HW, ZB), (X0 + T, HW, 46.0), W); box('wall_b_hi', (X0, -HW, 55.5), (X0 + T, HW, ZL0), W)
box('wall_b_mid1', (X0, -2.0, 46.0), (X0 + T, 15.0, 55.5), W); box('wall_b_mid2', (X0, 25.0, 46.0), (X0 + T, HW, 55.5), W); box('wall_b_mid3', (X0, -HW, 46.0), (X0 + T, -29.0, 55.5), W)
box('lid', (XR, -HW, ZL0), (X1, HW, 74.0), WL)
fs = 30.0 if FAN == 'A' else 25.0
box('fan', (-20.4 - fs, 1.4 - fs / 2, 64.4), (-20.4, 1.4 + fs / 2, 64.4 + (8 if FAN == 'A' else 7)), (.25, .25, .27, 1))
box('antenna', (X1 - T - 0.3, -21, 49.5), (X1 - T, 21, 61.5), (.5, .7, .95, 1))
# right-angle camera plug on port 2, leg to +y (port 1 stays free), sticks 10.5 mm out of the rear wall
box('cam_plug', (-55.5, -14.8, 47.85), (-44.7, 7.0, 55.85), (.6, .6, .62, 1))
CAM = [(10.8, 16.5, 60.0), (2.0, 16.0, 47.0), (-4.0, 14.0, 44.5), (-9.5, 24.0, 52.0), (-12.0, 30.0, 57.0), (-42.0, 30.0, 57.0), (-47.5, 28.0, 56.0),
       (-51.0, 18.0, 52.5), (-51.0, 7.0, 51.85)]
wire('cam', CAM, (.35, .35, .38, 1), 2.0)
NECK = [(10.8, 16.5, 60.0), (2.0, 10.0, 47.0), (-3.0, 6.0, 44.5)]
for i, (y, col) in enumerate(((-12, (.9, .1, .1, 1)), (-6, (.1, .1, .1, 1)), (0, (.95, .85, .1, 1)), (6, (.1, .6, .2, 1)), (12, (.2, .3, .9, 1)))):
    xp = -15.3 if i % 2 else -17.9
    wire(f'hw{i}', [(-3.0, y * .5, 44.5), (-8.0, y, 50.0), (-9.5, y, 64.0), (-12.5, y, 67.5), (xp, y, 66.0), (xp, y, 63.1)], col, 0.65)
for i, (y, col) in enumerate(((-22, (.9, .1, .1, 1)), (-19, (.1, .1, .1, 1)), (-16, (.95, .55, .1, 1)))):
    wire(f'tw{i}', [(-10.0, y * .6, 38.0), (-10.0, y, 50.0), (-10.0, y, 64.0), (-12.5, y, 67.5), (-17.9, y, 66.0), (-17.9, y, 63.1)], col, 0.65)
wire('coax', [(X1 - T - 0.6, 21, 55.0), (-7.5, 29.5, 52.0), (-26.0, 31.0, 50.5), (-28.0, 30.5, 49.9)], (.85, .75, .3, 1), 0.6)
wire('usbc1', [(-44.7, -22.0, 50.25), (-70.0, -22.0, 50.25), (-80.0, -22.0, 45.0)], (.15, .15, .15, 1), 1.8)
box('usbc1_body', (-62.0, -28.0, 47.0), (-44.7, -16.0, 53.5), (.12, .12, .12, 1))
m = spec.compile(); m.vis.global_.offwidth = 1800; m.vis.global_.offheight = 900
d = mujoco.MjData(m); Rt = feet_flat_rot(m, d, NAMES, HOME); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel())
setup(m, d, NAMES, HOME, q); z = np.vstack(sole_points(m, d))[:, 2].min(); d.qpos[2] -= z; mujoco.mj_forward(m, d)
tb = m.body('trunk_base').id; world = lambda p: d.xpos[tb] + d.xmat[tb].reshape(3, 3) @ (np.array(p, float) * mm)
yaw = float(np.degrees(np.arctan2(d.xmat[tb].reshape(3, 3)[1, 0], d.xmat[tb].reshape(3, 3)[0, 0])))
r = mujoco.Renderer(m, height=700, width=700)
def shot(az, el, dist, look):
    cam = mujoco.MjvCamera(); cam.lookat = world(look); cam.distance = dist; cam.azimuth = az + yaw; cam.elevation = el
    r.update_scene(d, camera=cam); scn = r.scene; zcut = world((0, 0, 80))[2]
    for i in range(scn.ngeom):
        g = scn.geoms[i]
        if g.pos[2] > zcut: g.rgba[3] = 0.0
    return r.render()
try: font = ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc', 22)
except Exception: font = ImageFont.load_default()
views = [('rear', '后方斜看：USB-C ①② 和 HDMI 朝后，摄像头弯头插 ②，① 空着', -35, -15, 0.22, (-35, 0, 54)),
         ('top', '俯视（上方是车头）：排针在前，风扇在后，摄像头线贴左墙内侧', 0, -89, 0.19, (-28, 0, 55)),
         ('left', '左侧看：盖子在 USB 口上方向后伸出（方案 %s）' % FAN, -90, -5, 0.21, (-28, 0, 58))]
tiles = []
for key, label, az, el, dist, look in views:
    img = Image.fromarray(shot(az, el, dist, look)); dr = ImageDraw.Draw(img)
    dr.rectangle((0, 0, 700, 34), fill=(255, 255, 255)); dr.text((8, 5), label, fill=(20, 20, 20), font=font); tiles.append(np.array(img))
Image.fromarray(np.hstack(tiles)).save(OUT / f'flip-{FAN}.png'); print('ok', yaw)
L = lambda p: float(np.linalg.norm(np.diff(np.array(p, float), axis=0), axis=1).sum())
print('cam route from neck point to plug end mm', round(L(CAM), 1), 'now', round(L([(10.8, 16.5, 60), (6.5, 25, 57), (3, 27, 53)]), 1))
print('coax', round(L([(X1 - T - 0.6, 21, 55.0), (-7.5, 29.5, 52.0), (-26.0, 31.0, 50.5), (-28.0, 30.5, 49.9)]), 1))
print('head wire in-saddle', round(L([(-3.0, 0, 44.5), (-8.0, 0, 50.0), (-9.5, 0, 64.0), (-12.5, 0, 67.5), (-17.9, 0, 66.0), (-17.9, 0, 63.1)]), 1))
