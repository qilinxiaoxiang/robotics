"""Reference renders of the as-built model at HOME and STAND, feet flat, for comparison with side/front photos."""
import sys, math
from pathlib import Path
import numpy as np, mujoco, imageio.v2 as imageio
sys.path.insert(0, str(Path(__file__).resolve().parent))
from static_gap import cfg, NAMES, HOME, STAND, feet_flat_rot, setup, sole_points
import evaluate_delay as ev
m, d, c, names, bam = ev.load(cfg(0.09))
r = mujoco.Renderer(m, height=640, width=480)
tiles = []
for pose in (HOME, STAND):
    Rt = feet_flat_rot(m, d, names, pose); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel())
    setup(m, d, names, pose, q); z = np.vstack(sole_points(m, d))[:, 2].min(); d.qpos[2] -= z; mujoco.mj_forward(m, d)
    row = []
    for az in (90, 180):  # left side, front
        cam = mujoco.MjvCamera(); cam.lookat = d.subtree_com[0].copy(); cam.lookat[2] = 0.09
        cam.distance = 0.55; cam.azimuth = az; cam.elevation = 0
        r.update_scene(d, camera=cam); row.append(r.render())
    tiles.append(np.hstack(row))
imageio.imwrite('reference-home-stand.png', np.vstack(tiles))
print('ok')
