"""Report on one hold session (Mac): pads, proximity, lift current, lock-ups, the hold in action, gesture features.

    python3 hold_analyze.py data/duck_wired_log_<suffix>.jsonl.gz data/hold_labels_<suffix>.jsonl [--cal-out PATH]

Trials come from hold_session.py's label file (Shawn's own labels; nothing is inferred from the trace). Prints a plain
text report and writes the calibration hold_session.py's c key would compute from the same trials
(hold_cal_<suffix>.json beside the labels), or the reasons it refuses.
"""
import argparse
import gzip
import json
import math
import os
import statistics as st

import hold_session as hs
from hold_session import NAMES, PADS, HEAD_PITCH, NECK_PITCH, Rows, window, middle

LIFTS = ("lift_head_off", "lift_body", "lift_head_on")
GESTURES = ("stroke", "pat", "pat_hard", "stroke_on", "pat_on", "pat_hard_on")
AFTER_S = 1.0     # also look this long past a trial's end (the set-down)
ON_MIN = 150.0    # counts: a pad is on above max(5 x rest std, ON_MIN) (features.py)


def load_log(path):
    op = gzip.open if path.endswith(".gz") else open
    rows = []
    with op(path, "rt") as f:
        for ln in f:
            try:
                r = json.loads(ln)
            except ValueError:
                continue  # a half-written last line
            if isinstance(r, dict) and "t" in r:
                rows.append(r)
    rows.sort(key=lambda r: r["t"])
    return rows


def med(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else None


def f0(x, spec=".0f"):
    return "-" if x is None else format(x, spec)


def cur(r, k):
    c = r.get("cur_ma")
    return abs(c[k]) if c and c[k] is not None else None


def lockup(full, t0, t1):
    """What happened inside a lift trial (+ AFTER_S): a guard trip (mode left walk), a hardware error, or neither."""
    rows = window(full, t0, t1 + AFTER_S)
    if not rows:
        return {"verdict": "no rows", "text": "no log rows"}
    out, verdict = [], []
    m0 = rows[0].get("mode")
    for a, b in zip(rows, rows[1:]):
        if b.get("mode") != a.get("mode"):
            out.append(f"mode {a.get('mode')} -> {b.get('mode')} at +{b['t'] - t0:.2f} s")
            if a.get("mode") == "walk":
                verdict.append("guard")
    faults = sorted({str(x) for r in rows for x in (r.get("hw_faults") or [])})
    if faults:
        first = next(r["t"] for r in rows if r.get("hw_faults"))
        out.append(f"hardware error {faults} from +{first - t0:.2f} s")
        verdict.append("hw")
    miss = sum(1 for r in rows if r.get("missing"))
    if miss:
        out.append(f"{miss} ticks with missing servo reads")
    if any(r.get("torque") is False for r in rows):
        out.append("torque off in some ticks")
    v = "+".join(dict.fromkeys(verdict)) or "neither"
    return {"verdict": v, "mode_at_start": m0, "text": "; ".join(out) or "no mode change, no hardware error"}


def gesture_features(full, slim, tr, rest_std):
    """Compact per-trial touch features after features.py: pads on, peak, rise slope, onset order and spread, taps,
    and the head's mechanical response (|acc| - g and |gyro| peaks)."""
    base = hs.pre_base(slim, tr["t0"], None)
    rows = [r for r in window(slim, tr["t0"], tr["t1"]) if r["touch"]]
    if base is None or len(rows) < 3:
        return None
    d = [[c - b for c, b in zip(r["touch"], base)] for r in rows]
    thr = [max(5 * s, ON_MIN) for s in rest_std]
    on = [[x > th for x, th in zip(row, thr)] for row in d]
    onset = [next((rows[k]["t"] - tr["t0"] for k in range(len(d)) if on[k][i]), None) for i in range(len(PADS))]
    ons = sorted((o, PADS[i]) for i, o in enumerate(onset) if o is not None)
    imax = max(range(len(PADS)), key=lambda i: max(row[i] for row in d))
    rises = [k for k in range(1, len(d)) if on[k][imax] and not on[k - 1][imax]] + ([0] if on[0][imax] else [])
    imu = window(full, tr["t0"], tr["t1"])
    acc = [abs(math.sqrt(sum(a * a for a in r["acc"])) - 9.81) for r in imu if r.get("acc")]
    gyr = [math.sqrt(sum(g * g for g in r["gyro_body"])) for r in imu if r.get("gyro_body")]
    return {"dur": tr["t1"] - tr["t0"], "pads_on": len(ons), "order": " ".join(p for _, p in ons),
            "spread": (ons[-1][0] - ons[0][0]) if len(ons) > 1 else 0.0,
            "peak": max(max(row) for row in d),
            "slope": max((d[k][i] - d[k - 1][i] for k in range(1, len(d)) for i in range(len(PADS))), default=0.0),
            "rises": len(rises), "acc_pk": max(acc, default=0.0), "gyro_pk": max(gyr, default=0.0)}


def hold_track(full, tr):
    """The hold estimate through a trial and 1 s after it: authority s, gains, engagement and load."""
    rows = [r for r in window(full, tr["t0"], tr["t1"] + AFTER_S) if r.get("hold")]
    if not rows:
        return None
    h = [r["hold"] for r in rows]
    s = [x.get("s") for x in h]
    i_min = min(range(len(s)), key=lambda i: s[i] if s[i] is not None else 9)
    after = [x.get("s") for r, x in zip(rows, h) if r["t"] > tr["t1"]]
    loads = [x["load"] for x in h if x.get("load") is not None]
    return {"s0": s[0], "s_min": s[i_min], "t_min": rows[i_min]["t"] - tr["t0"], "s_end": after[-1] if after else s[-1],
            "kp_leg_min": min((x.get("kp_leg") for x in h if x.get("kp_leg") is not None), default=None),
            "kp_neck_max": max((x.get("kp_neck") for x in h if x.get("kp_neck") is not None), default=None),
            "e_max": max((x.get("e") or 0 for x in h)), "load_min": min(loads) if loads else None,
            "applied": sum(bool(r.get("hold_on")) for r in rows) / len(rows)}


def report(full_rows, trials):
    full = Rows(full_rows)
    slim = Rows([hs.slim(r) for r in full_rows])
    by = {}
    for tr in trials:
        by.setdefault(tr["label"], []).append(tr)
    out = [f"{len(full_rows)} log rows, {len(trials)} good trials: "
           + ", ".join(f"{k} {len(v)}" for k, v in by.items())]
    rest_med, rest_std = hs.pad_rest(slim, by.get("rest", []))
    stand = med([r["legs_ma"] for tr in by.get("rest", []) for r in window(slim, tr["t0"], tr["t1"])])
    neck_rest = med([cur(r, NECK_PITCH) for tr in by.get("rest", []) for r in window(full, tr["t0"], tr["t1"])])
    head_rest = med([cur(r, HEAD_PITCH) for tr in by.get("rest", []) for r in window(full, tr["t0"], tr["t1"])])
    out.append("\n== rest (step 0)")
    if rest_med:
        out.append("pad rest median " + " ".join(f"{p} {m:.0f}" for p, m in zip(PADS, rest_med)))
        out.append("pad rest std    " + " ".join(f"{p} {s:.1f}" for p, s in zip(PADS, rest_std)))
    out.append(f"legs_ma standing {f0(stand)} mA, |neck_pitch| {f0(neck_rest)} mA, |head_pitch| {f0(head_rest)} mA")
    rest_std = rest_std or [10.0] * len(PADS)

    out.append("\n== single-pad presses (step 1): rise of the pressed pad, cross-talk = other pads / pressed")
    press_rise = {}
    for p in PADS:
        k = PADS.index(p)
        rises = [x for x in (hs.trial_rise(slim, tr, rest_med) for tr in by.get("press_" + p, [])) if x]
        if not rises:
            out.append(f"{p:>2}: no trials")
            continue
        press_rise[p] = st.median(x[k] for x in rises)
        xt = max((max(0.0, st.median(x[j] for x in rises)) / press_rise[p] if press_rise[p] > 0 else 0.0)
                 for j in range(len(PADS)) if j != k)
        out.append(f"{p:>2}: rise {press_rise[p]:.0f} (trials " + ", ".join(f"{x[k]:.0f}" for x in rises)
                   + f"), worst cross-talk {100 * xt:.0f} %")

    out.append("\n== hover 1-2 cm (step 2): strongest pad rise, share of its press rise")
    for tr in by.get("hover", []):
        x = hs.trial_rise(slim, tr, rest_med)
        if x:
            i = max(range(len(PADS)), key=lambda j: x[j])
            share = x[i] / press_rise[PADS[i]] if press_rise.get(PADS[i]) else None
            out.append(f"#{tr['trial']}: {PADS[i]} {x[i]:+.0f} counts" + (f" = {100 * share:.0f} % of a press" if share
                                                                          is not None else ""))

    cal, problems = hs.compute_cal(trials, slim)
    out.append("\n== grip without lift (step 3): covered area with the computed calibration")
    for tr in by.get("grip", []):
        if not cal:
            break
        base = hs.pre_base(slim, tr["t0"], rest_med)
        a, b = middle(tr["t0"], tr["t1"])
        areas = [hs.area_mm2(hs.levels([c - b0 for c, b0 in zip(r["touch"], base)], cal["pad_lo"], cal["pad_hi"]))
                 for r in window(slim, a, b) if r["touch"]]
        out.append(f"#{tr['trial']}: {f0(med(areas))} mm2")

    out.append("\n== lifts: legs_ma in the middle 1 s vs standing, neck current, what happened (+1 s after the end)")
    for lb in LIFTS:
        for tr in by.get(lb, []):
            a, b = middle(tr["t0"], tr["t1"], keep=1.0)
            mid = window(full, a, b)
            legs = med([hs.legs_of(r) for r in mid])
            sep = f"{100 * (stand - legs) / stand:.0f} % below standing" if legs is not None and stand else "-"
            amax = max((abs(x) for r in window(full, tr["t0"], tr["t1"]) for x in (r.get("action") or [])), default=None)
            tilt = max((hs.hold.tilt_deg(r["gb"]) for r in window(full, tr["t0"], tr["t1"]) if r.get("gb")), default=None)
            lk = lockup(full, tr["t0"], tr["t1"])
            out.append(f"{lb} #{tr['trial']} ({tr['t1'] - tr['t0']:.1f} s): legs {f0(legs)} mA ({sep}); "
                       f"|neck_pitch| {f0(med([cur(r, NECK_PITCH) for r in mid]))} mA (rest {f0(neck_rest)}), "
                       f"|head_pitch| {f0(med([cur(r, HEAD_PITCH) for r in mid]))} mA (rest {f0(head_rest)}); "
                       f"max|action| {f0(amax, '.2f')}, max tilt {f0(tilt, '.1f')} deg")
            out.append(f"    -> {lk['verdict']}: {lk['text']}")

    on_trials = [tr for lb in by for tr in by[lb] if lb.endswith("_on")]
    if on_trials:
        out.append("\n== hold ON (step 7): authority s start/min (at s)/1 s after, gains, engagement, load")
        for tr in on_trials:
            h = hold_track(full, tr)
            if h is None:
                out.append(f"{tr['label']} #{tr['trial']}: no hold field in the log")
                continue
            out.append(f"{tr['label']} #{tr['trial']}: s {h['s0']} -> min {h['s_min']} at +{h['t_min']:.2f} s -> "
                       f"{h['s_end']}; kp_leg min {h['kp_leg_min']}, kp_neck max {h['kp_neck_max']}; e max "
                       f"{h['e_max']:.2f}, load min {h['load_min']}; applied in {100 * h['applied']:.0f} % of ticks")

    out.append("\n== gestures: per-trial features (pads on, onset order, spread s, peak, max rise/tick, rises, "
               "|acc|-g peak, |gyro| peak)")
    for lb in GESTURES:
        feats = [(tr, gesture_features(full, slim, tr, rest_std)) for tr in by.get(lb, [])]
        feats = [(tr, f) for tr, f in feats if f]
        for tr, f in feats:
            out.append(f"{lb} #{tr['trial']}: on {f['pads_on']} [{f['order']}] spread {f['spread']:.2f} peak "
                       f"{f['peak']:.0f} slope {f['slope']:.0f} rises {f['rises']} acc {f['acc_pk']:.2f} "
                       f"gyro {f['gyro_pk']:.2f}")
        if feats:
            m = {k: st.median(f[k] for _, f in feats) for k in ("pads_on", "spread", "peak", "slope", "rises", "gyro_pk")}
            out.append(f"  {lb} median: " + " ".join(f"{k} {v:.2f}" for k, v in m.items()))

    out.append("\n== calibration")
    if cal:
        out.append(json.dumps(cal))
    else:
        out.append("refused: " + "; ".join(problems))
    return "\n".join(out), cal, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("log")
    ap.add_argument("labels")
    ap.add_argument("--cal-out")
    a = ap.parse_args()
    trials, _ = hs.load_trials(a.labels)
    text, cal, problems = report(load_log(a.log), trials)
    print(text)
    path = a.cal_out or os.path.join(os.path.dirname(os.path.abspath(a.labels)),
                                     f"hold_cal_{hs.suffix_of(a.log)}.json")
    with open(path, "w") as f:
        json.dump(cal if cal else {"refused": problems}, f, indent=1)
    print("calibration ->", path)


if __name__ == "__main__":
    main()
