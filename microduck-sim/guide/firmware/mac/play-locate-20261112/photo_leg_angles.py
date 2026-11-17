"""Measure, on a front photo or video frame, each foot's yellow sole edge angle and its shin (ankle servo block) side
edge angles, and draw the fitted lines for a visual check. The shin-to-sole angle does not depend on camera or body
roll, so it compares directly across frames (standing against lifted) and against the rigid model.

  python3 photo_leg_angles.py FRAME.jpg OUT.png NAME:x0,y0,x1,y1 [NAME:...]
Boxes are pixel boxes holding one foot and the lower part of its shin.
"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw


def fit(xs, ys):  # y = a x + b, with one pass of outlier rejection
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    a, b = np.polyfit(xs, ys, 1)
    r = ys - (a * xs + b)
    k = np.abs(r) < 2.5 * (np.std(r) + 1e-9)
    a, b = np.polyfit(xs[k], ys[k], 1)
    return a, b


im = Image.open(sys.argv[1]).convert("RGB")
A = np.asarray(im).astype(int)
out = im.copy()
dr = ImageDraw.Draw(out)
R, G, B = A[..., 0], A[..., 1], A[..., 2]
yellow = (R > 150) & (G > 140) & (B < 120) & (R - B > 80) & (abs(R - G) < 70)
black = (R < 70) & (G < 70) & (B < 75)
for spec in sys.argv[3:]:
    name, box = spec.split(":")
    x0, y0, x1, y1 = map(int, box.split(","))
    Y = yellow[y0:y1, x0:x1]
    cols = [c for c in range(Y.shape[1]) if Y[:, c].sum() > 15]
    lo, hi = cols[0], cols[-1]
    keep = [c for c in cols if lo + 0.15 * (hi - lo) <= c <= hi - 0.15 * (hi - lo)]
    bot = [max(np.nonzero(Y[:, c])[0]) for c in keep]
    a, b = fit(keep, bot)
    sole = math.degrees(math.atan(a))  # + = right end lower in the image
    top_y = int(min(min(np.nonzero(Y[:, c])[0]) for c in keep))  # top of the yellow front face
    # shin block: rows from 40 px to 160 px above the sole top; widest solid black run per row
    Lx, Rx, rows = [], [], []
    K = black[y0:y1, x0:x1]
    for r in range(max(0, top_y - 170), top_y - 40):
        row = K[r]
        best, run, start = (0, 0, 0), 0, 0
        for c in range(len(row)):
            if row[c]:
                if run == 0:
                    start = c
                run += 1
                if run > best[0]:
                    best = (run, start, c)
            else:
                run = 0
        if best[0] > 60:
            rows.append(r); Lx.append(best[1]); Rx.append(best[2])
    al, bl = fit(rows, Lx)  # x = a y + b
    ar, br = fit(rows, Rx)
    shinL, shinR = math.degrees(math.atan(al)), math.degrees(math.atan(ar))
    shin = (shinL + shinR) / 2  # + = lower end further right in the image
    print(f"{name}: sole edge {sole:+.1f} deg (right end lower +), shin edges {shinL:+.1f} / {shinR:+.1f} "
          f"(lower end right +), shin-to-sole {sole + shin:+.1f}")
    X0, X1 = x0 + keep[0], x0 + keep[-1]
    dr.line([(X0, y0 + a * keep[0] + b), (X1, y0 + a * keep[-1] + b)], fill=(255, 0, 255), width=3)
    for aa, bb in ((al, bl), (ar, br)):
        dr.line([(x0 + aa * rows[0] + bb, y0 + rows[0]), (x0 + aa * rows[-1] + bb, y0 + rows[-1])], fill=(0, 255, 255),
                width=3)
out.save(sys.argv[2])
