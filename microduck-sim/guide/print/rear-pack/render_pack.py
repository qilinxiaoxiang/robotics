"""Renders of the rear pack (matplotlib only). Usage: render_pack.py [assembled|sections|rear|front|print|all]"""
import sys
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from shapely.geometry import box as sbox
from shapely.geometry.polygon import orient
import pack_lib as P

OUT = P.OUT
body = trimesh.load(str(OUT / 'rear_pack-world.stl'), force='mesh', process=False)
cover = trimesh.load(str(OUT / 'rear_pack_cover-world.stl'), force='mesh', process=False)
openrb = P.openrb_mesh(); imu = P.imu_mesh()
dfr = trimesh.creation.box(bounds=np.array(P.DFR_BOX))
ORANGE, BLACK, GREEN, BLUE, GREY, RED, PURPLE = '#f28c28', '#2b2b2b', '#2e8b57', '#3b6fd6', '#9a9a9a', '#d33', '#8a4fbf'


def decim(key, target=12000):
    m = P.solid_mesh(key)
    if len(m.faces) > target:
        import fast_simplification as fs
        v, f = fs.simplify(m.vertices.astype(np.float32), m.faces.astype(np.int32), target_count=target)
        return trimesh.Trimesh(v, f, process=False)
    return m


def add_mesh(ax, m, color, alpha=1.0, light=np.array([-0.5, 0.6, 0.8]), edge=False):
    tri = m.vertices[m.faces]
    n = m.face_normals
    l = light / np.linalg.norm(light)
    sh = 0.45 + 0.55 * np.clip(n @ l, 0, 1)
    rgb = np.array(matplotlib.colors.to_rgb(color))
    cols = np.clip(rgb[None, :] * sh[:, None], 0, 1)
    pc = Poly3DCollection(tri, facecolors=np.c_[cols, np.full(len(cols), alpha)], edgecolors='k' if edge else 'none', linewidths=0.1)
    ax.add_collection3d(pc)


def setup3d(ax, lo, hi, elev, azim):
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(hi - lo); ax.view_init(elev=elev, azim=azim)
    ax.set_xlabel('x fwd'); ax.set_ylabel('y left'); ax.set_zlabel('z up')


def assembled(path, show_cover=True, elev=22, azim=145, shells=True, title='rear pack assembled (rear-left 3/4), shells ghosted'):
    fig = plt.figure(figsize=(11, 9)); ax = fig.add_subplot(111, projection='3d')
    for k in ('motor10', 'motor5', 'torso_base', 'ring10_torso', 'ring5_torso', 'motor12', 'idler12', 'yaw', 'right_yaw', 'hip', 'right_hip'):
        add_mesh(ax, decim(k), GREY, 0.9)
    add_mesh(ax, body, ORANGE)
    if show_cover:
        add_mesh(ax, cover, BLACK)
    add_mesh(ax, openrb, GREEN); add_mesh(ax, imu, BLUE); add_mesh(ax, dfr, '#1f77b4', 0.6)
    if shells:
        for k in ('shell_left', 'shell_right'):
            add_mesh(ax, decim(k, 8000), '#bbbbbb', 0.12)
    setup3d(ax, np.array([-70, -45, -60]), np.array([40, 45, 50]), elev, azim); ax.set_title(title)
    fig.savefig(path, dpi=110); plt.close(fig)


def section_patches(ax, mesh, origin, normal, axes, color, alpha=0.95, hatch=None):
    sec = mesh.section(plane_origin=origin, plane_normal=normal)
    if sec is None:
        return
    p2, T = sec.to_planar()
    for poly in p2.polygons_full:
        poly = orient(poly, 1.0)
        verts = []; codes = []
        for ring in [poly.exterior] + list(poly.interiors):
            pts = np.array(ring.coords); h = np.c_[pts, np.zeros(len(pts)), np.ones(len(pts))] @ T.T
            pp = h[:, axes]
            verts += pp.tolist(); codes += [MPath.MOVETO] + [MPath.LINETO] * (len(pp) - 2) + [MPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor='k', lw=0.4, alpha=alpha, hatch=hatch))


def rect(ax, lo, hi, axes, **kw):
    a, b = axes
    ax.add_patch(plt.Rectangle((lo[a], lo[b]), hi[a] - lo[a], hi[b] - lo[b], **kw))


def sections(path):
    fig, axs = plt.subplots(1, 3, figsize=(20, 9))
    # y = 0 (x-z), y = +18 (x-z), x = -20 (y-z plate silhouette)
    specs = [((0, 0, 0), (0, 1, 0), (0, 2), 'section y = 0  (x right = forward, z up)'),
             ((0, 18, 0), (0, 1, 0), (0, 2), 'section y = +18  (through J pocket and neck window side)'),
             ((-20, 0, 0), (1, 0, 0), (1, 2), 'section x = -20  (plate silhouette, y left, z up)')]
    for ax, (o, n, axes, title) in zip(axs, specs):
        for k, col in (('motor10', GREY), ('motor5', GREY), ('torso_base', GREY), ('shell_left', '#dddddd'), ('shell_right', '#dddddd'),
                       ('motor12', GREY), ('ring10_torso', GREY), ('ring5_torso', GREY)):
            section_patches(ax, P.solid_mesh(k), o, n, axes, col, 0.6)
        section_patches(ax, body, o, n, axes, ORANGE); section_patches(ax, cover, o, n, axes, BLACK)
        section_patches(ax, openrb, o, n, axes, GREEN); section_patches(ax, imu, o, n, axes, BLUE)
        for (lo, hi), col, lab in ((P.DFR_BOX, '#1f77b4', 'DFR'), (P.DFR_PAD_ROOM, '#1f77b4', 'pad room'),
                                   (P.ROOM_LEG_PLUGS, RED, 'leg plugs'), (P.ROOM_NECK_PLUG, RED, 'neck plug'), (P.ROOM_TERMINAL, RED, 'terminal'),
                                   (P.ROOM_USB, RED, 'USB'), (P.ROOM_IMU_PLUG_TOP, RED, 'IMU plug')):
            k = 1 if axes == (0, 2) else 0
            if lo[k] - 1e-6 <= o[k] <= hi[k] + 1e-6 or axes == (1, 2) and lo[0] <= o[0] <= hi[0]:
                rect(ax, lo, hi, axes, fill=False, ls='--', ec=col, lw=1.0)
                ax.text(lo[axes[0]], hi[axes[1]], lab, fontsize=7, color=col, va='bottom')
        ax.set_aspect('equal'); ax.set_title(title, fontsize=10); ax.grid(alpha=0.3)
        if axes == (0, 2):
            ax.set_xlim(-60, 30); ax.set_ylim(-60, 48); ax.set_xlabel('x'); ax.set_ylabel('z')
        else:
            ax.set_xlim(-35, 35); ax.set_ylim(-50, 45); ax.set_xlabel('y'); ax.set_ylabel('z')
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)


def print_views(path):
    fig = plt.figure(figsize=(16, 8))
    for i, (m, name, R) in enumerate(((body, 'body: standing on the bottom wall, z up', np.eye(3)),
                                      (cover, 'cover: flat on its outer face (x -47 face on the bed)', np.array([[0, -1, 0], [0, 0, 1], [1, 0, 0]], float)))):
        v = m.vertices @ R.T; mm = trimesh.Trimesh(v, m.faces, process=False)
        n = mm.face_normals; bed = mm.bounds[0][2]
        fz = mm.triangles[:, :, 2].max(1)
        over = (n[:, 2] < -0.7072) & (fz > bed + 0.05)
        for j, (elev, azim) in enumerate(((-25, 145), (25, -35))):
            ax = fig.add_subplot(2, 2, i * 2 + j + 1, projection='3d')
            tri = mm.vertices[mm.faces]
            cols = np.where(over[:, None], np.array([[0.85, 0.1, 0.1, 1.0]]), np.array([[0.75, 0.75, 0.75, 0.9]]))
            ax.add_collection3d(Poly3DCollection(tri, facecolors=cols, edgecolors='none'))
            lo, hi = mm.bounds; setup3d(ax, lo - 2, hi + 2, elev, azim)
            ax.set_title(f'{name}\nview {"from below" if elev < 0 else "from above"}; red = faces steeper than 45 deg overhang ({over.sum()} faces, {mm.area_faces[over].sum():.1f} mm2)', fontsize=8)
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if mode in ('assembled', 'all'):
        assembled(OUT / 'render_assembled_rear34.png')
    if mode in ('rear', 'all'):
        assembled(OUT / 'render_rear_cover_off.png', show_cover=False, elev=8, azim=180, shells=False, title='rear view, cover off (shells off)')
    if mode in ('front', 'all'):
        assembled(OUT / 'render_front_plate_imu.png', show_cover=True, elev=12, azim=-5, shells=False, title='front view: plate, tabs, IMU holder (shells off)')
    if mode in ('sections', 'all'):
        sections(OUT / 'render_sections.png')
    if mode in ('print', 'all'):
        print_views(OUT / 'render_print_poses.png')
    print('done', mode)
