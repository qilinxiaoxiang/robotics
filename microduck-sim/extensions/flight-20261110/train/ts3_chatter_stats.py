"""Action-chatter statistics of a tick log, the same measures as a7z-20261119/an2.py, for a robot log
(walk_wired, /tmp/duck_wired_log_*.jsonl) or a simulated one (brain_sim_check.py --tick-log): rows of the policy
mode with an action.

  python3 train/ts3_chatter_stats.py <log.jsonl> [<log.jsonl> ...] [--mode walk] [--out file.json]

Per log: policy ticks, duration, tick-to-tick action jumps over 0.5 rad (count and per 10 s), median and p90 of the
largest per-tick action step, action rms, gyro rms per axis, skipped ticks (policy mode, no action), the dominant
sign-flip rate of the leg actions (flips per second of the largest-amplitude joint).
"""
import argparse
import json

import numpy as np


def stats(path, mode="walk"):
    rows = []
    for line in open(path):
        if line.startswith("{"):
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    w = [r for r in rows if r.get("mode") == mode and r.get("action") is not None]
    if len(w) < 3:
        return dict(log=path, policy_ticks=len(w))
    a = np.array([r["action"] for r in w], dtype=float)
    d = np.abs(np.diff(a, axis=0)).max(1)
    dur = float(w[-1]["t"] - w[0]["t"])
    j = int(np.argmax(a.std(0)))
    c = a[:, j] - a[:, j].mean()
    flips = int((np.sign(c[1:]) != np.sign(c[:-1])).sum())
    gy = np.array([r["gyro_body"] for r in w], dtype=float)
    return dict(log=path, policy_ticks=len(w), duration_s=round(dur, 2), jumps_over_0p5=int((d > 0.5).sum()),
                jumps_per_10s=round(float((d > 0.5).sum() / dur * 10), 1), step_median_rad=round(float(np.median(d)), 3),
                step_p90_rad=round(float(np.percentile(d, 90)), 3), action_rms_rad=round(float(np.sqrt((a ** 2).mean())), 3),
                gyro_rms=np.sqrt((gy ** 2).mean(0)).round(3).tolist(),
                skipped_ticks=sum(1 for r in rows if r.get("mode") == mode and r.get("action") is None),
                loop_hz=round((len(w) - 1) / dur, 1) if dur > 0 else None,
                busiest_joint_index=j, busiest_joint_std_rad=round(float(a[:, j].std()), 3),
                busiest_joint_flips_per_s=round(flips / dur, 1) if dur > 0 else None)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--mode", default="walk")
    ap.add_argument("--out")
    a = ap.parse_args()
    res = [stats(p, a.mode) for p in a.logs]
    for r in res:
        print(json.dumps(r))
    if a.out:
        open(a.out, "w").write(json.dumps(res, indent=1))
