"""Concept render: enlarged left-rear head exit + neck bundler. Parts from the print-gate solid cache (HOME pose, robot frame mm).
argv: out.png  json-of-extras  (extras: {"routes": {name: {"pts": [...], "r": .., "rgba": [..]}}, "cyl": [...], "boxes": [...]})
Run with ~/.venvs/microduck-dyn/bin/python."""
import sys, json, tempfile
from pathlib import Path
import numpy as np, mujoco, trimesh
from PIL import Image, ImageDraw, ImageFont
C = Path('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/ia-cache')
out = sys.argv[1]; X = json.loads(Path(sys.argv[2]).read_text())
YEL, WHITE, SERVO, ORANGE = (.93, .78, .2, 1), (.92, .92, .9, 1), (.22, .24, .26, 1), (.9, .5, .15, 1)
PARTS = {'head_bottom': YEL, 'jaw_support': ORANGE, 'head_yaw_link': (.65, .55, .5, 1), 'jaw_frame': YEL,
         'motor11': SERVO, 'motor12': SERVO, 'motor13': SERVO, 'motor14': SERVO, 'motor15': SERVO,
         'neck_pitch': YEL, 'neck_link_b': YEL, 'neck_pitch_ring': YEL, 'head_roll_ring_a': YEL, 'head_roll_ring_b': YEL,
         'shell_left': WHITE, 'saddle_body': (.97, .97, .95, 1), 'saddle_lid': (.97, .97, .95, 1), 'sd_usb_c_plug': (.6, .6, .62, 1),
         'touch_xiao': (.1, .45, .9, 1), 'amplifier': (.1, .5, .2, 1), 'speaker': (.3, .3, .3, 1), 'rear_pack': (.93, .5, .1, 1)}
HIDE = set(X.get('hide', []))
tmp = Path(tempfile.mkdtemp())
spec = mujoco.MjSpec(); wb = spec.worldbody
spec.visual.global_.offwidth = 1800; spec.visual.global_.offheight = 1200
spec.visual.headlight.ambient = [.45, .45, .45]; spec.visual.headlight.diffuse = [.6, .6, .6]
for k, rgba in PARTS.items():
    if k in HIDE: continue
    f = tmp / f'{k}.stl'
    if k in X.get('override', {}):
        mm_ = trimesh.load(X['override'][k], force='mesh'); mm_.apply_scale(0.001); mm_.export(f)
    else:
        z = np.load(C / f'solid-{k}.npz'); trimesh.Trimesh(z['v'] * 0.001, z['f'], process=False).export(f)
    spec.add_mesh(name=f'm_{k}', file=str(f))
    wb.add_geom(name=k, type=mujoco.mjtGeom.mjGEOM_MESH, meshname=f'm_{k}', rgba=rgba, contype=0, conaffinity=0)
mm = 0.001
for name, r in X.get('routes', {}).items():
    P = np.array(r['pts'], float) * mm
    for i in range(len(P) - 1):
        wb.add_geom(name=f'{name}{i}', type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=np.r_[P[i], P[i + 1]], size=[r['r'] * mm, 0, 0], rgba=r['rgba'], contype=0, conaffinity=0)
for i, c in enumerate(X.get('cyl', [])):
    wb.add_geom(name=f'cyl{i}', type=mujoco.mjtGeom.mjGEOM_CYLINDER, fromto=np.r_[np.array(c['a']) * mm, np.array(c['b']) * mm], size=[c['r'] * mm, 0, 0], rgba=c['rgba'], contype=0, conaffinity=0)
for i, b in enumerate(X.get('boxes', [])):
    lo, hi = np.array(b['lo'], float), np.array(b['hi'], float)
    wb.add_geom(name=f'box{i}', type=mujoco.mjtGeom.mjGEOM_BOX, pos=(lo + hi) / 2 * mm, size=(hi - lo) / 2 * mm, rgba=b['rgba'], contype=0, conaffinity=0)
m = spec.compile(); d = mujoco.MjData(m); mujoco.mj_forward(m, d)
R = mujoco.Renderer(m, height=640, width=640)
try:
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 19)
except Exception:
    font = ImageFont.load_default()
tiles = []
for v in X['views']:
    cam = mujoco.MjvCamera(); cam.lookat = np.array(v['look']) * mm; cam.distance = v['dist']; cam.azimuth = v['az']; cam.elevation = v['el']
    R.update_scene(d, camera=cam); img = Image.fromarray(R.render()); dr = ImageDraw.Draw(img)
    dr.rectangle((0, 0, 640, 28), fill=(0, 0, 0)); dr.text((8, 4), v['label'], fill=(255, 255, 255), font=font)
    for t in v.get('notes', []):
        dr.text(tuple(t['xy']), t['text'], fill=tuple(t.get('rgb', (0, 0, 0))), font=font)
    tiles.append(np.array(img))
img = Image.fromarray(np.hstack(tiles)); W, H = img.size
leg = X.get('legend', [])
canvas = Image.new('RGB', (W, H + 26 * len(leg) + 10), (255, 255, 255)); canvas.paste(img, (0, 0)); dr = ImageDraw.Draw(canvas)
for i, t in enumerate(leg):
    dr.text((10, H + 6 + 26 * i), t, fill=(20, 20, 20), font=font)
canvas.save(out); print('ok', out)
