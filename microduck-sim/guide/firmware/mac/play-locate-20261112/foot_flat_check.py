#!/usr/bin/env python3
"""Mac mini: does one leg carry an angle its encoders do not see? Measured at quiet stand, per log, in time order.

Standing still, each sole lies flat on the floor. Gravity is known in the trunk frame from the IMU, and the leg
encoders give each foot's rotation against the trunk (as-built kinematics), so gravity expressed in each foot's own
frame must be the same constant vector at every stand, whatever the pose: the sole's "down". Any change of that vector
for one foot between two days is rotation inside that leg that its five encoders did not report: a link refitted at
another angle on its horn, a horn that slipped, a bracket that moved. Pitch-axis joints (hip pitch, knee, ankle) show
in the foot's pitch component, hip roll in its roll component. The sim's stand gives the reference vector.

  python3 foot_flat_check.py [--sim TICKLOG]
"""
import argparse
import glob
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import play_locate as PL  # noqa: E402

BASE = os.path.expanduser("~/sims/fall-onset-20261112")


NREF = {}


def foot_down(kin, q, gb):
    """Per foot: the rotation (deg, about the trunk's pitch axis y and roll axis x) between gravity as the IMU reads it
    and gravity as the leg encoders predict it with that sole flat (the sim's sole-down vector NREF); and dh in mm.
    Before NREF is set it returns gravity in each foot frame, to build the reference."""
    f = kin.feet(q)
    g = np.asarray(gb, float)
    g = g / (np.linalg.norm(g) or 1)
    dh = (float((f["left"][1] @ g).max()) - float((f["right"][1] @ g).max())) * 1000
    out = {}
    for s in ("left", "right"):
        if s not in NREF:
            out[s] = tuple(f[s][0].T @ g)
        else:
            w = np.degrees(np.cross(f[s][0] @ NREF[s], g))
            out[s] = (float(w[1]), float(w[0]))
    return out["left"], out["right"], dh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", default=None)
    ap.add_argument("--out", default=os.path.join(HERE, "foot-flat-check.json"))
    a = ap.parse_args()
    kin = PL.Kin()
    ref = None
    sim = a.sim or sorted(glob.glob(os.path.join(BASE, "turn-replay", "*.hold.seed0.ticks.jsonl")))[0]
    rows = [json.loads(x) for x in open(sim)]
    st = [r for r in rows if 1.5 <= r["t"] <= 2.9 and r.get("q") and r.get("gb")]
    raw = [foot_down(kin, r["q"], r["gb"]) for r in st]
    for k, s_ in enumerate(("left", "right")):
        n = np.median(np.array([x[k] for x in raw]), axis=0)
        NREF[s_] = n / np.linalg.norm(n)
    v = np.array([np.r_[x[0], x[1], x[2]] for x in (foot_down(kin, r["q"], r["gb"]) for r in st)])
    ref = np.median(v, axis=0)
    print(f"sim stand check (should be 0): left pitch {ref[0]:+.2f} roll {ref[1]:+.2f}, right pitch {ref[2]:+.2f} roll {ref[3]:+.2f} deg, dh {ref[4]:+.2f} mm")
    ref = np.zeros(5)
    print("\nrobot at quiet stand, minus the sim reference (0 = that foot is flat by its encoders):")
    print("log                when          n  |  LEFT pitch  roll  | RIGHT pitch  roll | R-L pitch | dh mm | spread(p10..p90) L pitch, R pitch")
    out = []
    files = sorted(glob.glob(os.path.join(BASE, "cache", "duck_wired_log_*.npz")), key=lambda p: float(np.load(p)["t"][:1].sum()))
    for f in files:
        L = dict(np.load(f))
        t = L["t"]
        if len(t) < 500:
            continue
        g = L["gb"] / np.maximum(np.linalg.norm(L["gb"], axis=1, keepdims=True), 1e-9)
        tilt = np.degrees(np.arccos(np.clip(-g[:, 2], -1, 1)))
        gy = np.linalg.norm(L["gyro"], axis=1)
        still = np.r_[True, np.max(np.abs(np.diff(L["pos"][:, :10], axis=0)), axis=1) <= 2]
        quiet = (L["torque"] > 0) & ((L["mode"] == 2) | (L["mode"] == 1)) & (np.abs(L["vx"]) < 1e-3) & (np.abs(L["vth"]) < 1e-3) \
            & (gy < 0.05) & still & (tilt < 12) & np.isfinite(L["q"][:, :10]).all(axis=1) & (np.nan_to_num(L["hold_s"], nan=1.0) > 0.99) \
            & (L["policy"] > 0) & (np.abs(L["q"][:, 1]) < 0.35) & (np.abs(L["q"][:, 6]) < 0.35)  # standing, not bent or seated
        idx = np.where(quiet)[0]
        if len(idx) < 150:
            continue
        # separate stands: quiet runs at least 1 s long, one sample per run (its median), so one long stand is one vote
        runs = np.split(idx, np.where(np.diff(idx) > 5)[0] + 1)
        runs = [r for r in runs if len(r) >= 50]
        if len(runs) < 2:
            continue
        nb = max(1, int((t[runs[-1][0]] - t[runs[0][0]]) // 1500) + 1)
        for blk in np.array_split(np.arange(len(runs)), nb):
            if len(blk) < 2:
                continue
            vals = []
            for ri in blk:
                r = runs[ri][:: max(1, len(runs[ri]) // 10)]
                vv = np.array([np.r_[foot_down(kin, L["q"][i], L["gb"][i])[0], foot_down(kin, L["q"][i], L["gb"][i])[1], foot_down(kin, L["q"][i], L["gb"][i])[2]] for i in r])
                vals.append(np.median(vv, axis=0) - ref)
            vals = np.array(vals)
            m = np.median(vals, axis=0)
            lo, hi = np.percentile(vals, 10, axis=0), np.percentile(vals, 90, axis=0)
            when = time.strftime("%m-%d %H:%M", time.localtime(t[runs[blk[0]][0]]))
            print(f"{os.path.basename(f)[15:-4]:18s} {when} {len(blk):4d}  |      {m[0]:+5.1f} {m[1]:+5.1f}  |       {m[2]:+5.1f} {m[3]:+5.1f} |   {m[2] - m[0]:+5.1f}   | {m[4]:+5.1f} |"
                  f"   {lo[0]:+.1f}..{hi[0]:+.1f}   {lo[2]:+.1f}..{hi[2]:+.1f}")
            out.append(dict(log=os.path.basename(f)[:-4], when=when, stands=int(len(blk)), left_pitch=float(m[0]), left_roll=float(m[1]),
                            right_pitch=float(m[2]), right_roll=float(m[3]), dh_mm=float(m[4])))
    json.dump(dict(sim_reference=ref.tolist(), rows=out), open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
