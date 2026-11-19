"""Servo response per joint from a tick log (robot walk_wired log or brain_sim_check --tick-log), policy-mode rows:
how much of the goal error a servo closes in one control tick, and how strongly its position follows the goal.

  python3 train/ts3_servo_response.py <log.jsonl> [...] [--out file.json]

Per joint (servo id order of the log): std of the goal and of the position (ticks, 4096 per turn), the gain of
position against the goal one tick earlier (least squares on the mean-removed series: 1 = the joint follows the goal
fully within a tick, 0 = it does not move), and alpha = least-squares slope of (pos[t+1] - pos[t]) on
(goal[t] - pos[t]), the share of the error closed per tick. Joints whose goal std is under 5 ticks are left out
(nothing to fit). Same code for both worlds, so the numbers compare directly when the excitation is similar.
"""
import argparse
import json

import numpy as np


def response(path, mode="walk"):
    rows = []
    for line in open(path):
        if line.startswith("{"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("mode") == mode and r.get("goal_tick") and r.get("pos_tick") is not None:
                rows.append(r)
    ids = sorted(rows[0]["goal_tick"], key=int)
    goal = np.array([[r["goal_tick"][i] for i in ids] for r in rows], dtype=float)
    pos = np.array([list(r["pos_tick"])[:len(ids)] for r in rows], dtype=float)
    t = np.array([r["t"] for r in rows])
    ok = np.diff(t) < 0.035  # consecutive ticks only
    out = {}
    for k, i in enumerate(ids):
        g, p = goal[:, k], pos[:, k]
        if g.std() < 5:
            continue
        e, v = (g[:-1] - p[:-1])[ok], (p[1:] - p[:-1])[ok]
        gc, pc = (g[:-1] - g.mean())[ok], (p[1:] - p.mean())[ok]
        out[i] = dict(goal_std=round(float(g.std()), 1), pos_std=round(float(p.std()), 1),
                      follow_gain=round(float((gc * pc).sum() / (gc * gc).sum()), 3),
                      alpha=round(float((e * v).sum() / (e * e).sum()), 3),
                      err_rms=round(float(np.sqrt((e ** 2).mean())), 1), kp=rows[0].get("kp"))
    return dict(log=path, ticks=len(rows), joints=out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--out")
    a = ap.parse_args()
    res = [response(p) for p in a.logs]
    for r in res:
        print(r["log"], r["ticks"])
        for i, v in r["joints"].items():
            print("  id", i, v)
    if a.out:
        open(a.out, "w").write(json.dumps(res, indent=1))
