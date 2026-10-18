"""3D views of the rear pack with the numpy z-buffer rasterizer (raster.py). Usage: render_views.py [assembled|rear|front|print|all]"""
import sys
import numpy as np, trimesh
from PIL import Image, ImageDraw
import pack_lib as P
from raster import render

OUT = P.OUT
body = P.load_stl(OUT / 'rear_pack-world.stl'); cover = P.load_stl(OUT / 'rear_pack_cover-world.stl')
openrb = P.openrb_mesh(); imu = P.imu_mesh()
dfr = trimesh.creation.box(bounds=np.array(P.DFR_BOX))
ORANGE, BLACK, GREEN, BLUE, GREY, DFRC, PURPLE = (242, 140, 40), (55, 55, 60), (46, 139, 87), (59, 111, 214), (150, 150, 150), (31, 119, 180), (138, 79, 191)


def decim(key, target=15000):
    m = P.solid_mesh(key)
    if len(m.faces) > target:
        import fast_simplification as fs
        v, f = fs.simplify(m.vertices.astype(np.float32), m.faces.astype(np.int32), target_count=target)
        return trimesh.Trimesh(v, f, process=False)
    return m


TORSO = ['motor10', 'motor5', 'torso_base', 'ring10_torso', 'ring5_torso', 'motor12', 'idler12', 'idler_cap12', 'yaw', 'right_yaw', 'hip', 'right_hip',
         'motor9', 'motor4', 'ring9', 'ring4', 'passive', 'right_passive']


def torso_layers():
    return [(decim(k), GREY) for k in TORSO]


def finish(img, text, path):
    d = ImageDraw.Draw(img); d.rectangle([0, 0, img.width, 16], fill=(255, 255, 255)); d.text((6, 3), text, fill=(0, 0, 0))
    img.save(path); print('wrote', path)


def assembled():
    layers = torso_layers() + [(body, ORANGE), (cover, BLACK), (openrb, GREEN), (imu, BLUE), (dfr, DFRC)]
    ghost = [(decim('shell_left', 12000), (120, 120, 120), 0.22), (decim('shell_right', 12000), (120, 120, 120), 0.22)]
    img, _ = render(layers, view_dir=(0.75, -0.5, -0.42), up=(0, 0, 1), px_per_mm=7.0, ghost=ghost)
    finish(img, 'rear-left 3/4 view, assembled on the torso: body orange, cover black, OpenRB green, BNO085 blue, DFR1202 box, J box purple; shells ghosted', OUT / 'render_assembled_rear34.png')


def rear():
    layers = torso_layers() + [(body, ORANGE), (openrb, GREEN), (imu, BLUE), (dfr, DFRC)]
    img, _ = render(layers, view_dir=(1.0, 0.0, -0.05), up=(0, 0, 1), px_per_mm=9.0, bounds=((-45, -60), (45, 45)))
    finish(img, 'rear view, cover off (shells off): OpenRB bay, DFR channel, J pocket, posts', OUT / 'render_rear_cover_off.png')
    layers = torso_layers() + [(body, ORANGE), (openrb, GREEN), (imu, BLUE)]
    img, _ = render(layers, view_dir=(1.0, 0.0, -0.05), up=(0, 0, 1), px_per_mm=9.0, bounds=((-45, -60), (45, 45)))
    finish(img, 'rear view, cover and DFR1202 off: screwdriver lanes to the four OpenRB screws', OUT / 'render_rear_cover_dfr_off.png')


def front():
    layers = torso_layers() + [(body, ORANGE), (cover, BLACK), (imu, BLUE)]
    img, _ = render(layers, view_dir=(-1.0, 0.15, -0.12), up=(0, 0, 1), px_per_mm=9.0, bounds=((-45, -60), (45, 45)))
    finish(img, 'front view (shells off): plate, screw tabs, IMU slot and shelf, BNO085 blue', OUT / 'render_front_plate_imu.png')
    layers = [(body, ORANGE), (imu, BLUE)]
    img, _ = render(layers, view_dir=(-0.8, 0.5, -0.33), up=(0, 0, 1), px_per_mm=9.0)
    finish(img, 'front-left 3/4 of the body alone with the BNO085 in its slot', OUT / 'render_front34_body_imu.png')


def print_pose():
    tiles = []
    for m, name, R in ((body, 'body standing on the bottom wall (z up)', np.eye(3)),
                       (cover, 'cover flat on its outer face', np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float))):
        v = m.vertices @ R.T; mm = trimesh.Trimesh(v, m.faces, process=False)
        n = mm.face_normals; bed = mm.bounds[0][2]
        on_bed = (np.abs(n[:, 2] + 1) < 1e-3) & (mm.triangles[:, :, 2].max(1) < bed + 0.02)
        over = (n[:, 2] < -0.7072) & ~on_bed
        red = mm.submesh([np.flatnonzero(over)], append=True) if over.any() else None
        rest = mm.submesh([np.flatnonzero(~over)], append=True)
        for vd, lab in (((0.6, 0.6, 0.55), 'from below'), ((-0.6, -0.6, -0.55), 'from above')):
            layers = [(rest, (200, 200, 200))] + ([(red, (220, 30, 30))] if red is not None else [])
            img, _ = render(layers, view_dir=vd, up=(0, 0, 1), px_per_mm=6.0, light=(0.3, -0.4, 0.85) if lab == 'from above' else (0.3, 0.4, -0.85))
            finish(img, f'{name}: {lab}; red = overhang faces steeper than 45 deg ({mm.area_faces[over].sum():.1f} mm2)', OUT / f'render_print_{name.split()[0]}_{lab.replace(" ", "_")}.png')
            tiles.append(img)
    W = sum(t.width for t in tiles); H = max(t.height for t in tiles)
    sheet = Image.new('RGB', (W, H), (255, 255, 255)); x = 0
    for t in tiles:
        sheet.paste(t, (x, 0)); x += t.width
    sheet.save(OUT / 'render_print_poses.png'); print('wrote', OUT / 'render_print_poses.png')


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if mode in ('assembled', 'all'):
        assembled()
    if mode in ('rear', 'all'):
        rear()
    if mode in ('front', 'all'):
        front()
    if mode in ('print', 'all'):
        print_pose()
