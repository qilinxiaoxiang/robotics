"""Renders of the two-piece converter-box layouts on the as-built model at HOME (feet flat), like back-box-candidates.png:
three views per layout (rear, +y side, rear-top isometric) with the shells, the V1.8 pack, the OpenRB and the legs.
Frame dark grey, lid translucent, XL4015 blue (ROBOTIS mesh), 5991 black, wire stubs: red 15 V IN, orange 7 V, yellow 5 V,
grey USB-C plug. Reads <layout>/*.stl and numbers.json from options.py; writes layout-<name>.png.
Run with ~/.venvs/microduck-dyn/bin/python (mujoco + the dynamics helpers) under the bounded runner."""
import sys, json
from pathlib import Path
import numpy as np, mujoco
from PIL import Image, ImageDraw, ImageFont
HERE = Path(__file__).resolve().parent
REAL = Path('/Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014')
WORLD = HERE.parent.parent / 'world'
sys.path.insert(0, str(REAL))
from static_gap import NAMES, HOME, feet_flat_rot, setup, sole_points
import evaluate_delay as ev
mm = 0.001
NUM = json.loads((HERE / 'numbers.json').read_text())
COL = dict(frame=(.17, .17, .19, .9), lid=(.6, .6, .65, .28), xl=(.12, .3, .9, 1), pd=(.05, .05, .05, 1), red=(.9, .1, .1, 1), orange=(1, .55, .05, 1),
           yellow=(.95, .85, .1, 1), grey=(.6, .6, .6, 1))
STUBS = {
 'A': [('orange', [(-55, 11.0, -20.0), (-38, 11.0, -20.0)], 1.0), ('yellow', [(-55, 11.0, -26.0), (-38, 11.0, -26.0)], 1.1),
       ('grey', [(-52.25, -3.0, -42.0), (-52.25, -3.0, -62.0)], 3.0)],
 'B': [('red', [(-56.5, 0, -38.0), (-56.5, 0, -58.0)], 1.0), ('orange', [(-54.7, 11.6, 36.0), (-54.7, 11.6, 52.0)], 1.0),
       ('yellow', [(-54.7, -11.35, 36.0), (-54.7, -11.35, 52.0)], 1.1)],
 'B_flip': [('red', [(-56.5, 0, 36.0), (-56.5, 0, 56.0)], 1.0), ('orange', [(-55, 8.0, -37.0), (-38, 8.0, -37.0)], 1.0),
            ('yellow', [(-55, -8.0, -37.0), (-38, -8.0, -37.0)], 1.1)],
}


def render(name):
    spec = mujoco.MjSpec.from_file(str(ev.MODEL_DIR / 'scene.xml'))
    trunk = spec.body('trunk_base')
    for g in list(spec.geoms):
        if g.name in ('power_support', 'np_f970'):
            spec.delete(g)
    def add(fname, rgba, tag):
        a = spec.add_mesh(name=f'm_{tag}', file=str(fname), scale=[mm] * 3)
        trunk.add_geom(name=f'g_{tag}', type=mujoco.mjtGeom.mjGEOM_MESH, meshname=a.name, contype=0, conaffinity=0, mass=0, rgba=rgba, group=2)
    add(WORLD / 'rear_pack-v18.stl', (.93, .5, .1, 1), 'pack'); add(WORLD / 'openrb-board-upright.stl', (.15, .35, .2, 1), 'orb')
    d = HERE / name
    add(d / 'frame-world.stl', COL['frame'], 'frame'); add(d / 'lid-world.stl', COL['lid'], 'lid')
    for f in sorted((d / 'render').glob('xl4015_*.stl')):   # decimated copies written by options.py
        add(f, COL['xl'], f.stem)
    if (d / 'pd5991-world.stl').exists():
        add(d / 'pd5991-world.stl', COL['pd'], 'pd')
    for i, (c, pts, r) in enumerate(STUBS[name]):
        for k in range(len(pts) - 1):
            trunk.add_geom(name=f'w{i}_{k}', type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=np.r_[np.array(pts[k]) * mm, np.array(pts[k + 1]) * mm],
                           size=[r * mm, 0, 0], rgba=COL[c], contype=0, conaffinity=0, mass=0, group=2)
    m = spec.compile(); m.vis.global_.offwidth = 1800; m.vis.global_.offheight = 700
    dd = mujoco.MjData(m)
    Rt = feet_flat_rot(m, dd, NAMES, HOME); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel())
    setup(m, dd, NAMES, HOME, q); z = np.vstack(sole_points(m, dd))[:, 2].min(); dd.qpos[2] -= z; mujoco.mj_forward(m, dd)
    tb = m.body('trunk_base').id
    world = lambda p: dd.xpos[tb] + dd.xmat[tb].reshape(3, 3) @ (np.array(p, float) * mm)
    yaw = np.degrees(np.arctan2(dd.xmat[tb].reshape(3, 3)[1, 0], dd.xmat[tb].reshape(3, 3)[0, 0]))
    r = mujoco.Renderer(m, height=600, width=600)
    def shot(az, el, dist, look):
        cam = mujoco.MjvCamera(); cam.lookat = world(look); cam.distance = dist; cam.azimuth = az + yaw; cam.elevation = el
        r.update_scene(dd, camera=cam); return r.render()
    views = [('rear', 0, 0, 0.30, (-50, 0, -5)), ('+y side', -90, 0, 0.36, (-35, 0, -15)), ('rear-top isometric', -40, -32, 0.36, (-45, 0, 0))]
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 20)
    except Exception:
        font = ImageFont.load_default()
    tiles = []
    for label, az, el, dist, look in views:
        img = Image.fromarray(shot(az, el, dist, look)); dr = ImageDraw.Draw(img)
        dr.rectangle((0, 0, 600, 30), fill=(0, 0, 0)); dr.text((8, 5), label, fill=(255, 255, 255), font=font); tiles.append(np.array(img))
    img = Image.fromarray(np.hstack(tiles)); n = NUM[name]
    W, H = img.size; legend_lines = legend(name, n)
    canvas = Image.new('RGB', (W, H + 34 + 24 * len(legend_lines) + 10), (0, 0, 0)); canvas.paste(img, (0, 34))
    dr = ImageDraw.Draw(canvas); dr.text((8, 6), n['title'], fill=(255, 255, 255), font=font)
    for i, t in enumerate(legend_lines):
        dr.text((8, H + 40 + 24 * i), t, fill=(230, 230, 230), font=font)
    out = HERE / f'layout-{name}.png'; canvas.save(out); print('wrote', out, 'trunk yaw deg', round(float(yaw), 2), flush=True)


def legend(name, n):
    ms = n['mass']
    L = [f"outer x {n['outer']['x'][0]}..-45, |y| <= {n['outer']['absY']}, z {n['outer']['z'][0]}..{n['outer']['z'][1]}; inner depth 18.9; printed {ms['printedG']} g; robot +{ms['netAddedG']} g -> {ms['totalRobotG']} g; COM shift {ms['comShiftMm']} mm",
         f"proud of the shells per side: left {n['shellOverhangPerSideMm']['shell_left']} / right {n['shellOverhangPerSideMm']['shell_right']} mm; free z above / below boards {n['freeZ']['aboveBoards']} / {n['freeZ']['belowBoards']}; free |y| past board ends {n['freeAbsYBeyondBoardEnds']}",
         'cover screws behind boards: ' + ', '.join(k for k, v in n['coverScrewsDia5Lanes'].items() if v['coveredByBoards']) + ' -> frame first, then boards, then lid']
    if name == 'A':
        p = n['pd5991']; L.append(f"5991: 1.24 mm under the lower XL4015; terminal wire room above it {p['terminalWireRoomAboveMm']} mm; USB-C opening x -56.25..-48.25, y -10..4")
    L.append('blue XL4015 (ROBOTIS mesh) | black 5991 | red 15 V IN | orange 7 V | yellow 5 V | grey USB-C plug | translucent lid')
    return L


if __name__ == '__main__':
    for nm in (sys.argv[1:] or ['A', 'B', 'B_flip']):
        render(nm)
