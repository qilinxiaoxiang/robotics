"""Read the ruler ticks in the hold frames of sweep2 / sweep3 / sweep4 and add them to bend_ticks.json (the sweep1
rows written by readticks.py are kept and tagged sweep "sweep1").

Per sweep and hold window (phase 0.05 / 0.08 / 0.12; deeper holds are blur or show no ruler) a few static frames
from the window's `use` stretch (sweepN/rows_matched.json, state = the next window's stored state, see
sweeps_match.py) are processed: the scale edge is straightened (edgeband.scale_edge round a per-window guess), the
whiteness profile A along it gives the mm-tick rows (local maxima, merged < 9 px). The cm identity comes from the
digits read by eye on 5x CLAHE crops of ONE frame per window (MANUAL below: the digit is centred under its long cm
tick on this ruler, +-8 px = +-0.5 mm); for the other frames of the same static window the manual row is snapped to
the nearest A peak within 6 px (the robot does not move inside a `use` stretch). Where the second digit was not
legible the second cm tick was counted as the tenth merged A peak from the read one (noted "by count").
sweep4 (ruler through the middle of the picture, cm scale at the left picture edge): no digit is legible on any
frame, so only the edge rows are stored (cm = None for the ticks).

Edge rows: the straightened edge column at rows 30, 90, .., 330 inside the window's visible range is what bendfit.py
uses as the lateral observation (no identity needed).

usage: python readticks_sweeps.py [OUT_DIR]   (check pictures check_<frame>.png; default: this directory)
"""
import json
import os
import sys

import cv2
import numpy as np

from edgeband import scale_edge
from readticks import merge_peaks, refined_edge
from tickprof import local_max, profiles

HERE = os.path.dirname(os.path.abspath(__file__))

# guess = (edge column at the top row, at the bottom row); crop = x range of the check picture;
# manual = {frame: {cm: picture row of the digit centre}}; edge_rows = rows where the ruler edge is in the picture
SWEEPS = {
    "sweep2": dict(crop=(430, 640), windows={
        0.05: dict(frames=["f091050", "f091060", "f091070", "f091078"], guess=(606, 532), edge_rows=(0, 359),
                   manual={"f091060": {6: 152, 5: 337}}, note="6 read by eye, 5 = tenth mm tick below it (long tick at 337)"),
        0.08: dict(frames=["f091100", "f091111", "f091120", "f091130"], guess=(581, 522), edge_rows=(0, 359),
                   manual={"f091111": {6: 259, 7: 66}}, note="6 and 7 read by eye"),
        0.12: dict(frames=["f091160", "f091170", "f091180", "f091190"], guess=(615, 600), edge_rows=(90, 359),
                   manual={}, note="sliver at the right picture edge, no digit"),
    }),
    "sweep3": dict(crop=(360, 640), windows={
        0.05: dict(frames=["f093200", "f093206", "f093215", "f093225"], guess=(429, 392), edge_rows=(0, 359),
                   manual={"f093206": {6: 135, 5: 302}}, note="6 read by eye, 5 = tenth mm tick below it (long tick at 302)"),
        0.08: dict(frames=["f093275", "f093285", "f093294"], guess=(440, 400), edge_rows=(0, 359),
                   manual={"f093294": {6: 200, 7: 20}}, note="6 read by eye, 7 read at the top edge (partly cut, 15-25)"),
        0.12: dict(frames=["f093310", "f093320", "f093330", "f093340"], guess=(525, 495), edge_rows=(0, 359),
                   manual={"f093320": {6: 315, 7: 118}}, note="6 read by eye; 7 read at 125 +-10, assigned to the peak 114 = ten mm ticks above the 6"),
    }),
    "sweep4": dict(crop=(0, 220), windows={
        0.05: dict(frames=["f094790", "f094800", "f094810", "f094820"], guess=(26, 59), edge_rows=(0, 359),
                   manual={}, note="blur, no digit legible"),
        0.08: dict(frames=["f094840", "f094860", "f094875", "f094885"], guess=(21, 61), edge_rows=(0, 359),
                   manual={}, note="blur, no digit legible"),
        0.12: dict(frames=["f094905", "f094920", "f094930", "f094937"], guess=(33, 50), edge_rows=(0, 359),
                   manual={}, note="blur, no digit legible"),
    }),
}


def read_frame(sweep, name, win, out_dir):
    cfg = SWEEPS[sweep]
    im = cv2.imread(os.path.join(HERE, sweep, f"{name}.png"))
    edge = refined_edge(im, win["guess"])
    lo, hi = win["edge_rows"]
    edge = {v: u for v, u in edge.items() if lo <= v <= hi}
    rows, prof = profiles(im, edge)
    rows = list(rows)
    peaks = merge_peaks(local_max(prof["A"], rows, min_prom=0.015))
    # cm identities from the window's manual reading (digit rows read by eye, +-8 px): in every static frame of the
    # window each row is snapped to the nearest A peak within 8 px (the robot does not move inside a `use` stretch)
    # and kept as read when no peak is that close
    manual = next(iter(win["manual"].values()), {})
    ticks = {}
    for cm, v in manual.items():
        near = [p for p in peaks if abs(p - v) <= 8]
        ticks[cm] = float(min(near, key=lambda p: abs(p - v))) if near else float(v)
    obs = []
    for cm, v in ticks.items():
        vi = int(round(v))
        if vi in edge:
            obs.append(dict(frame=name, sweep=sweep, cm=cm, u=float(edge[vi]), v=float(v)))
    x0, x1 = cfg["crop"]
    crop = im[:, x0:x1].copy()
    for v in edge:
        cv2.circle(crop, (int(round(edge[v])) - x0, v), 0, (0, 255, 0), -1)
    for p in peaks:
        vi = int(round(p))
        if vi in edge:
            x = int(round(edge[vi])) - x0
            cv2.line(crop, (x, vi), (x + 12, vi), (255, 255, 0), 1)
    for cm, v in ticks.items():
        vi = int(round(v))
        if vi in edge:
            x = int(round(edge[vi])) - x0
            cv2.line(crop, (x - 30, vi), (x + 60, vi), (0, 0, 255), 1)
            cv2.putText(crop, f"{cm} cm", (max(2, x - 60), vi + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
    crop = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(os.path.join(out_dir, f"check_{name}.png"), crop)
    sp = np.diff(sorted(peaks))
    print(f"{sweep} {name} phase {win['phase']}: edge top/bottom {edge[min(edge)]:.1f} {edge[max(edge)]:.1f}, "
          f"ticks {ticks}, mm spacing median {np.median(sp) if len(sp) else float('nan'):.1f} px, peaks {[round(p) for p in peaks]}")
    return obs, dict(sweep=sweep, phase=win["phase"], peaks=peaks, edge={str(k): v for k, v in edge.items()},
                     identity=win["note"])


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else HERE
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(HERE, "bend_ticks.json")
    bend = json.load(open(path))
    bend["obs"] = [dict(o, sweep=o.get("sweep", "sweep1")) for o in bend["obs"] if o.get("sweep", "sweep1") == "sweep1"]
    bend["detail"] = {k: dict(d, sweep=d.get("sweep", "sweep1")) for k, d in bend["detail"].items()
                      if d.get("sweep", "sweep1") == "sweep1"}
    for sweep, cfg in SWEEPS.items():
        rows = {r["name"]: r for r in json.load(open(os.path.join(HERE, sweep, "rows_matched.json")))}
        for phase, win in cfg["windows"].items():
            win["phase"] = phase
            for name in win["frames"]:
                r = rows[name]
                assert r["use"] and r["phase"] == phase, (name, r["phase"], r["use"])
                o, d = read_frame(sweep, name, win, out_dir)
                for x in o:
                    x.update(phase=phase, q=r["q"], gb=r["gb"], t_cap=r["t_cap"])
                bend["obs"] += o
                bend["detail"][name] = d
    bend["ruler_by_sweep"] = {
        "sweep1": "centre y = -0.022 (cm edge -0.0093), zero at the toe-line midpoint (00:29 capture)",
        "sweep2": "re-placed by Shawn, zero at the toe-line midpoint, side not recorded: RULER_Y fitted (prior -0.022)",
        "sweep3": "about 3 cm further left (robot +y), zero on the toe line: own RULER_Y nuisance",
        "sweep4": "about 6 cm left of sweep2 (through the middle of the bent-head picture): own RULER_Y nuisance",
    }
    json.dump(bend, open(path, "w"), indent=1)
    n = {}
    for o in bend["obs"]:
        n[o["sweep"]] = n.get(o["sweep"], 0) + (o["cm"] is not None)
    print("identified tick rows per sweep:", n, "->", path)


if __name__ == "__main__":
    main()
