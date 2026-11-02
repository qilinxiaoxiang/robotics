"""Colour-classed, two-way (scan->model and model->scan) rigid fit of the head and feet, multi-start. Sliding along a
smooth shell is what spoiled the first fit: the white/yellow border and the model->scan term pin it."""
import sys, json, os, numpy as np
from scipy.spatial import cKDTree as KD
from scipy.spatial.transform import Rotation as Rot


S = sys.argv[1]
GLOBAL = {"a": (-29.18, [-0.0031, 0.0035, 0.0]), "b": (-5.46, [0.0224, 0.005, 0.0])}


def rz(deg):
    a = np.radians(deg)
    return np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])


def classes(C):
    c = C.astype(float) / 255
    mx, mn = c.max(1), c.min(1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    hue = np.zeros(len(c))
    r, g, b = c.T
    d = np.maximum(mx - mn, 1e-6)
    m = mx == r
    hue[m] = ((g - b)[m] / d[m]) % 6
    m = mx == g
    hue[m] = (b - r)[m] / d[m] + 2
    m = mx == b
    hue[m] = (r - g)[m] / d[m] + 4
    hue *= 60
    out = np.full(len(c), "x", dtype="U1")
    out[(sat < 0.28) & (mx > 0.55)] = "w"
    out[(sat > 0.45) & (hue > 40) & (hue < 68) & (mx > 0.45)] = "y"
    out[(sat > 0.5) & (hue >= 5) & (hue <= 38) & (mx > 0.45)] = "o"
    return out


def solve(a, b):
    ca, cb = a.mean(0), b.mean(0)
    U, W, Vt = np.linalg.svd((a - ca).T @ (b - cb))
    Dg = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ Dg @ U.T
    return R, cb - R @ ca


def fit(src, P, R0, t0, iters=40):
    """src: {class: scan pts}, P: {class: model pts}. Finds model->real pose T: x_real = R p + t."""
    R, t = R0, t0
    trees_m = {k: KD(v) for k, v in P.items()}
    trees_s = {k: KD(v) for k, v in src.items()}
    for it in range(iters):
        gate = 0.025 + (0.005 - 0.025) * min(1, it / (iters * 0.7))
        A, B = [], []
        for k in P:
            X = P[k] @ R.T + t  # model in real frame
            d, i = trees_s[k].query(X, distance_upper_bound=gate)  # model->scan
            ok = np.isfinite(d)
            if ok.sum() > 30:
                ok &= d <= np.quantile(d[ok], 0.8)
                A.append(P[k][ok]); B.append(src[k][i[ok]])
            pinv = (src[k] - t) @ R
            d, i = trees_m[k].query(pinv, distance_upper_bound=gate)  # scan->model
            ok = np.isfinite(d)
            if ok.sum() > 30:
                ok &= d <= np.quantile(d[ok], 0.8)
                A.append(P[k][i[ok]]); B.append(src[k][ok])
        if not A:
            return None
        R, t = solve(np.vstack(A), np.vstack(B))
    cost, cov, n = 0.0, 0.0, 0
    for k in P:
        X = P[k] @ R.T + t
        d, _ = trees_s[k].query(X)
        d = np.minimum(d, 0.012)
        cost += (d ** 2).sum(); cov += (d < 0.004).sum(); n += len(d)
        d, _ = trees_m[k].query((src[k] - t) @ R)
        d = np.minimum(d, 0.012)
        cost += (d ** 2).sum(); n += len(d)
    return R, t, float(np.sqrt(cost / n) * 1000), cov / max(1, sum(len(v) for v in P.values()))


