#!/usr/bin/env python3
"""Tilt gap across one stance: is the walking pitch gap the foot rolling from heel to toe, or something faster?

For every single-stance run of at least MIN_TICKS walking ticks on one foot, the pitch and roll tilt gap (tilt_gap.py:
measured trunk tilt minus the tilt that stance leg's encoders give with that foot flat, the log's per-foot median
removed) is binned over the run's normalised phase (0 = the foot just took the load, 1 = just before it hands over).
A foot rolling over its sole shows a sweep across the phase (the trunk pitches further than the joints say, one way at
the start and the other at the end); play or shake that comes and goes fast shows as spread inside each bin with a
flat mean.

  python3 stance_profile.py --out prof.json LOG...
"""
import argparse
import glob
import json
import os

import numpy as np
import tilt_gap as G
import play_locate as P

MIN_TICKS, BINS = 6, 5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    paths = sorted(set(p for g in a.logs for p in glob.glob(os.path.expanduser(g))))
    kin = P.Kin()
    acc = {s: [[] for _ in range(BINS)] for s in ("left", "right")}
    runs = {"left": 0, "right": 0}
    for p in paths:
        T = G.ticks(p, kin)
        med = {}
        for s in ("left", "right"):
            v = [x["gap"] for x in T if x and x["walking"] and x["stance"] == s]
            if v:
                med[s] = np.median(np.array(v), 0)
        run = []
        for x in T + [None]:
            if x and x["walking"] and x["stance"] and (not run or run[-1]["stance"] == x["stance"]):
                run.append(x)
                continue
            if len(run) >= MIN_TICKS:
                s = run[0]["stance"]
                runs[s] += 1
                n = len(run)
                for i, y in enumerate(run):
                    acc[s][min(BINS - 1, int(i / n * BINS))].append(y["gap"] - med[s])
            run = [x] if x and x["walking"] and x["stance"] else []
    res = dict(runs=runs, profile={})
    for s in ("left", "right"):
        res["profile"][s] = []
        for b in acc[s]:
            if not b:
                continue
            v = np.array(b)
            res["profile"][s].append(dict(n=len(v), pitch_mean=round(float(v[:, 1].mean()), 2),
                                          pitch_sd=round(float(v[:, 1].std()), 2),
                                          roll_mean=round(float(v[:, 0].mean()), 2), roll_sd=round(float(v[:, 0].std()), 2)))
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps(res))


if __name__ == "__main__":
    main()
