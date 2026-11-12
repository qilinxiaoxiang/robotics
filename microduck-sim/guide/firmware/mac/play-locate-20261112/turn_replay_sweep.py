#!/usr/bin/env python3
"""Mac mini: do the robot's falls come from the turn command its heading hold feeds walk61?

On the robot the policy's yaw-rate input (`turn` = trim + heading hold, limit 2.0; walk61 trained on +-1.0) passes 1.0
in most walks and is pinned at 2.0 in some; in the sim's replays of the same walks it never passes 0.5, because the sim
has no yaw drift for the hold to fight. This sweep replays every forward-walk segment of the robot logs twice:

  hold   the scorecard's way: the app's commands, the sim's own heading hold
  turn   the same commands, plus the robot's logged `turn` fed to the policy tick by tick (--turn-replay)

Windows run from the walk's first command to 1 s past the fall's onset (fell) or 3 s past the walk's end (up), so a fall
that begins after the walk stops is inside its own walk's replay. Stand/monitor commands are left out (they are the
robot's fall guard). The sim counts as fell when its tilt passes 45 deg inside the window.

  python3 turn_replay_sweep.py prepare      # cases + replay files from the raw logs
  python3 turn_replay_sweep.py run --jobs 6 [--up 40] [--seeds 0 1] [--extra-tag T -- sim args]
"""
import argparse
import collections
import concurrent.futures
import glob
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
OUT = os.path.expanduser("~/sims/fall-onset-20261112/turn-replay")
CACHE = os.path.expanduser("~/sims/fall-onset-20261112/cache")
RAW = os.path.expanduser("~/duck-walks/raw")
WALK_AT = 3.0


def tilt_deg(gb):
    g = gb / np.maximum(np.linalg.norm(gb, axis=1, keepdims=True), 1e-9)
    return np.degrees(np.arccos(np.clip(-g[:, 2], -1, 1)))


def segments(mask, t, gap=0.3):
    idx = np.where(mask)[0]
    if not len(idx):
        return []
    cuts = np.where(np.diff(t[idx]) > gap)[0]
    return list(zip(np.r_[idx[0], idx[cuts + 1]], np.r_[idx[cuts], idx[-1]]))


def prepare():
    os.makedirs(OUT, exist_ok=True)
    card = json.load(open(os.path.expanduser("~/duck-walks/scorecard-auto.json")))["results"]
    manifest = {}
    for r in card:
        a = r.get("sim_argv") or []
        if "--manifest" in a:
            manifest[r["day"]] = a[a.index("--manifest") + 1]
    cases = []
    for f in sorted(glob.glob(os.path.join(CACHE, "duck_wired_log_app*.npz"))):
        log = os.path.basename(f)[:-4]
        L = dict(np.load(f))
        t, tot = L["t"], tilt_deg(L["gb"])
        walking = (L["mode"] == 2) & (L["vx"] > 0.01) & L["torque"].astype(bool)
        wins = []
        for s, e in segments(walking, t):
            if t[e] - t[s] < 0.8:
                continue
            after = int(np.searchsorted(t, t[e] + 3.0))
            fi = np.where(tot[s:after] > 45)[0]
            fell = len(fi) > 0
            j = s + int(fi[0]) if fell else e
            while fell and j > s and tot[j] > 15:
                j -= 1
            t_end = float(t[j] + 1.0) if fell else float(t[e] + 3.0)
            k = slice(s, int(np.searchsorted(t, t_end)))
            day = time.strftime("%Y-%m-%d", time.localtime(t[s]))
            batt = L["batt"][k]
            batt = batt[(batt >= 60) & (batt <= 86)]
            w = L["mode"][k] == 2
            turn = np.nan_to_num(L["turn"][k])
            tr, prev = [], None
            for ti, v, m in zip(t[k], turn, L["mode"][k]):
                v = float(v) if m == 2 else 0.0
                if v != prev:
                    tr.append([round(float(ti - t[s]), 3), round(v, 3)])
                    prev = v
            cid = f"{log}-{t[s]:.2f}"
            json.dump(tr, open(os.path.join(OUT, cid + ".turn.json"), "w"))
            pre = slice(s, min(j, e) + 1)
            cases.append(dict(id=cid, log=log, t0=float(t[s]), t1=t_end, fell=bool(fell), onset=float(t[j] - t[s]) if fell else None,
                              dur=float(t[e] - t[s]), volt=round(float(np.median(batt)) / 10, 1) if len(batt) else 7.6,
                              drop=round(float(np.mean(~L["fresh"][k][w].astype(bool))), 3) if w.any() else 0.0,
                              turn_absmax=float(np.max(np.abs(np.nan_to_num(L["turn"][pre])))),
                              robot_max_tilt=float(np.max(tot[k])), robot_gz_rms=float(np.sqrt(np.mean(L["gyro"][pre, 2] ** 2))),
                              manifest=manifest.get(day) or sorted(manifest.items())[-1][1]))
            wins.append(cases[-1])
        # the control-file commands inside each window, from the raw log (head commands included)
        if wins:
            outs = {c["id"]: ([], [None]) for c in wins}
            with open(os.path.join(RAW, log + ".jsonl")) as h:
                for line in h:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    tt = r.get("t")
                    if tt is None or not r.get("cmd"):
                        continue
                    for c in wins:
                        if c["t0"] <= tt < c["t1"]:
                            rp, prev = outs[c["id"]]
                            if r["cmd"].get("mode") != "walk":
                                continue  # the robot's own fall guard / stop: not part of the walk under test
                            key = json.dumps(r["cmd"], sort_keys=True)
                            if key != prev[0]:
                                rp.append([round(tt - c["t0"], 3), r["cmd"]])
                                prev[0] = key
            for c in wins:
                json.dump(outs[c["id"]][0], open(os.path.join(OUT, c["id"] + ".replay.json"), "w"))
        print(log, len(wins), "segments", sum(c["fell"] for c in wins), "fell", flush=True)
    json.dump(cases, open(os.path.join(OUT, "cases.json"), "w"), indent=1)
    print(len(cases), "cases,", sum(c["fell"] for c in cases), "fell")


def sim_result(tl, t_to):
    tilt_max, fell_at, gz, turn = 0.0, None, [], []
    with open(tl) as h:
        for line in h:
            r = json.loads(line)
            if r["t"] < WALK_AT or r["t"] > t_to or not r.get("gb"):
                continue
            tdeg = math.degrees(math.acos(max(-1.0, min(1.0, -r["gb"][2]))))
            tilt_max = max(tilt_max, tdeg)
            if tdeg > 45 and fell_at is None:
                fell_at = r["t"] - WALK_AT
            if fell_at is None:
                gz.append(r["gyro_body"][2])
                turn.append(abs(r.get("turn") or 0.0))
    return dict(fell=fell_at is not None, fell_at=fell_at, max_tilt=round(tilt_max, 1),
                gz_rms=round(float(np.sqrt(np.mean(np.square(gz)))), 3) if gz else None,
                turn_absmax=round(max(turn), 2) if turn else None)


def run(a, extra):
    cases = json.load(open(os.path.join(OUT, "cases.json")))
    fell = [c for c in cases if c["fell"]]
    up = [c for c in cases if not c["fell"]]
    if a.up and a.up < len(up):  # spread over the turn-command range, largest first half and an even sample of the rest
        up = sorted(up, key=lambda c: -c["turn_absmax"])
        up = up[:: max(1, len(up) // a.up)][: a.up]
    conds = [c for c in ("hold", "turn") if not a.only or c in a.only]
    jobs = []
    for c in fell + up:
        until = WALK_AT + (c["t1"] - c["t0"])
        base = ["--model", "asbuilt", "--manifest", c["manifest"], "--volt", str(c["volt"]), "--drop", str(c["drop"]),
                "--stand-s", "1.0", "--walk-at", str(WALK_AT), "--until", f"{until:.2f}", "--walk-s", "0",
                "--cmd-replay", os.path.join(OUT, c["id"] + ".replay.json")] + extra
        for cond in conds:
            for seed in a.seeds:
                tl = os.path.join(OUT, f"{c['id']}.{cond}{'.' + a.tag if a.tag else ''}.seed{seed}.ticks.jsonl")
                argv = [PY, os.path.join(MAC, "brain_sim_check.py")] + base + ["--seed", str(seed), "--tick-log", tl]
                if cond == "turn":
                    argv += ["--turn-replay", os.path.join(OUT, c["id"] + ".turn.json")]
                jobs.append(dict(case=c, cond=cond, seed=seed, tl=tl, until=until, argv=argv))
    t0, done = time.time(), [0]

    def ok(tl):
        return os.path.exists(tl + ".out") and open(tl + ".out").readline().strip() in ("exit 0", "exit -6") and os.path.exists(tl)

    def one(j):
        if ok(j["tl"]):
            return
        p = subprocess.run(j["argv"], capture_output=True, text=True, timeout=1800)
        open(j["tl"] + ".out", "w").write(f"exit {p.returncode}\n{(p.stdout.strip().splitlines() or [''])[-1]}\n--- stderr tail\n{p.stderr[-1500:]}")
        done[0] += 1
        if done[0] % 10 == 0:
            print(f"{done[0]}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)

    with concurrent.futures.ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(one, jobs))
    rows, agg, errs = [], collections.defaultdict(lambda: collections.defaultdict(list)), 0
    for j in jobs:
        if not ok(j["tl"]):
            errs += 1
            continue
        m = sim_result(j["tl"], j["until"])
        c = j["case"]
        rows.append(dict(case=c["id"], cond=j["cond"], seed=j["seed"], robot_fell=c["fell"], robot_onset=c["onset"],
                         robot_turn_absmax=round(c["turn_absmax"], 2), robot_gz_rms=round(c["robot_gz_rms"], 3), **m))
        g = agg[j["cond"]]
        g["fell" if c["fell"] else "up"].append(int(m["fell"]))
        if m["gz_rms"] is not None:
            g["gz"].append(m["gz_rms"])
            g["rgz"].append(c["robot_gz_rms"])
        g["tilt"].append(m["max_tilt"])
    summary = {}
    for cond in conds:
        g = agg[cond]
        summary[cond] = dict(sim_falls_where_robot_fell=f"{sum(g['fell'])}/{len(g['fell'])}",
                             sim_falls_where_robot_up=f"{sum(g['up'])}/{len(g['up'])}",
                             sim_gz_rms_median=round(float(np.median(g["gz"])), 3) if g["gz"] else None,
                             robot_gz_rms_median=round(float(np.median(g["rgz"])), 3) if g["rgz"] else None)
        print(cond, summary[cond], flush=True)
    # per case: share of seeds that fell under each condition
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        by[r["case"]][r["cond"]].append(r)
    print("\ncase                                   robot  onset turn| | hold: falls tilt | turn: falls tilt fell_at")
    for cid, d in sorted(by.items(), key=lambda kv: (-kv[1][conds[0]][0]["robot_fell"], kv[0])):
        r0 = d[conds[0]][0]
        line = f"{cid[15:]:38s} {'FELL' if r0['robot_fell'] else 'up  '} {r0['robot_onset'] or 0:5.2f} {r0['robot_turn_absmax']:4.2f} |"
        for cond in conds:
            v = d.get(cond, [])
            line += f" {sum(x['fell'] for x in v)}/{len(v)} {max((x['max_tilt'] for x in v), default=0):5.1f} "
            if cond == "turn":
                line += str([round(x["fell_at"], 2) for x in v if x["fell_at"] is not None])
        print(line)
    json.dump(dict(summary=summary, rows=rows, extra=extra, written=time.strftime("%Y-%m-%d %H:%M")),
              open(os.path.join(HERE, f"turn-replay-sweep{'-' + a.tag if a.tag else ''}.json"), "w"), indent=1)
    if errs:
        print(errs, "sims failed")
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("prepare", "run"))
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--up", type=int, default=40)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1])
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--tag", default="")
    a, extra = ap.parse_known_args()
    extra = [x for x in extra if x != "--"]
    if a.what == "prepare":
        prepare()
    else:
        run(a, extra)


if __name__ == "__main__":
    main()
