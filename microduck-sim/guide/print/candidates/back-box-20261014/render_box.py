"""Effect renders of two rear converter-box candidates on the as-built MicroDuck model (HOME pose, feet flat).

Boxes are drawn as visual-only scene geoms in the trunk_base frame (pack coordinates: x forward, z up, mm).
A: deep stack behind the pack cover, 40 mm back.   B: wide one-layer plate, 20 mm back.
Board sizes: XL4015 module 54 x 23 x 16 mm (common module; kit unit not measured), Adafruit 5991 33 x 23 x 8 mm.
"""
import sys, math
from pathlib import Path
import numpy as np, mujoco, imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont
REAL = Path('/Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014')
sys.path.insert(0, str(REAL))
from static_gap import cfg, NAMES, HOME, feet_flat_rot, setup, sole_points
import evaluate_delay as ev
OUT = Path(__file__).resolve().parent

m, d, c, names, bam = ev.load(cfg(0.09))
tb = m.body('trunk_base').id
Rt = feet_flat_rot(m, d, names, HOME); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel())
setup(m, d, names, HOME, q); z = np.vstack(sole_points(m, d))[:, 2].min(); d.qpos[2] -= z; mujoco.mj_forward(m, d)

# (lo, hi) mm in trunk frame, rgba
XL = (54, 23, 16); PD = (33, 23, 8)
def box(lo, hi, rgba): return (np.array(lo, float), np.array(hi, float), rgba)
SHELL = (1, 1, 1, 0.35); BLUE = (0.1, 0.3, 0.9, 1); BLK = (0.1, 0.1, 0.1, 1)
A = [box((-89, -18.6, -44), (-47, 18.6, 29.5), SHELL),                       # 40 mm deep box, cover footprint
     box((-67, -11.5, -40), (-51, 11.5, 14), BLUE),                           # XL4015 #1 standing, 54 tall (z), 23 wide
     box((-85, -11.5, -40), (-69, 11.5, 14), BLUE),                           # XL4015 #2 behind it
     box((-59, -11.5, 17), (-51, 11.5, 50 - 23 + 0), BLK)]                    # 5991 above, 33 wide? -> placed 8 deep
A[3] = box((-59, -16.5, 16), (-51, 16.5, 27), BLK)
B = [box((-69, -28, -8), (-47, 28, 41), SHELL),                               # 20 mm deep plate, 56 wide, 49 tall
     box((-65, -27, -6), (-49, 27, 17), BLUE),                                # XL4015 #1 lying, 54 along y, 23 tall
     box((-65, -27, 18), (-49, 27, 41), BLUE),                                # XL4015 #2 above it
     box((-45, -11.5, -40), (-37, 11.5, -7), BLK)]                            # 5991 in the empty DFR1202 channel
B2 = [box((-69, -28, -32), (-47, 28, 41), SHELL),                             # B with the 5991 also in the plate
      box((-65, -27, -6), (-49, 27, 17), BLUE), box((-65, -27, 18), (-49, 27, 41), BLUE),
      box((-57, -16.5, -31), (-49, 16.5, -8), BLK)]

def add_boxes(scn, boxes):
    R = d.xmat[tb].reshape(3, 3); p = d.xpos[tb]
    for lo, hi, rgba in boxes:
        cen = (lo + hi) / 2 / 1000; half = (hi - lo) / 2 / 1000
        pos = p + R @ cen
        g = scn.geoms[scn.ngeom]
        mujoco.mjv_initGeom(g, mujoco.mjtGeom.mjGEOM_BOX, half, pos, R.ravel(), np.array(rgba, np.float32))
        scn.ngeom += 1

r = mujoco.Renderer(m, height=560, width=420)
def shot(boxes, az, el=0, dist=0.5):
    cam = mujoco.MjvCamera(); cam.lookat = d.subtree_com[0].copy(); cam.lookat[2] = 0.085
    cam.distance = dist; cam.azimuth = az; cam.elevation = el
    r.update_scene(d, camera=cam); add_boxes(r.scene, boxes); return r.render()

variants = [('current', []), ('A deep 40 mm', A), ('B wide 20 mm', B), ('B2 wide 20 mm + 5991', B2)]
views = [('side', 90, 0), ('rear 3/4', 35, -12), ('rear', 0, 0)]
tiles = []
for label, bx in variants:
    row = [shot(bx, az, el) for _, az, el in views]
    img = Image.fromarray(np.hstack(row)); dr = ImageDraw.Draw(img)
    try: font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 26)
    except Exception: font = ImageFont.load_default()
    dr.rectangle((0, 0, 330, 40), fill=(0, 0, 0)); dr.text((8, 6), label, fill=(255, 255, 255), font=font)
    for i, (vn, _, _) in enumerate(views):
        dr.text((i * 420 + 8, 520), vn, fill=(255, 255, 255), font=font)
    tiles.append(np.array(img))
imageio.imwrite(OUT / 'back-box-candidates.png', np.vstack(tiles))
print('ok', OUT / 'back-box-candidates.png')
