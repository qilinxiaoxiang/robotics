#!/usr/bin/env python3
"""Mac mini: turn the robot brain logs (~/duck-walks/raw/*.jsonl) and sim tick logs into compact .npz files so
the fall-onset and servo-response analyses load in seconds instead of re-parsing 1.6 GB of JSON.

  python3 compact_logs.py --out ~/sims/fall-onset-20261112/cache ~/duck-walks/raw/duck_wired_log_app*.jsonl
"""
import argparse
import concurrent.futures
import json
import os

import numpy as np

MODES = ["monitor", "stand", "walk", "sit", "seepick", "groundpick", "kick", "other"]
N = 14


def vec(v, n):
    if v is None:
        return [np.nan] * n
    if isinstance(v, dict):
        return [float(v.get(str(i + 1), np.nan)) for i in range(n)]
    v = list(v)
    return [np.nan if x is None else float(x) for x in v[:n]] + [np.nan] * (n - len(v))


def compact(path, out_dir):
    out = os.path.join(out_dir, os.path.basename(path).replace(".jsonl", ".npz"))
    if os.path.exists(out) and os.path.getmtime(out) > os.path.getmtime(path):
        return out, -1
    cols = {k: [] for k in ("t", "mode", "policy", "vx", "vy", "vth", "cmdmode", "gb", "gyro", "q", "dq", "action",
                            "action_raw", "goal", "pos", "cur", "loop_ms", "read_ms", "joint_age", "imu_age",
                            "fresh", "nmiss", "kp", "batt", "turn", "trim", "hold_s", "imu_seq", "torque", "legs_ma")}
    pol = {"walk": 1, "stand": 2}
    with open(path) as h:
        for line in h:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if "t" not in r or "q" not in r:
                continue
            m = r.get("mode")
            cols["t"].append(r["t"])
            cols["mode"].append(MODES.index(m) if m in MODES else len(MODES) - 1)
            cols["policy"].append(pol.get(r.get("policy"), 0))
            c = r.get("cmd") or {}
            cols["vx"].append(float(c.get("vx") or 0))
            cols["vy"].append(float(c.get("vy") or 0))
            cols["vth"].append(float(c.get("vtheta") or 0))
            cm = c.get("mode")
            cols["cmdmode"].append(MODES.index(cm) if cm in MODES else len(MODES) - 1)
            cols["gb"].append(vec(r.get("gb"), 3))
            cols["gyro"].append(vec(r.get("gyro_body"), 3))
            cols["q"].append(vec(r.get("q"), N))
            cols["dq"].append(vec(r.get("dq"), N))
            cols["action"].append(vec(r.get("action"), N))
            cols["action_raw"].append(vec(r.get("action_raw"), N))
            cols["goal"].append(vec(r.get("goal_tick"), N))
            cols["pos"].append(vec(r.get("pos_tick"), N))
            cols["cur"].append(vec(r.get("cur_ma"), N))
            for k, f in (("loop_ms", "loop_ms"), ("read_ms", "read_ms"), ("joint_age", "joint_age"),
                         ("imu_age", "imu_age"), ("kp", "kp"), ("batt", "battery_dv"), ("turn", "turn"),
                         ("trim", "yaw_trim"), ("hold_s", "hold_s"), ("imu_seq", "imu_seq"), ("legs_ma", "legs_ma")):
                v = r.get(f)
                cols[k].append(float(v) if isinstance(v, (int, float)) else np.nan)
            cols["fresh"].append(bool(r.get("fresh", True)))
            cols["nmiss"].append(len(r.get("missing") or []))
            cols["torque"].append(bool(r.get("torque", True)))
    arr = {k: np.asarray(v, dtype=np.float32 if k != "t" else np.float64) for k, v in cols.items()}
    np.savez_compressed(out, **arr)
    return out, len(arr["t"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("logs", nargs="+")
    a = ap.parse_args()
    out = os.path.expanduser(a.out)
    os.makedirs(out, exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(a.jobs) as ex:
        for o, n in ex.map(compact, a.logs, [out] * len(a.logs)):
            print(os.path.basename(o), n, flush=True)


if __name__ == "__main__":
    main()
