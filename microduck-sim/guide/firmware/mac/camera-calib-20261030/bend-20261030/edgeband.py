"""Straighten the ruler's cm-scale edge in a frame and write a diagnostic band image so the tick pattern can be
read and verified by eye.

The DigiKey PCB ruler is a 1.6 mm board; its left side (the cm scale edge, nearest the robot's x axis) shows as a
dark line in the picture (the board's shadowed side). For each row the dark line is the brightness minimum inside a
window round a guessed straight line u = u0 + (u1 - u0) v / 359, and the scale edge is the first column right of it
where the brightness recovers half-way. The band image shows columns edge-10 .. edge+70 of every row, stretched
`zoom` times, with a whiteness profile (V (1 - S), mean of columns edge+2 .. edge+30) plotted beside it.

usage: python edgeband.py OUT_DIR frame:u0:u1 [frame:u0:u1 ...]
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def whiteness(im):
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).astype(float)
    return (hsv[:, :, 2] / 255.0) * (1 - hsv[:, :, 1] / 255.0)


def scale_edge(im, u0, u1, half=35):
    """{row: edge column (float)} and {row: dark-line column}."""
    v_ch = cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2HSV)[:, :, 2].astype(float), (7, 7), 0)
    edge, dark = {}, {}
    H, W = v_ch.shape
    for v in range(H):
        g = u0 + (u1 - u0) * v / (H - 1)
        lo, hi = int(max(0, g - half)), int(min(W - 1, g + half))
        if hi - lo < 10:
            continue
        seg = v_ch[v, lo:hi + 1]
        k = int(np.argmin(seg))
        ud = lo + k
        if ud >= W - 6:
            continue
        vmin = seg[k]
        right = v_ch[v, ud:min(W, ud + 40)]
        vmax = right.max()
        thr = 0.5 * (vmin + vmax)
        above = np.nonzero(right > thr)[0]
        if above.size == 0:
            continue
        j = above[0]
        # sub-pixel crossing between j-1 and j
        if j > 0 and right[j] != right[j - 1]:
            frac = (thr - right[j - 1]) / (right[j] - right[j - 1])
        else:
            frac = 0.0
        edge[v] = float(ud + j - 1 + frac)
        dark[v] = int(ud)
    return edge, dark


def band(im, edge, left=10, width=80):
    rows = sorted(edge)
    out = np.zeros((len(rows), width, 3), np.uint8)
    w = whiteness(im)
    prof = np.zeros(len(rows))
    for i, v in enumerate(rows):
        x0 = int(round(edge[v])) - left
        for k in range(width):
            x = x0 + k
            if 0 <= x < im.shape[1]:
                out[i, k] = im[v, x]
        xs = [x for x in range(int(round(edge[v])) + 2, int(round(edge[v])) + 30) if x < im.shape[1]]
        prof[i] = w[v, xs].mean() if xs else 0
    return rows, out, prof


def diagnostic(im, name, u0, u1, out_dir, left=10, width=80, zoom=4):
    edge, dark = scale_edge(im, u0, u1)
    if not edge:
        print(name, "no edge")
        return None
    rows, b, prof = band(im, edge, left, width)
    z = cv2.resize(b, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_CUBIC)
    pw = 200
    plot = np.full((z.shape[0], pw, 3), 255, np.uint8)
    for i in range(1, len(rows)):
        cv2.line(plot, (int(prof[i - 1] * (pw - 10)), (i - 1) * zoom + zoom // 2),
                 (int(prof[i] * (pw - 10)), i * zoom + zoom // 2), (0, 0, 0), 1)
    img = np.concatenate([z, plot], axis=1)
    for i, v in enumerate(rows):
        if v % 10 == 0:
            col = (0, 255, 0) if v % 50 == 0 else (0, 140, 0)
            cv2.line(img, (0, i * zoom), (img.shape[1], i * zoom), col, 1)
            if v % 50 == 0:
                cv2.putText(img, str(v), (2, i * zoom - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
    cv2.line(img, (left * zoom, 0), (left * zoom, img.shape[0]), (255, 0, 0), 1)
    path = os.path.join(out_dir, f"band_{name}.png")
    cv2.imwrite(path, img)
    print(name, "rows", rows[0], "-", rows[-1], "edge u first/last %.1f %.1f" % (edge[rows[0]], edge[rows[-1]]), "->", path)
    return dict(rows=rows, edge=edge, prof=prof.tolist())


if __name__ == "__main__":
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    res = {}
    for spec in sys.argv[2:]:
        name, u0, u1 = spec.split(":")
        im = cv2.imread(os.path.join(HERE, "frames", f"{name}.png"))
        r = diagnostic(im, name, float(u0), float(u1), out_dir)
        if r:
            res[name] = dict(edge={str(k): v for k, v in r["edge"].items()}, prof=r["prof"], rows=r["rows"])
    json.dump(res, open(os.path.join(out_dir, "edgeband.json"), "w"))
