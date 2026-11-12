#!/usr/bin/env python3
"""Tilt gap: the trunk tilt the IMU measures minus the tilt the stance leg's encoders allow with that foot flat.

Per walking tick with one foot carrying the robot (its sole lowest along gravity by STANCE_MM), the sole normal of
that foot, from the as-built model's forward kinematics at the logged joint angles, is where gravity would point in
the trunk frame if the foot were flat and every joint were rigid past its encoder. The angle between it and the
measured gravity (gb), split into pitch (about the trunk y axis) and roll (x), is the tilt gap. Its constant part is
the sole's own angle and the IMU trim; its tick-to-tick change is trunk motion the encoders did not make: play past
an encoder (horn, screws, bracket), the foot rocking or slipping, or IMU mount motion. Rates are never differentiated
from encoder angles here (quantised, dropped and delayed reads make that noisy).

For each leg joint the script also takes the ticks where that joint's load (goal minus position) changes sign while
its foot carries the robot and compares the gap's tick-to-tick change there with that foot's other stance ticks.

  python3 tilt_gap.py --out robot.json <robot logs>       # robot
  python3 tilt_gap.py --out sim.json <sim tick logs>      # same statistics in the sim (no play there)
"""
import argparse
import collections
import glob
import json
import math
import os
import sys

import play_locate as P  # re-executes under the sim venv; model loading and log reading live there
import numpy as np  # noqa: E402

STANCE_MM = 4.0
LOAD_TICKS = 2
LEG = P.LEG


def sole_normal(pts):
    c = pts - pts.mean(0)
    n = np.linalg.svd(c, full_matrices=False)[2][-1]
    return n if n @ (pts.mean(0)) < 0 or n[2] < 0 else -n


def signed_gap(n, g):
    """Small-angle rotation (trunk frame) that takes the predicted gravity n onto the measured g: x = roll, y = pitch."""
    v = np.cross(n, g)
    return np.degrees(v[:2])


def ticks(path, kin):
    out, prev_t = [], None
    for r in P.rows(path):
        f = kin.feet(r["q"])
        g = np.array(r["gb"], float)
        g /= np.linalg.norm(g) or 1
        low = {s: float((f[s][1] @ g).max()) for s in f}
        dh = (low["left"] - low["right"]) * 1000
        stance = "left" if dh > STANCE_MM else "right" if dh < -STANCE_MM else None
        walking = r["mode"] == "walk" and (any(float(r["cmd"].get(k, 0) or 0) for k in ("vx", "vy", "vtheta"))
                                           if r["cmd"] is not None else r["policy"] == "walk")
        load = None
        if r["pos"] and r["goal"]:
            gl = r["goal"]
            load = {n: gl[str(i)] - r["pos"][k] for k, (i, n) in enumerate(zip(P.wb.IDS, P.wb.NAMES))
                    if gl.get(str(i)) is not None and r["pos"][k] is not None}
        gap = signed_gap(sole_normal(f[stance][1]), g) if stance else None
        if prev_t is not None and r["t"] - prev_t > 0.06:
            out.append(None)
        prev_t = r["t"]
        out.append(dict(t=r["t"], stance=stance, walking=walking, gap=gap, load=load))
    return out


def analyse(paths, kin):
    by_side = collections.defaultdict(lambda: dict(gap=[], jump=[]))
    joint = collections.defaultdict(lambda: dict(rev=[], base=[]))
    per_log = {}
    for p in paths:
        T = ticks(p, kin)
        pj = collections.defaultdict(lambda: dict(rev=[], base=[]))
        side_gaps = collections.defaultdict(list)
        for x in T:
            if x and x["walking"] and x["stance"]:
                side_gaps[x["stance"]].append(x["gap"])
        med = {s: np.median(np.array(v), 0) for s, v in side_gaps.items() if v}
        for a, b in zip(T, T[1:]):
            if not a or not b or not (a["walking"] and b["walking"]) or not a["stance"] or a["stance"] != b["stance"]:
                continue
            s = a["stance"]
            jump = b["gap"] - a["gap"]
            by_side[s]["gap"].append(b["gap"] - med[s])
            by_side[s]["jump"].append(jump)
            mag = float(np.linalg.norm(jump))
            if not a["load"] or not b["load"]:
                continue
            for jn in LEG:
                n = f"{s}_{jn}"
                l0, l1 = a["load"].get(n), b["load"].get(n)
                if l0 is None or l1 is None:
                    continue
                rev = (l0 >= LOAD_TICKS and l1 <= -LOAD_TICKS) or (l0 <= -LOAD_TICKS and l1 >= LOAD_TICKS)
                for d in (joint[n], pj[n]):
                    d["rev" if rev else "base"].append(mag)
        per_log[os.path.basename(p)] = {k: P.ratio(v) for k, v in sorted(pj.items())}
    sides = {}
    for s, v in by_side.items():
        g, j = np.array(v["gap"]), np.array(v["jump"])
        if len(g) < 30:
            continue
        sides[s] = dict(ticks=len(g),
                        gap_sd_deg=dict(roll=round(float(g[:, 0].std()), 2), pitch=round(float(g[:, 1].std()), 2)),
                        jump_rms_deg=dict(roll=round(float(np.sqrt((j[:, 0] ** 2).mean())), 2),
                                          pitch=round(float(np.sqrt((j[:, 1] ** 2).mean())), 2)),
                        jump_p90_deg=round(float(np.percentile(np.linalg.norm(j, axis=1), 90)), 2))
    return dict(sides=sides, joints={k: P.ratio(v) for k, v in sorted(joint.items())}, per_log=per_log)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    paths = sorted(set(p for g in a.logs for p in glob.glob(os.path.expanduser(g))))
    res = analyse(paths, P.Kin())
    res["logs"] = [os.path.basename(p) for p in paths]
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps(dict(sides=res["sides"], joints={k: (v["reversals"], v.get("ratio")) for k, v in res["joints"].items()})))


if __name__ == "__main__":
    main()
