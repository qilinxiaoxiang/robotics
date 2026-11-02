"""Load a Scaniverse OBJ, find the floor, keep what stands on it, render colored orthographic views."""
import sys, json, numpy as np, trimesh
from PIL import Image

path, out = sys.argv[1], sys.argv[2]
m = trimesh.load(path, process=False, force="mesh")
V = np.asarray(m.vertices)
print("verts", len(V), "faces", len(m.faces), "bbox", V.min(0).round(3), V.max(0).round(3), "ext", (V.max(0) - V.min(0)).round(3))
print("watertight", m.is_watertight, "median edge mm", round(float(np.median(m.edges_unique_length)) * 1000, 2))
uv = m.visual.uv
img = np.asarray(m.visual.material.image.convert("RGB"))
h, w = img.shape[:2]
C = img[np.clip(((1 - uv[:, 1]) * h).astype(int), 0, h - 1), np.clip((uv[:, 0] * w).astype(int), 0, w - 1)]

# floor by RANSAC
rng = np.random.default_rng(0)
best, bn, bd = 0, None, None
for _ in range(1500):
    p = V[rng.choice(len(V), 3, replace=False)]
    n = np.cross(p[1] - p[0], p[2] - p[0])
    if np.linalg.norm(n) < 1e-9:
        continue
    n /= np.linalg.norm(n)
    d = np.abs((V - p[0]) @ n)
    c = (d < 0.003).sum()
    if c > best:
        best, bn, bd = c, n, -p[0] @ n
if bn[1] < 0:
    bn, bd = -bn, -bd
print("floor normal", bn.round(4), "inliers", best, "of", len(V))
H = V @ bn + bd
inl = np.abs(H) < 0.003
print("floor rms mm (<3mm inliers)", round(float(np.sqrt((H[inl] ** 2).mean())) * 1000, 2), "height range", H.min().round(3), H.max().round(3))
# basis
u = np.cross(bn, [0, 0, 1.0]); u /= np.linalg.norm(u)
t = np.cross(bn, u)
P = np.c_[V @ u, V @ t, H]
np.savez(out + ".npz", P=P, C=C, F=m.faces, n=bn, d=bd, u=u, t=t)


def render(a, b, name, res=1.0, mask=None):
    """res in mm/px, painter sort by depth from third axis handled by caller order."""
    Q = P if mask is None else P[mask]
    CC = C if mask is None else C[mask]
    x, y, z = Q[:, a], Q[:, b], Q[:, 3 - a - b]
    W, H_ = int((x.max() - x.min()) * 1000 / res) + 2, int((y.max() - y.min()) * 1000 / res) + 2
    im = np.full((H_, W, 3), 255, np.uint8)
    o = np.argsort(z)
    i = ((x[o] - x.min()) * 1000 / res).astype(int)
    j = H_ - 1 - ((y[o] - y.min()) * 1000 / res).astype(int)
    for di in (0, 1):
        for dj in (0, 1):
            im[np.clip(j + dj, 0, H_ - 1), np.clip(i + di, 0, W - 1)] = CC[o]
    Image.fromarray(im).save(f"{out}_{name}.png")
    print(name, im.shape)


render(0, 1, "top_all", res=max(1.0, float(np.ptp(P[:, :2], axis=0).max()) * 1000 / 900))
# objects above the floor near the tallest cluster
above = (H > 0.01) & (H < 0.6)
print("points above floor", above.sum())
xy = P[above, :2]
print("above-floor xy p1/p99", np.percentile(xy, 1, axis=0).round(3), np.percentile(xy, 99, axis=0).round(3))
json.dump({"above": int(above.sum())}, open(out + ".json", "w"))
