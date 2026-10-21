"""Acceptance for the ankle play repair: does the body still rock with the legs frozen, does stand61 still oscillate?

Reads one walk_wired tick log (robot or brain_sim_check --tick-log) and prints two verdicts:

1. Open-loop stand (mode stand, KP 400): 1 s windows in which all ten leg encoders stay within 3 ticks and the trunk
   leans less than 8 deg; the trunk pitch range inside each. Past 8 deg the foot rocks on its toe on both days, so those
   windows say nothing about play. 2026-10-19 (stock one-piece ankle brackets): p90 0.06 deg over 421 windows (roll
   0.06). 2026-10-21 (V1.24/V1.25 two-half ankle): p90 2.2 deg, median 1.0 deg over 20 windows (roll median 0.2).
   PASS: at least 20 windows and p90 <= 0.5 deg.
2. stand61 at zero command: per run (first 0.5 s skipped) the leg actions' rms above ~2 Hz and the trunk yaw-rate rms.
   2026-10-19: 1.4-42 mrad and 5-89 mrad/s. 2026-10-21: 180-630 mrad and 1.2-3.1 rad/s at 3.5-4.5 Hz, every run fell.
   PASS: at least 10 s of stand61 in total, every run <= 60 mrad and <= 150 mrad/s.

  python3 stand_check.py /tmp/duck_wired_log_<suffix>.jsonl[.gz]
"""
import gzip, json, math, os, statistics as st, sys
import numpy as np
sys.argv, ARGS = sys.argv[:1], sys.argv[1:]
_here = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.join(_here, "churn_replay.py")
exec(open(__file__).read().split("for path in sys.argv[1:]")[0])

SWING_P90_MAX_DEG = 0.5
SWING_MIN_WINDOWS = 20
LEAN_MAX_DEG = 8.0
FAST_ACTION_MAX_MRAD = 60.0
YAW_RATE_MAX_MRAD_S = 150.0
STAND61_MIN_S = 10.0


def rows(path):
    for line in (gzip.open(path, "rt") if path.endswith(".gz") else open(path)):
        try:
            yield json.loads(line)
        except json.JSONDecodeError:  # a log cut by a reset ends mid-line
            pass


def frozen_leg_swing(path):
    S = [r for r in rows(path) if r.get("mode") == "stand" and r.get("kp") == 400 and r.get("pos_tick") and r.get("gb")
         and r.get("torque", True)]
    swings = []
    for i in range(0, len(S) - 50, 25):
        w = S[i:i + 50]
        if w[-1]["t"] - w[0]["t"] > 1.3:
            continue
        if max(max(c) - min(c) for c in zip(*[r["pos_tick"][:10] for r in w])) > 3:
            continue
        p = [math.degrees(math.atan2(r["gb"][0], -r["gb"][2])) for r in w]
        if max(abs(x) for x in p) > 40:  # lying down, not standing
            continue
        if abs(sorted(p)[len(p) // 2]) >= LEAN_MAX_DEG:  # resting on the toes: the whole foot rocks
            continue
        swings.append(max(p) - min(p))
    return swings


def stand61_runs(path):
    out = []
    for s in segments(path):
        s = s[25:]
        if len(s) < 100:
            continue
        a = np.array([r["action"] for r in s]); g = np.array([r["gyro_body"] for r in s])
        out.append(dict(seconds=round(s[-1]["t"] - s[0]["t"], 1), fast_action_mrad=round(rms_fast(a) * 1000, 1),
                        yaw_rate_mrad_s=round(float(np.std(g[:, 2])) * 1000, 1)))
    return out


if __name__ == "__main__":
    ok_all = True
    for path in ARGS:
        print(os.path.basename(path))
        sw = frozen_leg_swing(path)
        if len(sw) < SWING_MIN_WINDOWS:
            print(f"   open-loop stand, legs frozen: UNDECIDED ({len(sw)} still 1 s windows, need {SWING_MIN_WINDOWS})"); ok_all = False
        else:
            p90 = st.quantiles(sw, n=10)[-1]; ok = p90 <= SWING_P90_MAX_DEG; ok_all &= ok
            print(f"   open-loop stand, legs frozen: {'PASS' if ok else 'FAIL'} body pitch swing p90 {p90:.2f} deg, max {max(sw):.2f} deg over {len(sw)} windows (limit p90 {SWING_P90_MAX_DEG})")
        runs = stand61_runs(path)
        total = sum(r["seconds"] for r in runs)
        if total < STAND61_MIN_S:
            print(f"   stand61: UNDECIDED ({total:.1f} s of stand61, need {STAND61_MIN_S})"); ok_all = False
        else:
            bad = [r for r in runs if r["fast_action_mrad"] > FAST_ACTION_MAX_MRAD or r["yaw_rate_mrad_s"] > YAW_RATE_MAX_MRAD_S]
            ok_all &= not bad
            print(f"   stand61: {'PASS' if not bad else 'FAIL'} {len(runs)} runs, {total:.1f} s: " + json.dumps(runs))
    sys.exit(0 if ok_all else 1)
