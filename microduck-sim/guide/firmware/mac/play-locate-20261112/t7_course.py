"""T7: time course of hip roll (position and goal), roll and stance width proxy around a walk and the zero command after it.

  python t7_course.py LOG.jsonl [--bin 2.0] [--t0 EPOCH_OR_S] [--end-summary S]

Prints per time bin: mode / command, IMU roll and pitch (deg), hip roll position R, L (deg, abduction positive on both
sides), their sum (stance-width proxy), hip roll goals, and the hip roll currents when logged. With --end-summary S it
prints one line for the last S seconds (the numbers T7 compares with the robot).
"""
import argparse
import json
import math
import sys

import numpy as np

DEG = 180 / math.pi
TICK = 2 * math.pi / 4096
IR, IL = 3, 8  # servo ID order: ID4 right_hip_roll, ID9 left_hip_roll


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--bin", type=float, default=2.0)
    ap.add_argument("--from-s", type=float, default=None, help="seconds from the first row")
    ap.add_argument("--to-s", type=float, default=None)
    ap.add_argument("--end-summary", type=float, default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    rows = []
    with open(args.log) as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if "q" in r and "gb" in r:
                rows.append(r)
    t00 = rows[0]["t"]
    if args.from_s is not None:
        rows = [r for r in rows if args.from_s <= r["t"] - t00 <= (args.to_s or 1e12)]

    def summ(rs):
        gb = np.mean([r["gb"] for r in rs], axis=0)
        q = np.mean([r["q"] for r in rs], axis=0)
        g = [r["goal_tick"] for r in rs if r.get("goal_tick")]
        gr = np.mean([(x["4"] - 2048) * TICK for x in g]) * DEG if g else float("nan")
        gl = np.mean([(x["9"] - 2048) * TICK for x in g]) * DEG if g else float("nan")
        cur = np.mean([r["cur_ma"] for r in rs], axis=0) if "cur_ma" in rs[0] else None
        cmd = rs[-1].get("cmd") or {}
        return dict(mode=rs[-1].get("mode"), vx=cmd.get("vx"), roll=math.degrees(math.atan2(gb[1], -gb[2])),
                    pitch=math.degrees(math.atan2(-gb[0], -gb[2])), R=q[IR] * DEG, L=-q[IL] * DEG, gR=gr, gL=-gl,
                    cR=None if cur is None else cur[IR], cL=None if cur is None else cur[IL])

    if not args.quiet:
        print("   t_s mode    vx   roll  pitch |  posR  posL   sum | goalR goalL | mA R / L")
        b0 = rows[0]["t"]
        cur = []
        for r in rows:
            if r["t"] - b0 >= args.bin and cur:
                s = summ(cur)
                print(f"{b0 - t00:7.1f} {str(s['mode']):7s} {str(s['vx']):>4s} {s['roll']:+6.2f} {s['pitch']:+6.2f} | {s['R']:5.2f} {s['L']:5.2f} "
                      f"{s['R'] + s['L']:5.2f} | {s['gR']:5.2f} {s['gL']:5.2f} | "
                      f"{'' if s['cR'] is None else format(s['cR'], '+.0f') + ' / ' + format(s['cL'], '+.0f')}")
                b0, cur = r["t"], []
            cur.append(r)
    if args.end_summary:
        t1 = rows[-1]["t"]
        s = summ([r for r in rows if r["t"] >= t1 - args.end_summary])
        print(f"END {args.log.split('/')[-1]:28s} roll {s['roll']:+5.2f} pitch {s['pitch']:+5.2f} hip roll pos R {s['R']:5.2f} L {s['L']:5.2f} "
              f"sum {s['R'] + s['L']:5.2f} goal R {s['gR']:5.2f} L {s['gL']:5.2f}")


if __name__ == "__main__":
    main()
