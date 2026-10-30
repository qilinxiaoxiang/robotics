"""Read the ruler ticks in the bend frames and write bend_ticks.json plus annotated check_*.png crops.

Rise frames (f012106..f012117, neck -1.6, head +0.33): the cm scale edge of the DigiKey 12-inch PCB ruler runs up the
right part of the picture; the labels 1 and 2 are legible and sit on their cm ticks (the digit is centred under the
long tick on this ruler), the 3 cm tick is the tenth mm tick above the 2 cm tick (the label 3 is at the top edge).
Procedure per frame: straighten the scale edge (edgeband.scale_edge), whiteness profiles A (ticks, edge+2..+9) and
C (labels, edge+30..+55), local maxima of A merged when closer than 9 px, the 2 cm tick = A peak nearest the C
maximum in rows 150..240, the 1 cm tick = A peak nearest the C maximum in rows 270..345, the 3 cm tick = ten merged
A peaks above the 2 cm tick (None when the count runs off the top).

Held frames (phases 0.12..0.33, neck -1.33, head -0.26..-0.31): only the ruler's scale edge and a sliver of ticks are
in the picture at its right edge, without labels; the tick rows are stored with cm = None (identity assigned later
by bendfit.py from the fitted model's prediction, and only when the prediction locks the pattern).

usage: python readticks.py [OUT_DIR]   (default: this directory)
"""
import json
import os
import sys

import cv2
import numpy as np

from edgeband import scale_edge
from tickprof import local_max, profiles

HERE = os.path.dirname(os.path.abspath(__file__))
RISE = ["f012106", "f012108", "f012110", "f012112", "f012113", "f012114", "f012116"]
# picture row of the cm tick per rise frame: digit centres of the labels 1 and 2 read by eye on 3x gridded crops
# (g_*.png / check_*.png), the 3 cm tick counted as the tenth mm tick above the 2 cm tick on the A-peak list
RISE_MANUAL = {
    "f012106": {1: 320.0, 2: 195.0},
    "f012108": {1: 318.0, 2: 198.0},
    "f012110": {1: 320.0, 2: 195.0},
    "f012112": {1: 317.0, 2: 185.0, 3: 11.0},
    "f012113": {1: 312.0, 2: 180.0, 3: 8.0},
    "f012114": {1: 315.0, 2: 175.0},
    "f012116": {1: 303.0, 2: 170.0},
}
HELD = {0.12: ["f011960", "f011970", "f011980", "f011990"], 0.20: ["f012000", "f012010", "f012020", "f012027"],
        0.28: ["f012035", "f012045", "f012055", "f012063"], 0.33: ["f012070", "f012080", "f012090", "f012098"]}
GUESS = {"rise": (528.0, 445.0), "held": (588.0, 532.0)}


def refined_edge(im, guess):
    edge, _ = scale_edge(im, *guess)
    rows = np.array(sorted(edge))
    us = np.array([edge[v] for v in rows])
    a, b = np.polyfit(rows, us, 1)
    edge, dark = scale_edge(im, b, b + a * (im.shape[0] - 1), half=25)
    return edge


def merge_peaks(peaks, min_sep=9):
    out = []
    for v, h in peaks:
        if out and v - out[-1][0] < min_sep:
            pv, ph = out[-1]
            out[-1] = ((pv * ph + v * h) / (ph + h), max(ph, h))
        else:
            out.append((float(v), h))
    return [v for v, _ in out]


def nearest(peaks, v, tol=15):
    if not peaks:
        return None
    p = min(peaks, key=lambda x: abs(x - v))
    return p if abs(p - v) <= tol else None


def read_rise(name, out_dir):
    im = cv2.imread(os.path.join(HERE, "frames", f"{name}.png"))
    edge = refined_edge(im, GUESS["rise"])
    rows, prof = profiles(im, edge)
    rows = list(rows)
    peaks = merge_peaks(local_max(prof["A"], rows))
    C = np.array(prof["C"])

    def c_max(lo, hi):
        idx = [i for i, v in enumerate(rows) if lo <= v <= hi]
        return rows[max(idx, key=lambda i: C[i])] if idx else None

    ticks = {}
    l2, l1 = c_max(150, 240), c_max(270, 345)
    if name in RISE_MANUAL:
        # digit centres read by eye on the 3x gridded crops (the digit sits centred under its cm tick on this ruler),
        # +-8 px; the 3 cm tick counted as the tenth mm tick (A peak) above the 2 cm one where the count stays inside
        # the picture; the automatic label rows l2 / l1 are kept only for the check picture
        ticks = dict(RISE_MANUAL[name])
    else:
        t2 = nearest(peaks, l2) if l2 is not None else None
        t1 = nearest(peaks, l1) if l1 is not None else None
        if t2 is not None:
            ticks[2] = t2
            above = [p for p in peaks if p < t2 - 4]
            above.sort(reverse=True)
            if len(above) >= 10:
                ticks[3] = above[9]
        if t1 is not None:
            ticks[1] = t1
    obs = []
    for cm, v in ticks.items():
        vi = int(round(v))
        u = edge[vi] if vi in edge else None
        if u is None:
            continue
        obs.append(dict(frame=name, cm=cm, u=float(u), v=float(v)))
    # annotated check crop
    crop = im[:, 420:640].copy()
    for v in edge:
        cv2.circle(crop, (int(round(edge[v])) - 420, v), 0, (0, 255, 0), -1)
    for p in peaks:
        vi = int(round(p))
        if vi in edge:
            cv2.line(crop, (int(round(edge[vi])) - 420, vi), (int(round(edge[vi])) - 420 + 12, vi), (255, 255, 0), 1)
    for cm, v in ticks.items():
        vi = int(round(v))
        if vi in edge:
            x = int(round(edge[vi])) - 420
            cv2.line(crop, (x - 30, vi), (x + 40, vi), (0, 0, 255), 1)
            cv2.putText(crop, f"{cm} cm", (x - 60, vi + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
    for lab, v in (("L2", l2), ("L1", l1)):
        if v is not None and v in edge:
            cv2.putText(crop, lab, (int(round(edge[v])) - 420 + 45, v + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
    crop = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(os.path.join(out_dir, f"check_{name}.png"), crop)
    spacing = np.diff(sorted(peaks)).round(1).tolist()
    print(name, "label rows L2/L1", l2, l1, "ticks", {k: round(v, 1) for k, v in ticks.items()}, "peaks", [round(p) for p in peaks])
    return obs, dict(peaks=peaks, spacing=spacing, edge={str(k): v for k, v in edge.items()}, labels=dict(L2=l2, L1=l1))


def read_held(name, phase, out_dir):
    im = cv2.imread(os.path.join(HERE, "frames", f"{name}.png"))
    edge = refined_edge(im, GUESS["held"])
    rows, prof = profiles(im, edge)
    rows = list(rows)
    peaks = merge_peaks(local_max(prof["A"], rows, min_prom=0.015))
    obs = []
    for p in peaks:
        vi = int(round(p))
        if vi in edge and 8 <= vi <= 351:
            obs.append(dict(frame=name, cm=None, u=float(edge[vi]), v=float(p), phase=phase))
    crop = im[:, 480:640].copy()
    for v in edge:
        cv2.circle(crop, (int(round(edge[v])) - 480, v), 0, (0, 255, 0), -1)
    for p in peaks:
        vi = int(round(p))
        if vi in edge:
            x = int(round(edge[vi])) - 480
            cv2.line(crop, (x, vi), (min(159, x + 15), vi), (255, 255, 0), 1)
            cv2.putText(crop, str(vi), (max(0, x - 30), vi + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 0), 1)
    crop = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(os.path.join(out_dir, f"check_{name}.png"), crop)
    print(name, f"phase {phase}", "edge u top/bottom %.1f %.1f" % (edge[min(edge)], edge[max(edge)]),
          "tick rows", [round(p) for p in peaks], "spacing", np.diff(sorted(peaks)).round(0).tolist())
    return obs, dict(peaks=peaks, edge={str(k): v for k, v in edge.items()})


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else HERE
    os.makedirs(out_dir, exist_ok=True)
    rows = {r["name"]: r for r in json.load(open(os.path.join(HERE, "rows_matched.json")))}
    obs, detail = [], {}
    for name in RISE:
        o, d = read_rise(name, out_dir)
        for x in o:
            x.update(phase=1.0, q=rows[name]["q"], gb=rows[name]["gb"], t_cap=rows[name]["t_cap"])
        obs += o
        detail[name] = d
    for phase, names in HELD.items():
        for name in names:
            o, d = read_held(name, phase, out_dir)
            for x in o:
                x.update(q=rows[name]["q"], gb=rows[name]["gb"], t_cap=rows[name]["t_cap"])
            obs += o
            detail[name] = d
    out = dict(note="u, v: continuous pixel of the tick at the cm scale edge (the ruler's left side, foot-frame y = "
                    "-0.0093); cm = None for held-frame ticks without a legible label. x is assigned by bendfit.py: "
                    "toe_x(q, gb) + cm / 100, the tick lies on the 1.6 mm board top.",
               ruler=dict(y_edge=-0.0093, y_centre=-0.022, width_m=0.0254, thickness_m=0.0016),
               obs=obs, detail=detail)
    json.dump(out, open(os.path.join(HERE, "bend_ticks.json"), "w"), indent=1)
    print(len(obs), "rows ->", os.path.join(HERE, "bend_ticks.json"))


if __name__ == "__main__":
    main()
