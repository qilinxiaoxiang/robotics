"""Real robot reference for closed_loop.py, from the brain log slice of the scan session (copied off the A7Z with tail).

    python3 real_windows.py <brain_slice.jsonl>   writes real_windows.json

Per held window: mean joints and body gravity as the brain saw them (trimmed), servo position minus goal in model rad,
the commands seen, read-drop fraction, supply. Prints the command timeline, which closed_loop.py replays.
"""
import datetime as dt
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "guide", "firmware", "pi"))
from joint_signs import MOTOR_SIGN  # noqa: E402

ID_NAMES = ["right_ankle", "right_knee", "right_hip_pitch", "right_hip_roll", "right_hip_yaw", "left_ankle", "left_knee",
            "left_hip_pitch", "left_hip_roll", "left_hip_yaw", "head_pitch", "neck_pitch", "head_yaw", "head_roll"]
TICK = 2 * math.pi / 4096
WINDOWS = {"stand1": ("20:38:00", "20:39:40"), "bend": ("20:40:30", "20:41:50"), "stand2": ("20:43:30", "20:47:20")}


def servo_volts(w):
    """Median of the servo supply readings of the window, whatever shape the log holds (number or per-id list)."""
    vals = []
    for r in w:
        v = r.get("servo_v")
        vals += [x for x in (v.values() if isinstance(v, dict) else v if isinstance(v, list) else [v]) if isinstance(x, (int, float))]
    return float(np.median(vals)) if vals else None


def main(path):
    rows = []
    for line in open(path):
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    day = dt.datetime.fromtimestamp(rows[0]["t"]).date()
    prev = None
    print("command timeline")
    for r in rows:
        k = json.dumps(r.get("cmd"), sort_keys=True)
        if k != prev:
            print(dt.datetime.fromtimestamp(r["t"]).strftime("%H:%M:%S.%f")[:10], r.get("mode"), k[:130], "kp", r.get("kp"))
            prev = k
    out = {}
    for name, (a, b) in WINDOWS.items():
        ta, tb = (dt.datetime.combine(day, dt.time.fromisoformat(x)).timestamp() for x in (a, b))
        w = [r for r in rows if ta <= r["t"] < tb]
        q = np.array([r["q"] for r in w], float)
        gb = np.array([r["gb"] for r in w], float)
        err = []
        for r in w:
            if not r.get("goal_tick"):
                continue
            err.append([(r["pos_tick"][i] - r["goal_tick"][str(i + 1)]) * TICK * MOTOR_SIGN[n] for i, n in enumerate(ID_NAMES)])
        err = np.array(err, float)
        out[name] = dict(n=len(w), start=a, end=b, q=dict(zip(ID_NAMES, np.round(q.mean(0), 4).tolist())),
                         q_range=dict(zip(ID_NAMES, np.round(np.ptp(q, axis=0), 4).tolist())),
                         err=dict(zip(ID_NAMES, np.round(np.median(err, axis=0), 4).tolist())),
                         gb=np.round(gb.mean(0), 4).tolist(), trunk_deg=round(math.degrees(math.asin(gb[:, 0].mean())), 2),
                         cmds=sorted({json.dumps(r.get("cmd"), sort_keys=True) for r in w})[:6],
                         modes=sorted({str(r.get("mode")) for r in w}), kp=sorted({str(r.get("kp")) for r in w}),
                         drop=round(1 - float(np.mean([bool(r.get("fresh")) for r in w])), 3),
                         battery_dv=float(np.median([r["battery_dv"] for r in w if r.get("battery_dv")])),
                         servo_v=servo_volts(w))
        print(name, {k: out[name][k] for k in ("n", "trunk_deg", "kp", "drop", "battery_dv", "servo_v", "modes")})
        print("  neck", out[name]["q"]["neck_pitch"], "head", out[name]["q"]["head_pitch"], "cmds", out[name]["cmds"][:3])
    json.dump(out, open(os.path.join(HERE, "real_windows.json"), "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
