"""Renders the ear options box-only on a light background and tiles them into renders/ear-options-compare.png.
python render_options.py  (CAD venv, bounded runner; reads options/*.stl from ear_options.py)."""
import json, math
from pathlib import Path
import numpy as np, mujoco
from PIL import Image, ImageDraw, ImageFont
HERE = Path(__file__).resolve().parent; LF = HERE.parent / 'layout-F'; O = HERE / 'options'; R = HERE / 'renders'; R.mkdir(exist_ok=True)
mm = 0.001
ORANGE, CAPC = [0.93, 0.5, 0.1, 1], [0.98, 0.64, 0.25, 1]
BLUE, BLACK, GREY, SCREW = [0.15, 0.3, 0.85, 1], [0.08, 0.08, 0.08, 1], [0.62, 0.62, 0.66, 1], [0.35, 0.35, 0.38, 1]
NETC = {'7V': [1.0, 0.5, 0.0, 1], '5V': [1.0, 0.85, 0.0, 1], 'p': [0.85, 0.05, 0.05, 1], 'q': [0.1, 0.1, 0.1, 1]}
OPTS = {'current': (LF / 'rear_frame-world.stl', LF / 'rear_lid-world.stl', []),
        'delete': (O / 'frame_delete-world.stl', O / 'lid_delete-world.stl', []),
        'hidden': (O / 'frame_hidden-world.stl', O / 'lid_hidden-world.stl', [O / 'screw_hidden-world.stl'])}
TITLES = {'current': 'Current (V1.11): +Y tail and -Y lug',
          'delete': '"delete": +Y ear gone, slot hook; -Y lug stays',
          'hidden': 'Hidden screw: both ears gone, M2x10 from the cap back'}
VIEWS = [('rear34+y', -38, -14, 0.15, [-57, 4, 0]), ('side+y', -90, -4, 0.13, [-55, 0, 0]), ('rear34-y', 38, -14, 0.15, [-57, -4, 0]),
         ('lower+y', -25, 18, 0.11, [-58, 10, -22]), ('cap inside', 150, -18, 0.13, [-60, 0, -8])]
HIDE = {'cap inside': {'frame', 'b0', 'b1', 'plug', 'pd'}}
CIRCLE = {'current': [(-59.7, 23.8, -33.6, 'tail'), (-59.7, -23.8, -17.4, 'lug')], 'delete': [(-59.7, -23.8, -17.4, 'lug')], 'hidden': []}
W = json.loads((LF / 'wires_F.json').read_text())
W_, H_ = 520, 520


def scene(opt):
    fr, ld, extra = OPTS[opt]
    sp = mujoco.MjSpec()
    sp.add_texture(name='sky', type=mujoco.mjtTexture.mjTEXTURE_SKYBOX, builtin=mujoco.mjtBuiltin.mjBUILTIN_GRADIENT,
                   rgb1=[1, 1, 1], rgb2=[0.93, 0.94, 0.96], width=64, height=64)
    sp.visual.headlight.ambient = [0.45, 0.45, 0.45]; sp.visual.headlight.diffuse = [0.55, 0.55, 0.55]
    sp.stat.extent = 0.2; sp.stat.center = [-0.055, 0, 0]
    wb = sp.worldbody
    wb.add_light(pos=[-0.3, 0.2, 0.4], dir=[1, -0.5, -1], diffuse=[0.35, 0.35, 0.35])
    meshes = [(fr, ORANGE, 'frame'), (ld, CAPC, 'lid'), (LF / 'xl4015_top_7V_render.stl', BLUE, 'b0'), (LF / 'xl4015_mid_5V_render.stl', BLUE, 'b1'),
              (LF / 'pd5991_F-world.stl', BLACK, 'pd')] + [(e, SCREW, f'x{i}') for i, e in enumerate(extra)]
    for f, rgba, tag in meshes:
        sp.add_mesh(name=f'm_{tag}', file=str(f), scale=[mm] * 3)
        wb.add_geom(name=tag, type=mujoco.mjtGeom.mjGEOM_MESH, meshname=f'm_{tag}', rgba=rgba, contype=0, conaffinity=0)
    lo, hi = np.array([-57.0, 15.05, -30.66]), np.array([-49.5, 40.05, -17.66])
    wb.add_geom(name='plug', type=mujoco.mjtGeom.mjGEOM_BOX, pos=(lo + hi) / 2 * mm, size=(hi - lo) / 2 * mm, rgba=GREY, contype=0, conaffinity=0)
    for k, v in W.items():
        pts = np.array(v['points'])
        for a, b in zip(pts[:-1], pts[1:]):
            if np.linalg.norm(b - a) > 1e-6:
                wb.add_geom(type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=np.r_[a * mm, b * mm], size=[0.9 * mm, 0, 0], rgba=NETC[v['net']], contype=0, conaffinity=0)
    m = sp.compile(); m.vis.global_.offwidth = W_; m.vis.global_.offheight = H_; m.vis.map.znear = 0.001
    return m


def project(m, cam, p):
    az, el = math.radians(cam.azimuth), math.radians(cam.elevation)
    f = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    pos = np.array(cam.lookat) - cam.distance * f
    r = np.cross(f, [0, 0, 1]); r /= np.linalg.norm(r); u = np.cross(r, f)
    q = np.array(p) * mm - pos; t = math.tan(math.radians(m.vis.global_.fovy) / 2)
    return W_ / 2 + (q @ r) / (q @ f) * (H_ / 2) / t, H_ / 2 - (q @ u) / (q @ f) * (H_ / 2) / t


try:
    FONT = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 19); FS = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 15)
except Exception:
    FONT = FS = ImageFont.load_default()
rows = []
for opt in OPTS:
    m = scene(opt); d = mujoco.MjData(m); mujoco.mj_forward(m, d); rd = mujoco.Renderer(m, height=H_, width=W_)
    tiles = []
    for key, az, el, dist, look in VIEWS:
        cam = mujoco.MjvCamera(); cam.lookat = np.array(look) * mm; cam.distance = dist; cam.azimuth = az; cam.elevation = el
        rd.update_scene(d, camera=cam)
        for gi in range(rd.scene.ngeom):
            g = rd.scene.geoms[gi]
            if key in HIDE and g.objtype == mujoco.mjtObj.mjOBJ_GEOM and (m.geom(g.objid).name in HIDE[key] or m.geom(g.objid).name == ''):
                g.rgba[3] = 0.0
        im = Image.fromarray(rd.render()); dr = ImageDraw.Draw(im)
        for (x, y, z, lab) in CIRCLE[opt]:
            if (key in ('rear34+y', 'side+y') and y < 0) or (key.endswith('-y') and y > 0) or key == 'cap inside':
                continue
            u, v = project(m, cam, (x, y, z)); rr = 30 if key != 'lower+y' else 48
            dr.ellipse((u - rr, v - rr, u + rr, v + rr), outline=(220, 0, 0), width=4); dr.text((u + rr + 4, v - 10), lab, fill=(220, 0, 0), font=FONT)
        im.save(R / f'{opt}-{key}.png'); tiles.append(im)
    row = Image.new('RGB', (W_ * len(tiles), H_ + 34), (255, 255, 255)); dr = ImageDraw.Draw(row)
    for i, t in enumerate(tiles):
        row.paste(t, (i * W_, 34))
    dr.text((10, 7), TITLES[opt], fill=(20, 20, 20), font=FONT)
    for i, (key, *_r) in enumerate(VIEWS):
        dr.text((i * W_ + 10, H_ + 34 - 24), 'view: ' + key, fill=(90, 90, 90), font=FS)
    rows.append(row)
out = Image.new('RGB', (rows[0].size[0], sum(r.size[1] for r in rows) + 40), (255, 255, 255)); y = 0
for r in rows:
    out.paste(r, (0, y)); y += r.size[1]
ImageDraw.Draw(out).text((10, y + 10), 'Layout F rear box, cap lower-corner options (study 2026-10-14). Orange = frame, light orange = cap, blue = XL4015, black = 5991, grey box = USB-C plug envelope.', fill=(40, 40, 40), font=FS)
out.save(R / 'ear-options-compare.png'); print('ok', R / 'ear-options-compare.png', out.size)
