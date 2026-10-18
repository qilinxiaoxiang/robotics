"""Generic render of one scene spec on the as-built model at HOME (feet flat), one scene per process (memory).
    python render_scene.py SPEC.json
SPEC: {"out": dir, "prefix": str, "meshes": [[path, rgba, tag]], "boxes": [[lo, hi, rgba]], "wires": [[[pts...], rgba, r]],
       "views": [[key, az, el, dist, [lookat mm]]], "hideInIso": [tags]}. Removes the power_support/np_f970 placeholders."""
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
spec = mujoco.MjSpec.from_file(str(ev.MODEL_DIR / 'scene.xml')); trunk = spec.body('trunk_base')
for g in list(spec.geoms):
    if g.name in ('power_support', 'np_f970'):
        spec.delete(g)
for i, (f, rgba, tag) in enumerate(S['meshes']):
    a = spec.add_mesh(name=f'm_{tag}', file=str(f), scale=[mm] * 3)
    trunk.add_geom(name=tag, type=mujoco.mjtGeom.mjGEOM_MESH, meshname=a.name, contype=0, conaffinity=0, mass=0, rgba=rgba, group=2)
for i, (lo, hi, rgba) in enumerate(S.get('boxes', [])):
    lo, hi = np.array(lo, float), np.array(hi, float)
    trunk.add_geom(name=f'box{i}', type=mujoco.mjtGeom.mjGEOM_BOX, pos=(lo + hi) / 2 * mm, size=(hi - lo) / 2 * mm, rgba=rgba, contype=0, conaffinity=0, mass=0, group=2)
for i, (pts, rgba, r) in enumerate(S.get('wires', [])):
    for k in range(len(pts) - 1):
        trunk.add_geom(name=f'w{i}_{k}', type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=np.r_[np.array(pts[k]) * mm, np.array(pts[k + 1]) * mm],
                       size=[r * mm, 0, 0], rgba=rgba, contype=0, conaffinity=0, mass=0, group=2)
m = spec.compile(); m.vis.global_.offwidth = 800; m.vis.global_.offheight = 800
d = mujoco.MjData(m)
Rt = feet_flat_rot(m, d, NAMES, HOME); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel())
setup(m, d, NAMES, HOME, q); z = np.vstack(sole_points(m, d))[:, 2].min(); d.qpos[2] -= z; mujoco.mj_forward(m, d)
tb = m.body('trunk_base').id
world = lambda p: d.xpos[tb] + d.xmat[tb].reshape(3, 3) @ (np.array(p, float) * mm)
r = mujoco.Renderer(m, height=600, width=600)
for key, az, el, dist, look in S['views']:
    cam = mujoco.MjvCamera(); cam.lookat = world(look); cam.distance = dist; cam.azimuth = az; cam.elevation = el
    r.update_scene(d, camera=cam); scn = r.scene
    if key == 'iso':
        for i in range(scn.ngeom):
            g = scn.geoms[i]
            if g.objtype == mujoco.mjtObj.mjOBJ_GEOM and m.geom(g.objid).name in S.get('hideInIso', []):
                g.rgba[3] = 0.0
    Image.fromarray(r.render()).save(OUT / f"{S['prefix']}-{key}.png")
print('ok', S['prefix'])
