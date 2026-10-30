"""Replay the 2026-10-30 02:15 lift (run holdfix2: regrip in the air at 02:15:45, set down and let go at 02:15:50)
through hold.HoldEstimator, read-only, no robot. Feeds the logged touch counts, touch age, summed leg current and
|gyro_body| with the A7Z calibration (made 2026-10-23).

From 02:15:45.24 to 02:15:48.3 the logged leg current and gyro come from walk61 flailing in the hand after the old
estimator ended the lift; a held lift (s 0, kp 80) draws 101-125 mA there. --flail-ma replaces the leg current in that
window with that in-air level (default 119 mA, the run's median in the air); --flail-ma 0 keeps the logged values.

  python3 regrip_replay.py <tick log .jsonl> [--hold /path/hold.py] [--flail-ma 119]
"""
import argparse
import importlib.util
import json
import math
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CAL = {"pad_lo": [624.5, 698.0, 320.5, 352.0, 474.8], "pad_hi": [1998.4, 2233.6, 1025.6, 1126.4, 1519.2],
       "grip_full_mm2": 1010.6, "legs_stand_ma": 294.0, "legs_air_ma": 138.0}
FLAIL = (1793340945.24, 1793340948.3)
SHOW = (1793340944.9, 1793340951.0)


def load(path):
    spec = importlib.util.spec_from_file_location("hold_under_test", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--hold", default=os.path.join(HERE, "..", "hold.py"))
    ap.add_argument("--flail-ma", type=float, default=119.0)
    a = ap.parse_args()
    hold = load(a.hold)
    est = hold.HoldEstimator(CAL, kp_rl=200)
    prev, last_key, last_print = None, None, 0.0
    for line in open(a.log):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        t = r.get("t")
        if t is None or r.get("hold") is None:
            continue
        dt = 0.02 if prev is None else max(0.001, min(0.1, t - prev))
        prev = t
        ma = r.get("legs_ma")
        if a.flail_ma and FLAIL[0] <= t <= FLAIL[1]:
            ma = a.flail_ma
        g = r.get("gyro_body")
        w = math.sqrt(sum(v * v for v in g)) if g else None
        est.update(dt, r.get("touch"), r.get("touch_age"), ma, gyro=w)
        if not SHOW[0] <= t <= SHOW[1]:
            continue
        key = (est.airborne, est.landed, round(est.s, 1))
        if key != last_key or t - last_print >= 0.25:
            h = r["hold"]
            print(f"{time.strftime('%H:%M:%S', time.localtime(t))}.{int(t % 1 * 100):02d}  logged s {h['s']:.2f} "
                  f"kp {h['kp_leg']}  |  replay s {est.s:.2f} kp {est.gains()['left_knee']} airborne {int(est.airborne)}"
                  f" landed {int(est.landed)} cov {est.cov:.2f} e {est.e:.2f} gap {est.gap_s:.2f} still {est.still_s:.2f}"
                  f" |w| {w if w is None else round(w, 2)}")
            last_key, last_print = key, t


if __name__ == "__main__":
    main()
