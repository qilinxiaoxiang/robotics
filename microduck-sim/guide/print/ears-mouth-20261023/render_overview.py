"""D-025 overview picture: the two ears in the cap, the speaker box behind the camera with its duct to the six ports, and the
new wires. Four tiles: inside from the rear left (cap and face hidden), the left ear from inside, the mouth from below
(the six ports over the lower jaw), and the outside left side. argv: out.png

    /tmp/microduck-cad-venv/bin/python render_overview.py ears-mouth.png
"""
import json
import sys
import tempfile
from pathlib import Path

import mujoco
import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
GUIDE = HERE.parents[1]
sys.path.insert(0, str(GUIDE / 'content' / 'interference-audit'))
import ia_lib  # noqa: E402

CACHE = {k: ia_lib.load_solid(k) for k in ('jaw_support', 'jaw_frame', 'motor13', 'motor14', 'motor15', 'mouth_sliding_ring', 'camera_u20cam',
                                           'camera_cable_stub', 'face_panel', 'eye_trim', 'amplifier', 'touch_xiao', 'head_yaw_link',
                                           'head_roll_ring_a', 'head_roll_ring_b', 'exit_clamp_loose')}
F = {'head_cap': HERE / 'head-cap/head_cap_ears-world.stl', 'head_bottom': HERE / 'yellow-reprint/head_bottom_ports-world.stl',
     'speaker_box': HERE / 'speaker-box/speaker_box-world.stl', 'speaker': HERE / 'speaker-box/speaker_mouth-world.stl',
     'tape_rim': HERE / 'speaker-box/speaker_tape_rim-world.stl', 'tape_box': HERE / 'speaker-box/speaker_box_tape-world.stl',
     'mic_left': HERE / 'head-cap/mic_left-world.stl', 'mic_right': HERE / 'head-cap/mic_right-world.stl'}
COL = {'head_cap': (.95, .95, .95, .25), 'head_bottom': (.93, .78, .25, 1), 'speaker_box': (.97, .97, .97, 1), 'speaker': (.45, .3, .2, 1),
       'tape_rim': (1, .9, .1, 1), 'tape_box': (1, .9, .1, 1), 'mic_left': (.1, .6, .2, 1), 'mic_right': (.1, .6, .2, 1),
       'jaw_support': (.25, .25, .25, 1), 'jaw_frame': (.93, .6, .2, 1), 'motor13': (.15, .15, .15, 1), 'motor14': (.15, .15, .15, 1),
       'motor15': (.15, .15, .15, 1), 'mouth_sliding_ring': (.25, .25, .25, 1), 'camera_u20cam': (.2, .4, .75, 1),
       'camera_cable_stub': (0, .5, .55, 1), 'face_panel': (.98, .98, .98, 1), 'eye_trim': (.1, .1, .1, 1), 'amplifier': (.1, .35, .6, 1),
       'touch_xiao': (.2, .2, .5, 1), 'head_yaw_link': (.3, .3, .3, 1), 'head_roll_ring_a': (.3, .3, .3, 1), 'head_roll_ring_b': (.3, .3, .3, 1),
       'exit_clamp_loose': (.1, .1, .1, 1)}
ROUTES = json.loads((HERE / 'routes/routes_ears_mouth.json').read_text())['routes']
RCOL = {'mic_r_harness': (.85, .1, .1, 1), 'mic_l_harness': (.85, .1, .1, 1), 'mic_sd_pin38': (.55, .15, .65, 1), 'mic_gnd_pin34': (.55, .15, .65, 1),
        'spk_plus': (.8, .2, .2, 1), 'spk_minus': (.1, .1, .1, 1)}
tmp = Path(tempfile.mkdtemp())


def scene(hide=()):
    spec = mujoco.MjSpec(); wb = spec.worldbody
    spec.visual.global_.offwidth = 1000; spec.visual.global_.offheight = 1000
    spec.visual.headlight.ambient = [.5, .5, .5]; spec.visual.headlight.diffuse = [.55, .55, .55]
    items = {**{k: trimesh.Trimesh(*CACHE[k], process=False) for k in CACHE}, **{k: trimesh.load(p, force='mesh') for k, p in F.items()}}
    for k, m in items.items():
        if k in hide:
            continue
        m = m.copy(); m.vertices = m.vertices * 1e-3; f = tmp / f'{k}.stl'; m.export(f)
        spec.add_mesh(name=f'm_{k}', file=str(f))
        wb.add_geom(name=k, type=mujoco.mjtGeom.mjGEOM_MESH, meshname=f'm_{k}', rgba=COL[k], contype=0, conaffinity=0)
    for k, pts in ROUTES.items():
        p = np.array(pts) * 1e-3
        for i, (a, b) in enumerate(zip(p[:-1], p[1:])):
            if a[2] < 0.095 and b[2] < 0.095:
                continue
            wb.add_geom(name=f'{k}_{i}', type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=np.r_[a, b], size=[0.0009, 0, 0], rgba=RCOL[k],
                        contype=0, conaffinity=0)
    mdl = spec.compile(); d = mujoco.MjData(mdl); mujoco.mj_forward(mdl, d)
    return mdl, d


def shot(hide, lookat, dist, az, el):
    mdl, d = scene(hide)
    R = mujoco.Renderer(mdl, height=620, width=620)
    cam = mujoco.MjvCamera(); cam.lookat = np.array(lookat) * 1e-3; cam.distance = dist; cam.azimuth = az; cam.elevation = el
    R.update_scene(d, camera=cam); return R.render()


def section():
    import matplotlib
    matplotlib.use('Agg'); import matplotlib.pyplot as plt
    items = {**{k: trimesh.Trimesh(*CACHE[k], process=False) for k in ('jaw_frame', 'jaw_support', 'camera_u20cam', 'face_panel', 'eye_trim')},
             **{k: trimesh.load(F[k], force='mesh') for k in ('head_bottom', 'head_cap', 'speaker_box', 'speaker', 'tape_rim', 'tape_box')}}
    fig, ax = plt.subplots(figsize=(6.2, 6.2), dpi=100)
    for k, m in items.items():
        sct = m.section(plane_origin=[0, -3.0, 0], plane_normal=[0, 1, 0])
        if sct is None:
            continue
        c = COL[k]
        for e in sct.discrete:
            e = np.asarray(e)
            ax.fill(e[:, 0], e[:, 2], fc=c[:3], ec='k', lw=.4, alpha=.9 if k != 'head_cap' else .5)
    for t, xy in (('speaker', (54.8, 128)), ('chamber', (59.6, 136)), ('duct', (66, 112.4)), ('ports', (68, 106.5)), ('camera', (70, 122)),
                  ('lower jaw', (64, 102)), ('jaw support', (36, 118))):
        ax.annotate(t, xy, fontsize=8, ha='center')
    ax.set_xlim(30, 92); ax.set_ylim(96, 158); ax.set_aspect('equal'); ax.grid(alpha=.25)
    ax.set_xlabel('x (forward), mm'); ax.set_ylabel('z, mm')
    fig.tight_layout(); f = tmp / 'section.png'; fig.savefig(f); plt.close(fig)
    return np.array(Image.open(f).convert('RGB').resize((620, 620)))


tiles = [
    (shot({'head_cap', 'face_panel', 'eye_trim', 'camera_u20cam'}, [40, 0, 126], 0.19, 30, -30), 'inside, from the rear and above (cap, face, camera hidden)'),
    (shot({'face_panel', 'eye_trim'}, [58, 30, 133], 0.075, -95, -12), 'left ear from inside the head'),
    (shot({'jaw_frame'}, [66, -3, 110], 0.09, 180, 70), 'from below, jaw hidden: six ports, duct above'),
    (section(), 'section at y -3: speaker, chamber, duct, ports'),
]
img = Image.fromarray(np.vstack([np.hstack([tiles[0][0], tiles[1][0]]), np.hstack([tiles[2][0], tiles[3][0]])]))
dr = ImageDraw.Draw(img); font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 18)
for i, (_, t) in enumerate(tiles):
    x, y = 620 * (i % 2), 620 * (i // 2)
    dr.rectangle((x, y, x + 620, y + 26), fill=(0, 0, 0)); dr.text((x + 8, y + 4), t, fill=(255, 255, 255), font=font)
img.save(sys.argv[1]); print('ok', sys.argv[1], img.size)
