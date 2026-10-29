"""Replay a robot recording through the real namecall detector + localiser and score it against the calls Shawn
confirmed by ear. Prints per-call azimuth, error, elevation and detection time, the false triggers on the quiet
stretches, and writes the JSON record.

  pet/.venv/bin/python replay_calls.py recordings/calls_221619.wav \
      --calls 39.3:0,47.1:45,55.6:90,63.8:135,71.6:180,79.8:-135,88.0:-90,95.1:-45 \
      --out results/replay_221619.json [-- any namecall.py flags, e.g. --elev 0,35 --loc-band 1500,8000]

  pet/.venv/bin/python replay_calls.py recordings/calls_201411.wav --calls 21.75,34.08,42.43,51.07,59.79,68.55,80.31,88.15 \
      --exclude 26-30,37,45,54,63,75,83,144,175 --out results/replay_201411.json      (negative reference, no azimuths)

A call window is [t - 0.5, t + 1.5] s around the given time (the times are the start of the word by ear, within
about 0.3 s; the detector fires at the first loud block, which on these recordings is 0.5-1.0 s later). The first
detection inside a window is the call's; later ones in the same window are "extra"; detections outside every call
window and every --exclude range are false triggers, counted per minute of that quiet time.
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import namecall as nc  # noqa: E402

CALL_WIN = (-0.5, 1.5)


def wrap(d):
    return (d + 180.0) % 360.0 - 180.0


def parse_calls(s):
    out = []
    for item in s.split(","):
        if not item.strip():
            continue
        if ":" in item:
            t, az = item.split(":")
            out.append((float(t), float(az)))
        else:
            out.append((float(item), None))
    return out


def parse_ranges(s):
    out = []
    for item in (s or "").split(","):
        if not item.strip():
            continue
        if "-" in item.strip("-") and not item.strip().startswith("-"):
            a, b = item.split("-")
            out.append((float(a), float(b)))
        else:
            v = float(item)
            out.append((v - 1.0, v + 1.0))
    return out


def side_ok(est, exp):
    return np.sign(est) == np.sign(exp)


def front_ok(est, exp):
    return (abs(est) < 90) == (abs(exp) < 90)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("wav")
    ap.add_argument("--calls", required=True, help="t[:az_deg],... call times by ear (s) and expected azimuths (+ left)")
    ap.add_argument("--exclude", default="", help="a-b,... or t,... ranges (s) left out of the quiet-stretch count")
    ap.add_argument("--out", default=None, help="JSON record")
    ap.add_argument("--within", type=float, default=30.0, help="deg, counts as correct")
    ap.add_argument("--quiet", action="store_true")
    a, extra = ap.parse_known_args(argv)
    if extra and extra[0] == "--":
        extra = extra[1:]
    calls = parse_calls(a.calls)
    excl = parse_ranges(a.exclude)

    nargs = nc.parse_args(["--wav", a.wav, "--no-head", "--mute", "--no-sound", "--quiet", "--log", os.devnull] + extra)
    nargs.no_gate = True
    log = nc.Log(None, echo=False)
    n = nc.NameCall(nargs, log)
    src = nc.WavSource(a.wav)
    t0 = time.perf_counter()
    dets, stats = nc.replay(n, src, log)
    wall = time.perf_counter() - t0
    dur = len(src.x) / src.fs

    rows, used = [], set()
    for g, az_exp in calls:
        lo, hi = g + CALL_WIN[0], g + CALL_WIN[1]
        inside = [i for i, d in enumerate(dets) if lo <= d["t"] <= hi and i not in used]
        row = dict(t_by_ear=g, expected_az_deg=az_exp, detected=bool(inside))
        if inside:
            d = dets[inside[0]]
            used.update(inside)
            row.update(onset_t=round(d["t"], 2), onset_after_ear_s=round(d["t"] - g, 2),
                       decided_t=round(d.get("decided_t", d["t"]), 2),
                       decision_after_onset_s=round(d.get("decided_t", d["t"]) - d["t"], 2),
                       az_deg=d["az_deg"], el_deg=d.get("el_deg"), bins=d.get("bins"), margin=d.get("margin"),
                       srp=d.get("srp"), pairs=d.get("pairs"), extra_in_window=len(inside) - 1)
            if az_exp is not None:
                err = wrap(d["az_deg"] - az_exp)
                row.update(error_deg=round(err, 1), within=abs(err) <= a.within,
                           side_ok=None if abs(az_exp) in (0, 180) else bool(side_ok(d["az_deg"], az_exp)),
                           front_back_ok=None if abs(az_exp) == 90 else bool(front_ok(d["az_deg"], az_exp)))
        rows.append(row)

    def excluded(t):
        return any(lo <= t <= hi for lo, hi in excl) or any(g + CALL_WIN[0] <= t <= g + CALL_WIN[1] for g, _ in calls)

    false = [d for i, d in enumerate(dets) if i not in used and not excluded(d["t"])]
    on_excluded = [d for i, d in enumerate(dets) if i not in used and excluded(d["t"])
                   and not any(g + CALL_WIN[0] <= d["t"] <= g + CALL_WIN[1] for g, _ in calls)]
    quiet_s = dur - sum(CALL_WIN[1] - CALL_WIN[0] for _ in calls) - sum(max(0.0, hi - lo) for lo, hi in excl)
    quiet_s = max(quiet_s, 1e-6)
    scored = [r for r in rows if r["expected_az_deg"] is not None]
    summary = dict(
        wav=os.path.basename(a.wav), duration_s=round(dur, 1), calls=len(calls),
        detected=sum(r["detected"] for r in rows),
        within=sum(bool(r.get("within")) for r in scored), within_deg=a.within,
        side_ok=sum(bool(r.get("side_ok")) for r in scored),
        side_calls=sum(abs(r["expected_az_deg"]) not in (0, 180) for r in scored),
        front_back_ok=sum(bool(r.get("front_back_ok")) for r in scored),
        front_back_calls=sum(abs(r["expected_az_deg"]) != 90 for r in scored),
        mean_abs_error_deg=round(float(np.mean([abs(r["error_deg"]) for r in scored if "error_deg" in r])), 1)
        if any("error_deg" in r for r in scored) else None,
        false_triggers=len(false), false_on_excluded=len(on_excluded), quiet_s=round(quiet_s, 1),
        false_per_min=round(60.0 * len(false) / quiet_s, 2),
        false_trigger_times=[round(d["t"], 2) for d in false],
        excluded_trigger_times=[round(d["t"], 2) for d in on_excluded],
        decision_after_onset_s=[r.get("decision_after_onset_s") for r in rows if r["detected"]],
        cpu=dict(cpu_share=stats["cpu_share"], block_ms_p50=stats["block_ms_p50"], block_ms_p99=stats["block_ms_p99"],
                 block_ms_max=stats["block_ms_max"], wall_s=round(wall, 2)),
        settings=n.mode_info(), extra_flags=extra, host=os.uname().nodename)
    out = dict(summary=summary, calls=rows, all_detections=[dict(t=round(d["t"], 2), az_deg=d["az_deg"], el_deg=d.get("el_deg"),
                                                                   bins=d.get("bins"), margin=d.get("margin")) for d in dets])
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump(out, open(a.out, "w"), indent=1)
    if not a.quiet:
        for r in rows:
            if not r["detected"]:
                print(f"  call at {r['t_by_ear']:6.1f} s exp {str(r['expected_az_deg']):>6}: MISSED")
                continue
            e = f"err {r['error_deg']:+5.0f}" if "error_deg" in r else ""
            print(f"  call at {r['t_by_ear']:6.1f} s exp {str(r['expected_az_deg']):>6}: az {r['az_deg']:+6.1f} {e:10s} "
                  f"el {r['el_deg']} bins {r['bins']} margin {r['margin']} onset +{r['onset_after_ear_s']:.2f} s, "
                  f"decided +{r['decision_after_onset_s']:.2f} s after the onset")
        s = summary
        print(f"{s['wav']}: {s['detected']}/{s['calls']} detected, {s['within']}/{len(scored)} within {a.within:.0f} deg, "
              f"side {s['side_ok']}/{s['side_calls']}, front/back {s['front_back_ok']}/{s['front_back_calls']}, "
              f"mean |err| {s['mean_abs_error_deg']}; false triggers {s['false_triggers']} in {s['quiet_s']:.0f} s quiet "
              f"= {s['false_per_min']}/min (on excluded events: {s['false_on_excluded']}); cpu share {s['cpu']['cpu_share']}")
        if a.out:
            print("->", a.out)
    return out


if __name__ == "__main__":
    main()
