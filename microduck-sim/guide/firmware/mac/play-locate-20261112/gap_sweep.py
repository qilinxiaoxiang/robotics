#!/usr/bin/env python3
"""Which hardware effect closes the sim-to-robot gap? (2026-11-12, Shawn: bring servo deadband, play, the head's wobble
and COM sway into the sim; what cannot be simulated cannot be closed.)

The gap, from the scorecard (`~/duck-walks/scorecard-auto.json`, robot walks of 11-02..11-06 replayed in the as-built
sim): the robot fell in 36 replays where the sim stayed up (5 the other way round), and its trunk jitter (std of the
tick-to-tick gyro change over walk ticks) has median 0.51 against the sim's 0.20. In single stance the robot's pitch
also gives way unrepeatably (play-locate README: spread 4-10 deg on the left foot, sim 1.3-2.1).

Each condition below adds one effect to the sim and replays the same robot commands. An effect explains the gap if it
raises sim falls on the robot-fell replays and the jitter towards the robot's, without felling the robot-up replays.

  python3 gap_sweep.py --jobs 9            # Mac mini; results in gap-sweep.json, tick logs in gap-sweep/
  python3 gap_sweep.py --only base fric20  # a subset
"""
import argparse
import collections
import concurrent.futures
import json
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scorecard-20261109"))
import scorecard as SC  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
OUT = os.path.join(HERE, "gap-sweep")
HEAD = r"^(neck_pitch|head_pitch|head_yaw|head_roll)$"
CONDS = {
    "base": [],
    "fric1.5": ["--bam-friction-scale", "1.5"],          # servo deadband / stiction (10/17 sim-ID fit x1.5)
    "fric2.0": ["--bam-friction-scale", "2.0"],
    "legplay4": ["--joint-play", "4"],                   # 4 deg total horn/bracket play on every leg joint
    "footplay3": ["--foot-play", "3"],                   # +-3 deg play between ankle horn and foot
    "head8": ["--joint-play", "8", "--joint-play-only", HEAD],  # neck/head play: the head swings freely 8 deg
    "com+10": ["--com-x", "10"],                         # COM 10 mm forward / back
    "com-10": ["--com-x", "-10"],
    "com+3": ["--com-x", "3"], "com-3": ["--com-x", "-3"], "com+5": ["--com-x", "5"], "com-5": ["--com-x", "-5"],
    "solesoft": ["--sole-solref", "0.05", "1"],          # a compliant sole
    "drop10": ["--drop", "0.10"],                        # 10 % dropped servo reads (robot 3.3 %)
    "allplay4": ["--joint-play", "4", "--joint-play-only", "."],  # legs and head
    "combo": ["--bam-friction-scale", "1.5", "--joint-play", "4", "--joint-play-only", ".", "--foot-play", "3"],
}


def cases(n_fell, n_up):
    res = json.load(open(os.path.expanduser("~/duck-walks/scorecard-auto.json")))["results"]
    ok = [r for r in res if r["kind"] in ("walk", "turn", "balance") and r.get("sim_argv")
          and "--cmd-replay" in r["sim_argv"] and r.get("robot_jitter") is not None]
    fell = [r for r in ok if r["robot"] == "fell" and r["sim"] != "fell"][:n_fell]  # the gap cases
    up = [r for r in ok if r["robot"] == "up" and r["kind"] in ("walk", "turn")]
    up = up[:: max(1, len(up) // n_up)][:n_up]
    return fell + up


def finished(out):
    """A sim counts when it exited 0, or when it printed its result row and then aborted at teardown (exit -6:
    onnxruntime's "recursive_mutex lock failed" at interpreter exit, after the tick log is complete)."""
    lines = open(out).read().split("\n")
    if lines[0].strip() == "exit 0":
        return True
    return lines[0].strip() == "exit -6" and len(lines) > 1 and lines[1].startswith("{") and "recursive_mutex" in lines[-1] + "".join(lines[2:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=9)
    ap.add_argument("--fell", type=int, default=16, help="robot-fell / sim-up replays")
    ap.add_argument("--up", type=int, default=12, help="robot-up walk/turn replays")
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--models", default=None, help="policy directory for brain_sim_check --models (a fine-tune candidate)")
    ap.add_argument("--tag", default="", help="names this policy's tick logs and result file (gap-sweep<-tag>.json)")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    conds = {k: v for k, v in CONDS.items() if not a.only or k in a.only}
    cs = cases(a.fell, a.up)
    jobs = []
    for r in cs:
        base = [x for x in r["sim_argv"] if x]
        for cond, extra in conds.items():
          for seed in a.seeds:
            tl = os.path.join(OUT, f"{r['id']}.{cond}{'.' + a.tag if a.tag else ''}.seed{seed}.ticks.jsonl")
            jobs.append(dict(until=float(base[base.index("--until") + 1]), case=r["id"], kind=r["kind"], robot=r["robot"], robot_jitter=r["robot_jitter"], cond=cond,
                             tl=tl, replay=base[base.index("--cmd-replay") + 1],
                             argv=[PY, os.path.join(MAC, "brain_sim_check.py")] + base + extra +
                             (["--models", os.path.abspath(a.models)] if a.models else []) +
                             ["--seed", str(seed), "--tick-log", tl]))
    t0 = time.time()
    done = [0]

    def one(j):
        if os.path.exists(j["tl"] + ".out") and finished(j["tl"] + ".out"):
            return
        p = subprocess.run(j["argv"], capture_output=True, text=True, timeout=1800)
        last = (p.stdout.strip().splitlines() or [""])[-1]
        open(j["tl"] + ".out", "w").write(f"exit {p.returncode}\n{last}\n--- stderr tail\n{p.stderr[-2000:]}")
        done[0] += 1
        print(f"{done[0]}/{len(jobs)} {time.time() - t0:.0f}s {j['cond']} {j['case'][-30:]} exit {p.returncode}",
              flush=True)

    with concurrent.futures.ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(one, jobs))
    agg = collections.defaultdict(lambda: collections.defaultdict(list))
    rows = []
    for j in jobs:
        lines = open(j["tl"] + ".out").read().split("\n")
        if not finished(j["tl"] + ".out"):
            rows.append(dict(case=j["case"], cond=j["cond"], error=lines[0] + " " + lines[-1][-300:]))
            continue
        # the scorecard's own verdict: fall (> 45 deg) inside the robot's window (its fall + 1 s), times from the
        # replay start, a fall within 1 s of a replayed stand/monitor is the switch's (stop_topple), jitter as the card
        m = SC.sim_metrics(j["tl"], SC.WALK_AT, j["until"] - 0.5, True)
        stops = [t for t, c in json.load(open(j["replay"])) if c.get("mode") in ("stand", "monitor")]
        if m["outcome"] == "fell" and any(0 <= m["fell_at"] - t <= SC.STOP_TOPPLE_S for t in stops):
            m["outcome"] = "stop_topple"
        fell = m["outcome"] == "fell"
        rows.append(dict(case=j["case"], kind=j["kind"], robot=j["robot"], cond=j["cond"], outcome=m["outcome"],
                         fell_at=m["fell_at"], max_tilt=m["max_tilt_deg"], jitter=m["jitter"],
                         robot_jitter=j["robot_jitter"]))
        g = agg[j["cond"]]
        g[f"fell_robot_{j['robot']}"].append(int(fell))
        if m["jitter"] is not None and j["kind"] in ("walk", "turn"):
            g["jitter"].append(m["jitter"])
            g["robot_jitter"].append(j["robot_jitter"])
    summary = {}
    for cond in conds:
        g = agg[cond]
        summary[cond] = dict(
            sim_falls_where_robot_fell=f"{sum(g['fell_robot_fell'])}/{len(g['fell_robot_fell'])}",
            sim_falls_where_robot_up=f"{sum(g['fell_robot_up'])}/{len(g['fell_robot_up'])}",
            jitter_median=round(float(np.median(g["jitter"])), 3) if g["jitter"] else None,
            robot_jitter_median=round(float(np.median(g["robot_jitter"])), 3) if g["robot_jitter"] else None)
        print(f"{cond:10s}", summary[cond], flush=True)
    json.dump(dict(summary=summary, rows=rows, conds=CONDS, written=time.strftime("%Y-%m-%d %H:%M")),
              open(os.path.join(HERE, f"gap-sweep{'-' + a.tag if a.tag else ''}.json"), "w"), indent=1)
    errs = [r for r in rows if "error" in r]
    if errs:
        print(len(errs), "sims failed, first:", errs[0])
        sys.exit(1)


if __name__ == "__main__":
    main()
