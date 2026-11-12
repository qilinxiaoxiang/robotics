#!/usr/bin/env python3
"""Mac mini: how high does the swing foot lift, robot against sim, in the same walks?

From the leg encoders (as-built kinematics) and the IMU's gravity direction, the lowest sole point of each foot along
gravity is known every tick without assuming a flat foot. The lower foot is on the floor, so the height difference is
the swing foot's clearance. Per swing: the peak clearance and the swing's length. A robot that lifts its feet much less
than the sim scuffs the floor, which the rigid flat sim floor never shows.

  python3 swing_clearance.py            # all cases of turn_replay_sweep.py (robot logs + the sim's tick logs)
"""
import argparse
import collections
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import play_locate as PL  # noqa: E402  (re-executes under the sim venv if needed)

BASE = os.path.expanduser("~/sims/fall-onset-20261112")
MIN_MM = 1.5


def heights(kin, q, gb):
    f = kin.feet(q)
    g = np.asarray(gb, float)
    g = g / (np.linalg.norm(g) or 1)
    return float((f["left"][1] @ g).max()), float((f["right"][1] @ g).max())


def swings(t, dh):
    """dh = h_left - h_right in mm (+ = left foot lower = right foot in the air). Returns [(side, peak_mm, dur_s)]."""
    out, i, n = [], 0, len(dh)
    while i < n:
        s = 1 if dh[i] > MIN_MM else -1 if dh[i] < -MIN_MM else 0
        if s == 0:
            i += 1
            continue
        j = i
        while j + 1 < n and dh[j + 1] * s > MIN_MM and t[j + 1] - t[j] < 0.06:
            j += 1
        if j - i >= 3:
            out.append(("right" if s > 0 else "left", float(np.max(np.abs(dh[i:j + 1]))), float(t[j] - t[i])))
        i = j + 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conds", nargs="*", default=["hold", "turn"])
    ap.add_argument("--out", default=os.path.join(HERE, "swing-clearance.json"))
    a = ap.parse_args()
    kin = PL.Kin()
    cases = json.load(open(os.path.join(BASE, "turn-replay", "cases.json")))
    cache = {}
    res = collections.defaultdict(list)   # (source, side) -> peaks
    dur = collections.defaultdict(list)
    per_case = []
    double = collections.defaultdict(list)
    for c in cases:
        if c["log"] not in cache:
            cache[c["log"]] = dict(np.load(os.path.join(BASE, "cache", c["log"] + ".npz")))
        L = cache[c["log"]]
        t = L["t"]
        t_end = c["t0"] + (c["onset"] - 0.3 if c["fell"] else c["dur"])
        k = np.where((t >= c["t0"] + 0.6) & (t <= t_end) & np.isfinite(L["q"]).all(axis=1))[0]
        if len(k) < 30:
            continue
        hl = np.array([heights(kin, L["q"][i], L["gb"][i]) for i in k])
        dh = (hl[:, 0] - hl[:, 1]) * 1000
        sw = swings(t[k], dh)
        day = time.strftime("%m-%d", time.localtime(c["t0"]))
        for side, pk, du in sw:
            res[("robot", side)].append(pk)
            res[("robot " + day, side)].append(pk)
            res[("robot fell" if c["fell"] else "robot up", side)].append(pk)
            dur[("robot", side)].append(du)
        double[("robot")].append(float(np.mean(np.abs(dh) < MIN_MM)))
        row = dict(id=c["id"], fell=c["fell"], robot_peak_left=float(np.median([p for s, p, _ in sw if s == "left"] or [np.nan])),
                   robot_peak_right=float(np.median([p for s, p, _ in sw if s == "right"] or [np.nan])))
        for cond in a.conds:
            tl = os.path.join(BASE, "turn-replay", f"{c['id']}.{cond}.seed0.ticks.jsonl")
            if not os.path.exists(tl):
                continue
            rows = [json.loads(x) for x in open(tl)]
            rows = [r for r in rows if 3.0 + 0.6 <= r["t"] <= 3.0 + (t_end - c["t0"]) and r.get("q") and r.get("gb")]
            if len(rows) < 30:
                continue
            ts = np.array([r["t"] for r in rows])
            hs = np.array([heights(kin, r["q"], r["gb"]) for r in rows])
            dhs = (hs[:, 0] - hs[:, 1]) * 1000
            sws = swings(ts, dhs)
            for side, pk, du in sws:
                res[("sim " + cond, side)].append(pk)
                dur[("sim " + cond, side)].append(du)
            double[("sim " + cond)].append(float(np.mean(np.abs(dhs) < MIN_MM)))
            row[f"sim_{cond}_peak_left"] = float(np.median([p for s, p, _ in sws if s == "left"] or [np.nan]))
            row[f"sim_{cond}_peak_right"] = float(np.median([p for s, p, _ in sws if s == "right"] or [np.nan]))
        per_case.append(row)
    print("swing-foot peak clearance, mm (lowest sole point above the stance foot's lowest point)")
    print(f"{'source':16s} {'foot':6s} {'n':>5s}   p10   p25   p50   p75   p90   share<3mm  share<5mm")
    summary = {}
    for (src, side), v in sorted(res.items()):
        v = np.array(v)
        p = np.percentile(v, [10, 25, 50, 75, 90])
        summary[f"{src}|{side}"] = dict(n=len(v), p10=p[0], p25=p[1], p50=p[2], p75=p[3], p90=p[4],
                                        under3=float(np.mean(v < 3)), under5=float(np.mean(v < 5)))
        print(f"{src:16s} {side:6s} {len(v):5d} " + " ".join(f"{x:5.1f}" for x in p) + f"   {np.mean(v < 3):6.2f}     {np.mean(v < 5):6.2f}")
    print("\nswing duration s (median): " + ", ".join(f"{k[0]} {k[1]} {np.median(v):.2f}" for k, v in sorted(dur.items())))
    print("share of walking ticks with both feet within %.1f mm: " % MIN_MM + ", ".join(f"{k} {np.median(v):.2f}" for k, v in double.items()))
    json.dump(dict(summary=summary, per_case=per_case), open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
