#!/usr/bin/env python3
"""Trunk swing with every leg encoder still (stand_check.py check 1, widened to any torque-on mode).

0.5 s windows in which all ten leg encoders stay within 3 ticks (0.26 deg) and the trunk leans under 8 deg: the
trunk's pitch and roll range inside each. A rigid robot cannot rotate its trunk with the leg joints still, so this
range is play past the encoders (horn, bracket, foot) or the foot rocking on the floor. References from
stand_check.py: 2026-10-19 one-piece ankle p90 0.06 deg; 2026-10-21 two-half ankle p90 2.2 deg, median 1.0.

  python3 frozen_swing.py LOG...      # prints one line per log and the pooled percentiles
"""
import glob
import json
import math
import os
import sys

WIN, STEP, STILL_TICKS, LEAN_MAX = 25, 12, 3, 8.0


def pitch_roll(g):
    return math.degrees(math.atan2(g[0], -g[2])), math.degrees(math.atan2(-g[1], -g[2]))


def windows(path):
    R = []
    for line in open(path):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not r.get("torque") or not r.get("imu_valid") or not r.get("pos_tick") or not r.get("gb"):
            continue
        if None in r["pos_tick"][:10]:
            continue
        R.append((r["t"], r["mode"], r["pos_tick"][:10], r["gb"]))
    out = []
    for i in range(0, len(R) - WIN, STEP):
        w = R[i:i + WIN]
        if w[-1][0] - w[0][0] > 0.65:
            continue
        if max(max(c) - min(c) for c in zip(*[x[2] for x in w])) > STILL_TICKS:
            continue
        pr = [pitch_roll(x[3]) for x in w]
        p, r = [a for a, _ in pr], [b for _, b in pr]
        if abs(sorted(p)[len(p) // 2]) >= LEAN_MAX or abs(sorted(r)[len(r) // 2]) >= LEAN_MAX:
            continue
        out.append(dict(t=w[0][0], mode=w[0][1], pitch=max(p) - min(p), roll=max(r) - min(r)))
    return out


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))] if v else None


def main():
    paths = sorted(set(p for g in sys.argv[1:] for p in glob.glob(os.path.expanduser(g))))
    pooled = []
    for p in paths:
        w = windows(p)
        pooled += w
        if w:
            print(f"{os.path.basename(p)}: {len(w)} windows, pitch median {pct([x['pitch'] for x in w], .5):.2f} "
                  f"p90 {pct([x['pitch'] for x in w], .9):.2f}, roll median {pct([x['roll'] for x in w], .5):.2f} "
                  f"p90 {pct([x['roll'] for x in w], .9):.2f} deg; modes {sorted(set(x['mode'] for x in w))}")
    if pooled:
        print(f"POOLED {len(pooled)} windows: pitch median {pct([x['pitch'] for x in pooled], .5):.2f} p90 "
              f"{pct([x['pitch'] for x in pooled], .9):.2f}; roll median {pct([x['roll'] for x in pooled], .5):.2f} p90 "
              f"{pct([x['roll'] for x in pooled], .9):.2f} deg")


if __name__ == "__main__":
    main()
