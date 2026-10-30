"""Whiteness profiles along the straightened scale edge at three distances from it, to tell mm ticks (short),
5 mm ticks (longer), cm ticks (longest) and the labels apart. Writes a tall plot per frame: left the band image
(edge-10 .. edge+70, zoom 3), right the three profiles (A edge+2..+9 all ticks, B edge+14..+22 long ticks,
C edge+30..+55 labels) against the picture row, with local maxima of A marked and listed.

usage: python tickprof.py OUT_DIR frame:u0:u1 [...]
"""
import json
import os
import sys

import cv2
import numpy as np

from edgeband import scale_edge, whiteness

HERE = os.path.dirname(os.path.abspath(__file__))
WINDOWS = {"A": (2, 9), "B": (14, 22), "C": (30, 55)}


def profiles(im, edge):
    w = whiteness(im)
    rows = sorted(edge)
    out = {k: np.zeros(len(rows)) for k in WINDOWS}
    for i, v in enumerate(rows):
        e = int(round(edge[v]))
        for k, (a, b) in WINDOWS.items():
            xs = [x for x in range(e + a, e + b + 1) if x < im.shape[1]]
            out[k][i] = w[v, xs].mean() if xs else np.nan
    return rows, out


def local_max(p, rows, min_sep=5, min_prom=0.02):
    ps = np.convolve(np.nan_to_num(p), np.ones(3) / 3, mode="same")
    peaks = []
    for i in range(2, len(ps) - 2):
        if ps[i] >= ps[i - 1] and ps[i] >= ps[i + 1] and ps[i] > ps[i - 2] and ps[i] > ps[i + 2]:
            lo = ps[max(0, i - 8):i + 9].min()
            if ps[i] - lo >= min_prom:
                if peaks and rows[i] - peaks[-1][0] < min_sep:
                    if ps[i] > peaks[-1][1]:
                        peaks[-1] = (rows[i], ps[i])
                    continue
                peaks.append((rows[i], ps[i]))
    return peaks


def main():
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    res = {}
    for spec in sys.argv[2:]:
        name, u0, u1 = spec.split(":")
        im = cv2.imread(os.path.join(HERE, "frames", f"{name}.png"))
        edge, _ = scale_edge(im, float(u0), float(u1))
        rows, prof = profiles(im, edge)
        zoom = 3
        bandw = 80
        band = np.zeros((len(rows), bandw, 3), np.uint8)
        for i, v in enumerate(rows):
            x0 = int(round(edge[v])) - 10
            for k in range(bandw):
                x = x0 + k
                if 0 <= x < im.shape[1]:
                    band[i, k] = im[v, x]
        z = cv2.resize(band, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_NEAREST)
        pw = 420
        plot = np.full((z.shape[0], pw, 3), 255, np.uint8)
        cols = {"A": (0, 0, 0), "B": (0, 0, 255), "C": (255, 0, 0)}
        for k, p in prof.items():
            for i in range(1, len(rows)):
                if np.isnan(p[i - 1]) or np.isnan(p[i]):
                    continue
                cv2.line(plot, (int(p[i - 1] * (pw - 10)), (i - 1) * zoom + 1), (int(p[i] * (pw - 10)), i * zoom + 1), cols[k], 1)
        peaks = local_max(prof["A"], rows)
        for v, h in peaks:
            i = rows.index(v)
            cv2.line(plot, (0, i * zoom + 1), (pw, i * zoom + 1), (0, 160, 0), 1)
            cv2.putText(plot, str(v), (pw - 40, i * zoom + 1), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 120, 0), 1)
        img = np.concatenate([z, plot], axis=1)
        for i, v in enumerate(rows):
            if v % 50 == 0:
                cv2.line(img, (0, i * zoom), (z.shape[1], i * zoom), (0, 255, 0), 1)
                cv2.putText(img, str(v), (2, i * zoom - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        cv2.imwrite(os.path.join(out_dir, f"prof_{name}.png"), img)
        print(name, "A peaks:", [v for v, _ in peaks])
        res[name] = dict(rows=rows, edge={str(k): v for k, v in edge.items()}, peaksA=[v for v, _ in peaks],
                         **{k: np.nan_to_num(p).tolist() for k, p in prof.items()})
    json.dump(res, open(os.path.join(out_dir, "tickprof.json"), "w"))


if __name__ == "__main__":
    main()
