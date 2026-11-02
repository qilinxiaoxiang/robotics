"""Crop the robot from a scan npz (floor frame: x,y in plane, z up) and render colored views."""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as ni

out = sys.argv[1]
D = np.load(out + ".npz")
P, C, F = D["P"], D["C"], D["F"]
ab = (P[:, 2] > 0.012)
g = 0.006
ij = np.floor(P[ab, :2] / g).astype(int)
ij -= ij.min(0)
occ = np.zeros(ij.max(0) + 1, bool)
occ[ij[:, 0], ij[:, 1]] = True
lab, n = ni.label(ni.binary_closing(occ, iterations=1))
sizes = ni.sum(occ, lab, range(1, n + 1))
# robot = component with the most colored (saturated) points
sat = (C.max(1).astype(int) - C.min(1)) > 70
sat_ab = sat[ab]
l = lab[ij[:, 0], ij[:, 1]]
score = np.bincount(l, weights=sat_ab, minlength=n + 1)
score[0] = 0
r = score.argmax()
keep = np.zeros(len(P), bool)
keep[np.where(ab)[0][l == r]] = True
Q = P[keep]
print("components", n, "robot comp pts", keep.sum(), "bbox", Q.min(0).round(3), Q.max(0).round(3), "ext mm", ((Q.max(0) - Q.min(0)) * 1000).round(1))
# PCA in plane for robot heading
xy = Q[:, :2] - Q[:, :2].mean(0)
w, v = np.linalg.eigh(np.cov(xy.T))
ax = v[:, 1]
print("plane eig (mm std)", (np.sqrt(w) * 1000).round(1), "major axis", ax.round(3))
R = np.c_[np.r_[ax, 0], np.r_[-ax[1], ax[0], 0], [0, 0, 1]]
L = (P - np.r_[Q[:, :2].mean(0), 0]) @ R
pad = 0.03
lo, hi = L[keep].min(0) - pad, L[keep].max(0) + pad
box = np.all((L > np.r_[lo[:2], -0.01]) & (L < np.r_[hi[:2], hi[2]]), axis=1)
np.savez(out + "_robot.npz", L=L[box], C=C[box], keep=keep[box], R=R, idx=np.where(box)[0])


def render(a, b, name, flip=False, res=0.5):
    q = L[box]
    x, y, z = q[:, a], q[:, b], q[:, 3 - a - b]
    if flip:
        z = -z
    W, H = int(np.ptp(x) * 1000 / res) + 3, int(np.ptp(y) * 1000 / res) + 3
    im = np.full((H, W, 3), 255, np.uint8)
    o = np.argsort(z)
    i = ((x[o] - x.min()) * 1000 / res).astype(int)
    j = H - 1 - ((y[o] - y.min()) * 1000 / res).astype(int)
    for di in (-1, 0, 1, 2):
        for dj in (-1, 0, 1, 2):
            im[np.clip(j + dj, 0, H - 1), np.clip(i + di, 0, W - 1)] = C[box][o]
    Image.fromarray(im).save(f"{out}_{name}.png")


render(0, 2, "side_a")
render(0, 2, "side_b", flip=True)
render(1, 2, "front_a")
render(0, 1, "top")
