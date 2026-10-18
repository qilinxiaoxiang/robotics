"""Colour-study render of the as-built MicroDuck at HOME (feet flat). Extends ../back-plate/layout-D-20261014/render_scene.py
with three spec keys; everything else (model, pose, camera, image size) is the same.
    python render_colour.py SPEC.json
SPEC: {"out", "prefix", "views": [[key, az, el, dist, [lookat mm, trunk frame]]],
       "meshes": [[stl, rgba, tag, body?]]   world-frame STLs (robot frame, mm). With a body name the mesh is attached to that
                                             body at its q0 pose, so head parts follow the neck and head joints to HOME.
       "recolor": {mjcf_mesh_name: rgba}     recolours every visual geom of the community MJCF that uses that mesh.
       "hideMeshes": [mjcf_mesh_name]}       community geoms to drop: the head shells replaced by the printed V1.8/V1.9
                                             head STLs, and the power_support/np_f970 placeholders (unnamed geoms, so
                                             render_scene.py's name filter does not remove them)."""
import sys, json
from pathlib import Path
import numpy as np, mujoco
from PIL import Image
REAL = Path('/Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014')
sys.path.insert(0, str(REAL))
from static_gap import NAMES, HOME, feet_flat_rot, setup, sole_points
import evaluate_delay as ev
S = json.loads(Path(sys.argv[1]).read_text()); OUT = Path(S['out']); OUT.mkdir(parents=True, exist_ok=True)
mm = 0.001
spec = mujoco.MjSpec.from_file(str(ev.MODEL_DIR / 'scene.xml'))
for g in list(spec.geoms):
    if g.name in ('power_support', 'np_f970'):
        spec.delete(g)
# body poses relative to trunk_base at q0 (the frame the world STLs were exported in)
m0 = spec.compile(); d0 = mujoco.MjData(m0); mujoco.mj_forward(m0, d0)
t0 = m0.body('trunk_base').id; Rt0 = d0.xmat[t0].reshape(3, 3); pt0 = d0.xpos[t0]
def rel(body):
    b = m0.body(body).id
    R = Rt0.T @ d0.xmat[b].reshape(3, 3); p = Rt0.T @ (d0.xpos[b] - pt0)
    return R, p
recolor, hide = S.get('recolor', {}), set(S.get('hideMeshes', []))
for g in list(spec.geoms):
    if g.type == mujoco.mjtGeom.mjGEOM_MESH and g.meshname:
        if g.meshname in hide:
            spec.delete(g); continue
        if g.meshname in recolor:
            g.material = ''; g.rgba = recolor[g.meshname]
for i, entry in enumerate(S['meshes']):
    f, rgba, tag = entry[:3]; body = entry[3] if len(entry) > 3 else 'trunk_base'
    a = spec.add_mesh(name=f'm_{tag}', file=str(f), scale=[mm] * 3)
    kw = {}
    if body != 'trunk_base':
        R, p = rel(body); q = np.zeros(4); mujoco.mju_mat2Quat(q, R.T.ravel())
        kw = {'pos': -R.T @ p, 'quat': q}
    spec.body(body).add_geom(name=tag, type=mujoco.mjtGeom.mjGEOM_MESH, meshname=a.name, contype=0, conaffinity=0, mass=0,
                             rgba=rgba, group=2, **kw)
m = spec.compile(); m.vis.global_.offwidth = 900; m.vis.global_.offheight = 900
d = mujoco.MjData(m)
Rt = feet_flat_rot(m, d, NAMES, HOME); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel())
setup(m, d, NAMES, HOME, q); z = np.vstack(sole_points(m, d))[:, 2].min(); d.qpos[2] -= z; mujoco.mj_forward(m, d)
tb = m.body('trunk_base').id
world = lambda p: d.xpos[tb] + d.xmat[tb].reshape(3, 3) @ (np.array(p, float) * mm)
r = mujoco.Renderer(m, height=S.get('size', 600), width=S.get('size', 600))
for key, az, el, dist, look in S['views']:
    cam = mujoco.MjvCamera(); cam.lookat = world(look); cam.distance = dist; cam.azimuth = az; cam.elevation = el
    r.update_scene(d, camera=cam)
    Image.fromarray(r.render()).save(OUT / f"{S['prefix']}-{key}.png")
print('ok', S['prefix'])
