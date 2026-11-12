#!/usr/bin/env python3
"""Mac mini: tick-level trace around a robot fall (from the compact logs and turn_replay_sweep.py's cases.json).

  python3 fall_trace.py [CASE_ID_SUBSTRING ...] [--back 2.2] [--fwd 0.6] [--step 2]
Servo order: 1-5 right ankle, knee, hip pitch, hip roll, hip yaw; 6-10 left the same; 11-14 neck pitch, head pitch,
head yaw, head roll.
"""
import argparse
import json
import os

import numpy as np

C = os.path.expanduser("~/sims/fall-onset-20261112/cache/")
CASES = os.path.expanduser("~/sims/fall-onset-20261112/turn-replay/cases.json")


def show(c, back, fwd, step):
    L = dict(np.load(C + c["log"] + ".npz"))
    t = L["t"]
    on = c["t0"] + (c["onset"] if c["onset"] is not None else c["dur"])
    g = L["gb"] / np.linalg.norm(L["gb"], axis=1, keepdims=True)
    pitch = np.degrees(np.arctan2(-g[:, 0], -g[:, 2]))
    roll = np.degrees(np.arctan2(g[:, 1], -g[:, 2]))
    print(f"\n### {c['id']} fell={c['fell']} onset {c['onset']} s, turn_absmax {c['turn_absmax']:.2f}")
    print(" t-on   vx  turn | pitch  roll |   gx    gy    gz | cur R: ank  knee   hp    hr    hy | L: ank  knee   hp    hr    hy |"
          " err(tick) Rhy  Lhy Rank Lank | max|act| loop miss")
    i0, i1 = np.searchsorted(t, on - back), np.searchsorted(t, on + fwd)
    for i in range(i0, i1, step):
        k = slice(i, i + step)
        cur = np.nanmean(L["cur"][k], axis=0)
        err = np.nanmean(L["goal"][k] - L["pos"][k], axis=0)
        act = L["action"][k]
        ma = np.nanmax(np.abs(act)) if np.isfinite(act).any() else float("nan")
        print(f"{t[i] - on:6.2f} {L['vx'][i]:4.2f} {np.nan_to_num(L['turn'][i]):5.2f} | {pitch[i]:5.1f} {roll[i]:5.1f} |"
              f" {L['gyro'][i, 0]:5.2f} {L['gyro'][i, 1]:5.2f} {L['gyro'][i, 2]:5.2f} |      "
              + " ".join(f"{cur[j]:5.0f}" for j in range(5)) + " |   " + " ".join(f"{cur[j]:5.0f}" for j in range(5, 10))
              + f" |          {err[4]:4.0f} {err[9]:4.0f} {err[0]:4.0f} {err[5]:4.0f} | {ma:5.2f} {np.nanmax(L['loop_ms'][k]):5.1f} {int(np.sum(~L['fresh'][k].astype(bool)))}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--back", type=float, default=2.2)
    ap.add_argument("--fwd", type=float, default=0.6)
    ap.add_argument("--step", type=int, default=2)
    a = ap.parse_args()
    cases = json.load(open(CASES))
    for c in cases:
        if (a.ids and any(s in c["id"] for s in a.ids)) or (not a.ids and c["fell"]):
            show(c, a.back, a.fwd, a.step)


if __name__ == "__main__":
    main()
