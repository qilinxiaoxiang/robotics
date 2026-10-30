"""Label the duck's everyday recordings (life_log.py segments, or any mono16 recording) for the name spotter without
anyone marking them, the way a pet learns from what happens around it.

Per recording, on the ear mix at 16 kHz:
  score    the deployed spotter's P(mochi) every 100 ms (ownkws.OwnModel, an ensemble when the .npz holds members)
  events   voiced runs (train_mochi.events)
  like     log-mel correlation of each event with calls already known (mine_calls.py templates), z against the file
Labels, from strongest to weakest:
  call (sure)       an event the spotter is sure of (P >= --sure) that also resembles known calls (like >= --like)
  call (repeated)   an event that resembles a sure call 1-8 s away in the same recording (people repeat a name the
                    pet did not answer; Shawn calls every 2-3 s), and the spotter gave it at least --maybe
  not call          1 s windows with P under --quiet and no event resembling a call within 1 s: footsteps, standing up,
                    talk, servo and fan noise of ordinary life (the bulk of the negatives)
  doubtful hit      the spotter fired (P >= --sure) but nothing about it resembles a call and nothing repeats it:
                    reported for the next training as a negative only with --use-doubtful (a real call said oddly
                    can look like this, so it is a weaker label)
Output: a labels fragment (calls_found, negative_spans, doubtful) that train_mochi.py merges with --extra-labels.

  python3 mine_life.py --mono16 DIR --files a,b [--out life_labels.json]
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import mine_calls as mc  # noqa: E402
import ownkws as ok  # noqa: E402
import train_mochi as tm  # noqa: E402


def similar(f, t_a, t_b, n):
    """Normalised log-mel correlation of the T_LEN windows at t_a and t_b of one feature matrix."""
    ia, ib = int(round(t_a / mc.HOP)), int(round(t_b / mc.HOP))
    if min(ia, ib) < 0 or max(ia, ib) + n > len(f):
        return 0.0
    a, b = f[ia:ia + n] - f[ia:ia + n].mean(), f[ib:ib + n] - f[ib:ib + n].mean()
    return float((a * b).sum() / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def label(y, model, tpl, sure=0.9, maybe=0.3, quiet=0.1, like=3.0, rep_sim=0.5):
    ts, ps = tm.scores(model, y)
    tz, z = mc.scan(y, tpl)
    ev = tm.events(y, 0.0, len(y) / tm.FS)
    f = mc.feats(y)
    n = int(mc.T_LEN / mc.HOP)

    def p_near(s, e):
        sel = (ts >= s + 0.2) & (ts <= e + 1.2)              # windows ending on or after the word
        return float(ps[sel].max()) if sel.any() else 0.0

    def z_near(s):
        sel = np.abs(tz - s) <= 0.3
        return float(z[sel].max()) if sel.any() else -9.0

    info = [dict(s=round(s, 2), e=round(e, 2), p=round(p_near(s, e), 3), like=round(z_near(s), 1)) for s, e in ev]
    sure_calls = [d for d in info if d["p"] >= sure and d["like"] >= like]
    calls = {d["s"]: "sure" for d in sure_calls}
    # no "template alone" tier: on Shawn's ordinary speech (live_150103, no name said) events at like >= 5 and
    # P >= 0.3 gave six false calls; the template matches his voice as much as the word
    for d in info:
        if d["s"] in calls or d["p"] < maybe:
            continue
        if any(1.0 <= abs(d["s"] - c["s"]) <= 8.0 and similar(f, d["s"], c["s"], n) >= rep_sim for c in sure_calls):
            calls[d["s"]] = "repeated"
    callish = [d["s"] for d in info if d["like"] >= like or d["s"] in calls]
    doubtful = [d for d in info if d["p"] >= sure and d["s"] not in calls]
    # negative spans: 1 s steps whose windows stay under `quiet` and keep 1 s from anything call-like
    neg, start = [], None
    step = 0.5
    for t0 in np.arange(0.0, len(y) / tm.FS - ok.WINDOW_S, step):
        sel = (ts >= t0 + ok.WINDOW_S - 0.05) & (ts <= t0 + ok.WINDOW_S + step)
        ok_here = (not sel.any() or ps[sel].max() < quiet) and all(abs(c - t0 - 0.5) > 1.0 + 0.5 for c in callish)
        if ok_here and start is None:
            start = t0
        if not ok_here and start is not None:
            if t0 - start >= ok.WINDOW_S:
                neg.append([round(start, 2), round(t0 + ok.WINDOW_S - step, 2)])
            start = None
    if start is not None:
        neg.append([round(start, 2), round(len(y) / tm.FS, 2)])
    return dict(calls=[dict(s=s, how=h) for s, h in sorted(calls.items())], negative_spans=neg,
                doubtful=[dict(s=d["s"], p=d["p"], like=d["like"]) for d in doubtful], events=info)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mono16", required=True)
    ap.add_argument("--files", required=True)
    ap.add_argument("--labels", default=os.path.join(HERE, "mochi_labels.json"))
    ap.add_argument("--model", default=ok.MODEL_DEFAULT)
    ap.add_argument("--out", default=None)
    ap.add_argument("--sure", type=float, default=0.9)
    ap.add_argument("--like", type=float, default=3.0)
    a = ap.parse_args()
    lab = json.load(open(a.labels))
    mono = {p[:-4]: np.load(os.path.join(a.mono16, p)) for p in os.listdir(a.mono16) if p.endswith(".npy") and "@" not in p}
    files = a.files.split(",")
    model = ok.OwnModel(a.model)
    tpl = mc.templates(mono, mc.known_calls(lab, mono), exclude=tuple(files))   # never judge a file by its own calls
    out = dict(calls_found={}, negative_spans={}, doubtful={})
    for nm in files:
        r = label(mono[nm], model, tpl, sure=a.sure, like=a.like)
        out["calls_found"][nm] = [c["s"] for c in r["calls"]]
        out["negative_spans"][nm] = r["negative_spans"]
        out["doubtful"][nm] = r["doubtful"]
        neg_s = sum(t1 - t0 for t0, t1 in r["negative_spans"])
        print(f"{nm}: calls {[(c['s'], c['how']) for c in r['calls']]}; doubtful hits {[(d['s'], d['p'], d['like']) for d in r['doubtful']]}; "
              f"not-call {neg_s:.0f} s of {len(mono[nm]) / tm.FS:.0f} s")
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
