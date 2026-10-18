#!/usr/bin/env python3
"""Free height under the V1.8 head roof, with every motion that happens inside the head.

For each (x, y) column on a 0.5 mm grid: roof = lowest cap voxel above z 128 (cap inner roof), floor = highest
occupied voxel below the roof from: head-fixed parts (motor14, motor15, jaw_support, mouth ring, lower shell, face,
eye trim, camera, Pi group with all 8 plugged housings), the yaw body (motor13, head_yaw_link, both roll rings)
swept through head roll -25..+25 deg about the MJCF head_roll axis, the jaw frame swept 0..40 deg, and keep-out
tubes around the existing cables (head_csi ribbon r 4 mm, bundle_head r 3 mm). Writes ../freespace.json and
../png/freespace-under-roof.png. Voxel screening only; exact checks are in check_study.py.
"""
from __future__ import annotations

import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh

from scene import JAW_PIVOT, SIM, STUDY, load_tm, manifest, pi_group_keys

H = 0.5
LO = np.array([-34.0, -46.0, 98.0])
HI = np.array([93.0, 46.0, 158.0])
SHAPE = np.ceil((HI - LO) / H).astype(int)
ROLL_AXIS_P = np.array([8.1, 0.0, 115.615])   # MJCF head_roll anchor, axis -x (robot frame)
FIXED = ['head_bottom', 'face_panel', 'eye_trim', 'camera_board', 'motor14', 'motor15', 'jaw_support',
         'mouth_sliding_ring']
YAW = ['motor13', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b']


def T_rot(axis, deg, p):
    a = np.radians(deg)
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    R = np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = p - R @ p
    return T


def vox(m: trimesh.Trimesh, grid):
    """Mark voxel centres inside the mesh: exact manifold3d slices at every voxel-centre z, rasterised with an
    even-odd point-in-polygon test (matplotlib Path) on the mesh's sub-grid."""
    from matplotlib.path import Path as MPath
    import manifold3d as m3
    M = m3.Manifold(m3.Mesh(vert_properties=np.ascontiguousarray(m.vertices, np.float32),
                            tri_verts=np.ascontiguousarray(m.faces, np.uint32)))
    b = m.bounds
    i0 = np.clip(np.floor((b[0] - LO) / H).astype(int) - 1, 0, SHAPE - 1)
    i1 = np.clip(np.ceil((b[1] - LO) / H).astype(int) + 1, 0, SHAPE - 1)
    xs = LO[0] + H * (np.arange(i0[0], i1[0] + 1) + 0.5)
    ys = LO[1] + H * (np.arange(i0[1], i1[1] + 1) + 0.5)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    P = np.c_[X.ravel(), Y.ravel()]
    for kz in range(i0[2], i1[2] + 1):
        z = LO[2] + H * (kz + 0.5)
        polys = M.slice(z).to_polygons()
        if not len(polys):
            continue
        inside = np.zeros(len(P), bool)
        for poly in polys:
            poly = np.asarray(poly)
            if len(poly) >= 3:
                inside ^= MPath(poly).contains_points(P)   # even-odd over outer loops and holes
        inside = inside.reshape(X.shape)
        grid[i0[0]:i1[0] + 1, i0[1]:i1[1] + 1, kz] |= inside


def tube(grid, pts, r):
    pts = np.asarray(pts, float)
    seg = []
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(2, int(np.linalg.norm(b - a) / 0.25))
        seg.append(np.linspace(a, b, n))
    S = np.vstack(seg)
    lo = np.floor((S.min(0) - r - LO) / H).astype(int)
    hi = np.ceil((S.max(0) + r - LO) / H).astype(int)
    ax = [LO[k] + H * (np.arange(lo[k], hi[k] + 1) + 0.5) for k in range(3)]
    X, Y, Z = np.meshgrid(*ax, indexing='ij')
    P = np.c_[X.ravel(), Y.ravel(), Z.ravel()]
    from scipy.spatial import cKDTree
    d, _ = cKDTree(S).query(P)
    grid[lo[0]:hi[0] + 1, lo[1]:hi[1] + 1, lo[2]:hi[2] + 1] |= (d <= r).reshape(X.shape)


def main():
    man = manifest()
    cap = np.zeros(SHAPE, bool)
    occ = np.zeros(SHAPE, bool)
    vox(load_tm('head_cap'), cap)
    for k in FIXED + pi_group_keys(man):
        vox(load_tm(k), occ)
    for k in YAW:
        m0 = load_tm(k)
        for a in np.arange(-25, 25.1, 2.5):
            vox(m0.copy().apply_transform(T_rot([-1, 0, 0], a, ROLL_AXIS_P)), occ)
    j0 = load_tm('jaw_frame')
    for a in np.arange(0, 40.1, 2.0):
        vox(j0.copy().apply_transform(T_rot([0, 1, 0], a, JAW_PIVOT)), occ)
    routes = json.loads((SIM / 'guide' / 'content' / 'routes.json').read_text())['routes']
    cab = np.zeros(SHAPE, bool)
    tube(cab, routes['head_csi'], 4.0)
    tube(cab, routes['bundle_head'], 3.0)
    np.savez_compressed(STUDY / 'scripts' / '.freespace-grid.npz', cap=cap, occ=occ, cab=cab)
    zc = LO[2] + H * (np.arange(SHAPE[2]) + 0.5)
    roof = np.full(SHAPE[:2], np.nan)
    floor_parts = np.full(SHAPE[:2], np.nan)
    floor_all = np.full(SHAPE[:2], np.nan)
    for i in range(SHAPE[0]):
        for j in range(SHAPE[1]):
            c = np.where(cap[i, j] & (zc > 128))[0]
            if not len(c):
                continue
            # roof = underside of the topmost cap run: walk down from the top cap voxel to the first non-cap voxel
            k = c.max()
            while k > 0 and cap[i, j, k]:
                k -= 1
            roof[i, j] = zc[k] + H / 2
            below = np.where(occ[i, j, :k + 1])[0]
            floor_parts[i, j] = zc[below.max()] + H / 2 if len(below) else np.nan
            below2 = np.where((occ | cab)[i, j, :k + 1])[0]
            floor_all[i, j] = zc[below2.max()] + H / 2 if len(below2) else np.nan
    xs = LO[0] + H * (np.arange(SHAPE[0]) + 0.5)
    ys = LO[1] + H * (np.arange(SHAPE[1]) + 0.5)
    np.savez_compressed(STUDY / 'scripts' / '.freespace-maps.npz', xs=xs, ys=ys, roof=roof, fp=floor_parts, fa=floor_all)
    fig, axs = plt.subplots(1, 3, figsize=(18, 6))
    for ax, data, title in ((axs[0], roof, 'cap roof underside z (mm)'),
                            (axs[1], roof - floor_parts, 'free height under roof: parts + motions'),
                            (axs[2], roof - floor_all, 'free height: parts + motions + cable keep-outs')):
        im = ax.imshow(data.T, origin='lower', extent=[xs[0], xs[-1], ys[0], ys[-1]], cmap='viridis',
                       vmin=0 if 'free' in title else 135, vmax=25 if 'free' in title else 158)
        ax.set_title(title, fontsize=9)
        ax.set_xlabel('x mm')
        ax.set_ylabel('y mm')
        ax.grid(True, lw=0.3, color='w')
        fig.colorbar(im, ax=ax, shrink=0.7)
        if 'free' in title:
            cs = ax.contour(xs, ys, data.T, levels=[6, 10, 14], colors=['r', 'orange', 'w'], linewidths=0.8)
            ax.clabel(cs, fontsize=7)
    fig.tight_layout()
    fig.savefig(STUDY / 'png' / 'freespace-under-roof.png', dpi=110)
    out = {'gridMm': H, 'bounds': [LO.tolist(), HI.tolist()],
           'method': 'voxel centres inside closed audit solids (manifold3d slices, even-odd fill per slice); yaw body swept head roll -25..25 '
                     'deg step 2.5 about anchor [8.1, 0, 115.615] axis x; jaw frame 0..40 deg step 2; cable keep-outs '
                     'head_csi r4, bundle_head r3 (routes.json)',
           'measurement': 'voxel screening (0.5 mm), not exact'}
    (STUDY / 'freespace.json').write_text(json.dumps(out, indent=1))
    print('done')


if __name__ == '__main__':
    main()
