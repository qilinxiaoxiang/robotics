"""Tiny numpy z-buffer rasterizer (orthographic) for the pack renders; no GPU/OpenGL libraries available in the venv."""
import numpy as np
from PIL import Image, ImageDraw


def _basis(view_dir, up):
    d = np.asarray(view_dir, float); d /= np.linalg.norm(d)                 # direction FROM camera TO scene
    u = np.asarray(up, float); r = np.cross(d, u); r /= np.linalg.norm(r); u = np.cross(r, d)
    return r, u, d


def render(layers, view_dir, up=(0, 0, 1), px_per_mm=8.0, bounds=None, bg=(255, 255, 255), light=(-0.4, 0.5, 0.75), ghost=None):
    """layers: list of (trimesh, rgb tuple 0-255). ghost: optional list of (trimesh, rgb, alpha) drawn translucent over the result
    where the ghost is in front of the opaque depth. Returns PIL RGB image."""
    r, u, d = _basis(view_dir, up)
    allv = np.vstack([m.vertices for m, _ in layers] + [m.vertices for m, _, _ in (ghost or [])])
    pr = allv @ r; pu = allv @ u
    if bounds is None:
        lo = np.array([pr.min(), pu.min()]) - 3; hi = np.array([pr.max(), pu.max()]) + 3
    else:
        lo, hi = np.asarray(bounds[0], float), np.asarray(bounds[1], float)
    W = int(np.ceil((hi[0] - lo[0]) * px_per_mm)); H = int(np.ceil((hi[1] - lo[1]) * px_per_mm))
    L = np.asarray(light, float); L /= np.linalg.norm(L)

    def raster(meshes):
        depth = np.full((H, W), np.inf); col = np.zeros((H, W, 3), np.uint8); hit = np.zeros((H, W), bool)
        for m, rgb in meshes:
            V = m.vertices; F = m.faces; n = m.face_normals
            shade = 0.35 + 0.65 * np.clip(n @ L, 0, 1)
            sx = (V @ r - lo[0]) * px_per_mm; sy = (hi[1] - V @ u) * px_per_mm; sz = V @ d
            tx = sx[F]; ty = sy[F]; tz = sz[F]
            x0 = np.clip(np.floor(tx.min(1)).astype(int), 0, W - 1); x1 = np.clip(np.ceil(tx.max(1)).astype(int), 0, W - 1)
            y0 = np.clip(np.floor(ty.min(1)).astype(int), 0, H - 1); y1 = np.clip(np.ceil(ty.max(1)).astype(int), 0, H - 1)
            rgb = np.asarray(rgb, float)
            for i in range(len(F)):
                if x1[i] < x0[i] or y1[i] < y0[i]:
                    continue
                ax, ay = tx[i, 0], ty[i, 0]; bx, by = tx[i, 1], ty[i, 1]; cx, cy = tx[i, 2], ty[i, 2]
                det = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
                if abs(det) < 1e-9:
                    continue
                xs = np.arange(x0[i], x1[i] + 1) + 0.5; ys = np.arange(y0[i], y1[i] + 1) + 0.5
                X, Y = np.meshgrid(xs, ys)
                l1 = ((bx - X) * (cy - Y) - (cx - X) * (by - Y)) / det
                l2 = ((cx - X) * (ay - Y) - (ax - X) * (cy - Y)) / det
                l3 = 1 - l1 - l2
                ins = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
                if not ins.any():
                    continue
                z = l1 * tz[i, 0] + l2 * tz[i, 1] + l3 * tz[i, 2]
                sub = depth[y0[i]:y1[i] + 1, x0[i]:x1[i] + 1]
                upd = ins & (z < sub)
                sub[upd] = z[upd]
                col[y0[i]:y1[i] + 1, x0[i]:x1[i] + 1][upd] = np.clip(rgb * shade[i], 0, 255).astype(np.uint8)
                hit[y0[i]:y1[i] + 1, x0[i]:x1[i] + 1][upd] = True
        return depth, col, hit

    depth, col, hit = raster(layers)
    img = np.full((H, W, 3), bg, np.uint8); img[hit] = col[hit]
    if ghost:
        gd, gc, gh = raster([(m, c) for m, c, _ in ghost])
        a = ghost[0][2]
        front = gh & (gd < depth)
        img[front] = (img[front] * (1 - a) + gc[front] * a).astype(np.uint8)
    return Image.fromarray(img), (lo, hi, px_per_mm, r, u)


def label(img, text, xy=(8, 8)):
    ImageDraw.Draw(img).text(xy, text, fill=(0, 0, 0))
    return img
