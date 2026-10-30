"""Replay the 2026-10-30 01:33 pickup (log excerpt) through hold.HoldEstimator, read-only, no robot.

  python3 replay.py                       # the repo's hold.py: reproduces the logged s and the false "landed"
  python3 replay.py --hold /path/hold.py  # another hold.py, e.g. the repo's after proposed.diff is applied

Feeds the logged touch counts, touch age and summed leg current with the calibration in ~/.duck_hold.json on the A7Z
(made 2026-10-23). Rows after +2.63 s carry the leg currents the deployed behaviour produced once it handed the
authority back, so for a fixed estimator they are a harsher input than the robot would have given it.
"""
import argparse
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CAL = {"pad_lo": [624.5, 698.0, 320.5, 352.0, 474.8], "pad_hi": [1998.4, 2233.6, 1025.6, 1126.4, 1519.2],
       "grip_full_mm2": 1010.6, "legs_stand_ma": 294.0, "legs_air_ma": 138.0}
T_GRIP = 1793338402.0  # 05:33:22.0 UTC, 01:33:22 local, just before the first pad rises


def load(path):
    spec = importlib.util.spec_from_file_location("hold_under_test", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hold", default=os.path.join(HERE, "..", "hold.py"))
    ap.add_argument("--log", default=os.path.join(HERE, "log_app1030-040713_0533.jsonl"))
    ap.add_argument("--every", type=int, default=5, help="print every n-th tick after the grip")
    a = ap.parse_args()
    hold = load(a.hold)
    est = hold.HoldEstimator(CAL, kp_rl=200)
    prev, n, first_land = None, 0, None
    for line in open(a.log):
        r = json.loads(line)
        dt = 0.02 if prev is None else max(0.001, min(0.1, r["t"] - prev))
        prev = r["t"]
        est.update(dt, r["touch"], r["touch_age"], r["legs_ma"])
        if est.landed and first_land is None:
            first_land = round(r["t"] - T_GRIP, 2)
        if r["t"] < T_GRIP:
            continue
        if n % a.every == 0:
            h = r["hold"] or {}
            print(f"{r['t'] - T_GRIP:6.2f} s  logged: mode {r['mode']:<5} s {h.get('s')} landed {int(bool(h.get('landed')))}"
                  f" |action| {r['act_max']:.2f} legs {r['legs_ma']} mA tilt {r['tilt_deg']}  |  replay: s {est.s:.3f}"
                  f" airborne {int(est.airborne)} landed {int(est.landed)} kp_leg {est.gains()['left_knee']}"
                  f" e {est.e:.2f} load {None if est.load_f is None else round(est.load_f, 2)}")
        n += 1
    print(f"first 'landed' in the replay: {first_land} s after the grip "
          f"(the robot was in the hand from about +2 s to +8.6 s; logged landed at +2.77 s)")


if __name__ == "__main__":
    main()
