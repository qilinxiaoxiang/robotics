#!/usr/bin/env python3
"""Fit the duck's first look from its own experience: every call the camera later confirmed (bearing_seen) pairs the
heard bearing (CallLocaliser, three microphones inside the head) with the true bearing of the caller. Writes
bearing_prior.json, which namecall.py reads for the take (--bearing-prior).

2026-10-30 19:48, 15 pairs: the heard side was right 15 of 15 times, the heard magnitude carried no information
(folded |heard| against true |bearing|: no correlation; readings of 100-176 deg came from callers 13-51 deg in
front). So the prior is: look to the heard side by the median true |bearing| (about 35 deg) and let the camera take
over; a body turn still waits for the front search to fail. Refit as labels accumulate (the pet learns from its
life, not from a foam gasket):

  ssh a7z 'cat ~/duck-logs/namecall_*.jsonl' | grep -h '"call"\\|"bearing_seen"' > /tmp/nc.jsonl
  python3 fit_bearing.py /tmp/nc.jsonl [more.jsonl ...] [--out bearing_prior.json]
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MIN_PAIRS = 8


def pairs_from(paths):
    rows = []
    for p in paths:
        for line in open(p):
            if line.startswith("{"):
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    calls = {r["t"]: r for r in rows if r.get("kind") == "call"}
    out = []
    for r in rows:
        if r.get("kind") != "bearing_seen" or r["t"] not in calls:
            continue
        c = calls[r["t"]]
        heard = math.radians(c["az_deg"]) + c.get("head_yaw_now", 0.0)      # rest frame, as respond() uses it
        heard = (heard + math.pi) % (2 * math.pi) - math.pi
        out.append(dict(t=r["t"], heard_deg=round(math.degrees(heard), 1), true_deg=r["bearing_deg"], source=r["source"],
                        margin=c.get("margin"), srp=c.get("srp")))
    return out


def fit(pairs):
    h = np.array([p["heard_deg"] for p in pairs])
    t = np.array([p["true_deg"] for p in pairs])
    side_ok = int(np.sum(np.sign(h) == np.sign(t)))
    folded = np.where(np.abs(h) <= 90, np.abs(h), 180 - np.abs(h))
    corr = float(np.corrcoef(folded, np.abs(t))[0, 1]) if len(t) > 2 else float("nan")
    return dict(made=time.strftime("%Y-%m-%d %H:%M"), n=len(pairs), side_correct=side_ok,
                look_deg=round(float(np.median(np.abs(t))), 1), true_abs_range_deg=[round(float(np.abs(t).min()), 1), round(float(np.abs(t).max()), 1)],
                folded_magnitude_corr=round(corr, 2), pairs=pairs,
                rule="look side * look_deg; the heard magnitude is ignored while folded_magnitude_corr < 0.5")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--out", default=os.path.join(HERE, "bearing_prior.json"))
    a = ap.parse_args()
    pairs = pairs_from(a.logs)
    if len(pairs) < MIN_PAIRS:
        print(f"only {len(pairs)} pairs, need {MIN_PAIRS}; nothing written")
        return 1
    rep = fit(pairs)
    json.dump(rep, open(a.out, "w"), indent=1)
    print(f"{rep['n']} pairs: side right {rep['side_correct']}/{rep['n']}, folded-magnitude corr {rep['folded_magnitude_corr']}, "
          f"look {rep['look_deg']} deg (true |bearing| {rep['true_abs_range_deg']}) -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
