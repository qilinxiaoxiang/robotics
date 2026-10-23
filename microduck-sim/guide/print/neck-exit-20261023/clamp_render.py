"""Clamp picture: left two tiles plan sections (z 114.5 below the lips, z 119 through tongues and lips), right two 3D views. argv: out.png"""
import sys, tempfile, numpy as np, trimesh, mujoco
from pathlib import Path
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MP
from PIL import Image
E = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/neck-exit-20261023')
C = '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/ia-cache'
JS = trimesh.load(E / 'jaw_support_exit.stl'); LA = trimesh.load(E / 'exit_clamp_loose_A.stl'); HB = trimesh.load(E / 'head_bottom_exit.stl')
z = np.load(f'{C}/solid-motor15.npz'); M15 = trimesh.Trimesh(z['v'], z['f'], process=False)
fig, axs = plt.subplots(1, 2, figsize=(12, 6))
for ax, zc in zip(axs, (114.5, 119.0)):
    for m, col, lab in ((HB, '#e6b800', 'lower head shell'), (M15, '#37474f', 'jaw servo ID15'), (JS, '#9e9e9e', 'jaw support with the fixed half'), (LA, '#1e88e5', 'loose half A')):
        s = m.section(plane_origin=[0, 0, zc], plane_normal=[0, 0, 1])
        if s is None: continue
        p, _ = s.to_2D(to_2D=np.eye(4))
        for poly in p.polygons_full:
            v, c = [], []
            for ring in [poly.exterior] + list(poly.interiors):
                q = np.asarray(ring.coords); v += q.tolist(); c += [MP.MOVETO] + [MP.LINETO] * (len(q) - 2) + [MP.CLOSEPOLY]
            ax.add_patch(PathPatch(MP(v, c), fc=col, ec='k', lw=.4, alpha=.85, label=lab))
    ax.add_patch(plt.Circle((10, 18.5), 3.4, fill=False, ec='#2e7d32', ls='--', lw=1.2, label='bundle space (rib tips dia 6.8)'))
    ax.set_xlim(1, 19); ax.set_ylim(9.5, 27.5); ax.set_aspect('equal'); ax.grid(alpha=.25)
    ax.set_title(f'top view, cut at z {zc}' + (' (below the lips)' if zc < 116 else ' (tongues behind the lips)') + '\nfront to the right, robot left up', fontsize=10)
h, l = axs[1].get_legend_handles_labels(); u = dict(zip(l, h)); fig.legend(u.values(), u.keys(), loc='lower center', ncol=5, fontsize=9)
plt.tight_layout(rect=(0, .07, 1, .95)); tmp = Path(tempfile.mkdtemp()); fig.savefig(tmp / 'plan.png', dpi=90); plt.close(fig)
# 3D: crop the jaw support round the exit
box = trimesh.creation.box(extents=[24, 24, 20]); box.apply_translation([10, 18.5, 120])
jsc = trimesh.boolean.intersection([JS, box], engine='manifold')
spec = mujoco.MjSpec(); wb = spec.worldbody
spec.visual.global_.offwidth = 900; spec.visual.global_.offheight = 900
spec.visual.headlight.ambient = [.45, .45, .45]; spec.visual.headlight.diffuse = [.6, .6, .6]
for name, m, rgba, off in (('js', jsc, (.55, .55, .55, 1), [0, 0, 0]), ('la', LA, (.12, .53, .9, 1), [0, 0, 0]), ('la_up', LA, (.12, .53, .9, 1), [0, 0, 0])):
    f = tmp / f'{name}.stl'; mm = m.copy()
    if name == 'la_up': continue
    mm.vertices = mm.vertices * 0.001; mm.export(f)
    spec.add_mesh(name=f'm_{name}', file=str(f)); wb.add_geom(name=name, type=mujoco.mjtGeom.mjGEOM_MESH, meshname=f'm_{name}', rgba=rgba, contype=0, conaffinity=0)
mdl = spec.compile(); d = mujoco.MjData(mdl); mujoco.mj_forward(mdl, d); R = mujoco.Renderer(mdl, height=540, width=540)
tiles = []
for az, el, lab in ((-30, -35, 'seated, from the front right'), (150, -40, 'from the rear left')):
    cam = mujoco.MjvCamera(); cam.lookat = np.array([10, 18.5, 119]) * 0.001; cam.distance = 0.06; cam.azimuth = az; cam.elevation = el
    R.update_scene(d, camera=cam); tiles.append(R.render())
# exploded: loose half lifted 9 mm
mdl2spec = mujoco.MjSpec(); wb2 = mdl2spec.worldbody
mdl2spec.visual.global_.offwidth = 900; mdl2spec.visual.global_.offheight = 900
mdl2spec.visual.headlight.ambient = [.45, .45, .45]; mdl2spec.visual.headlight.diffuse = [.6, .6, .6]
mdl2spec.add_mesh(name='m_js', file=str(tmp / 'js.stl')); wb2.add_geom(name='js', type=mujoco.mjtGeom.mjGEOM_MESH, meshname='m_js', rgba=(.55, .55, .55, 1), contype=0, conaffinity=0)
mdl2spec.add_mesh(name='m_la', file=str(tmp / 'la.stl')); wb2.add_geom(name='la', type=mujoco.mjtGeom.mjGEOM_MESH, meshname='m_la', pos=[0, 0, 0.009], rgba=(.12, .53, .9, 1), contype=0, conaffinity=0)
m2 = mdl2spec.compile(); d2 = mujoco.MjData(m2); mujoco.mj_forward(m2, d2); R2 = mujoco.Renderer(m2, height=540, width=540)
cam = mujoco.MjvCamera(); cam.lookat = np.array([10, 18.5, 123]) * 0.001; cam.distance = 0.065; cam.azimuth = -30; cam.elevation = -30
R2.update_scene(d2, camera=cam); tiles.append(R2.render())
plan = np.array(Image.open(tmp / 'plan.png').convert('RGB'))
H = 540; plan = np.array(Image.fromarray(plan).resize((int(plan.shape[1] * H / plan.shape[0]), H)))
img = Image.fromarray(np.hstack([plan] + tiles))
from PIL import ImageDraw, ImageFont
dr = ImageDraw.Draw(img); font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 17)
x0 = plan.shape[1]
for i, t in enumerate(('seated, from the front right', 'from the rear left (fixed half)', 'loose half lifted 9 mm: slides down')):
    dr.rectangle((x0 + 540 * i, 0, x0 + 540 * (i + 1), 24), fill=(0, 0, 0)); dr.text((x0 + 540 * i + 8, 3), t, fill=(255, 255, 255), font=font)
img.save(sys.argv[1]); print('ok', sys.argv[1], img.size)
