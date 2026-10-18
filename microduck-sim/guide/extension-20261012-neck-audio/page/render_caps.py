#!/usr/bin/env python3
"""Exterior of the V1.8 head cap next to the integrated extension study cap (same camera), for the review page."""
from pathlib import Path
import numpy as np, trimesh, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

EXT = Path(__file__).resolve().parents[1]
CAPS = [('V1.8 现在的头盖', EXT.parents[1] / 'guide/print/world/head_cap.stl'),
        ('拓展版头盖（研究件）', EXT / 'integrated/study-solids/head_cap-integrated-world.stl')]
LIGHT = np.array([-0.4, 0.3, 0.85]); LIGHT /= np.linalg.norm(LIGHT)
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Hiragino Sans GB', 'Arial Unicode MS']

def draw(ax, mesh, elev, azim, title):
    e, a = np.radians(elev), np.radians(azim)
    view = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])  # towards the camera
    keep = mesh.face_normals @ view > 0
    # painter's order: far faces first
    order = np.argsort((mesh.triangles_center[keep] @ view))
    tri = mesh.vertices[mesh.faces[keep]][order]
    shade = 0.35 + 0.65 * np.clip(mesh.face_normals[keep][order] @ LIGHT, 0, 1)
    col = np.c_[0.93 * shade, 0.55 * shade, 0.12 * shade, np.ones_like(shade)]
    pc = Poly3DCollection(tri, facecolors=col, edgecolors='none'); ax.add_collection3d(pc)
    lo, hi = mesh.bounds; c = (lo + hi) / 2; r = (hi - lo).max() / 2
    ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r); ax.set_zlim(c[2]-r, c[2]+r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=elev, azim=azim); ax.set_axis_off(); ax.set_title(title, fontsize=13)

fig = plt.figure(figsize=(12, 6), dpi=110)
for i, (title, path) in enumerate(CAPS):
    m = trimesh.load(path)
    draw(fig.add_subplot(1, 2, i + 1, projection='3d'), m, 32, 155, title)
plt.subplots_adjust(left=0, right=1, bottom=0, top=0.93, wspace=0); out = Path(__file__).with_name('caps-rear.png'); plt.savefig(out); print(out)
