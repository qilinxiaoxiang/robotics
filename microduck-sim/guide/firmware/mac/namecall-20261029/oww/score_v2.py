#!/usr/bin/env python3
"""Round-2 additions to score_oww.py (same streaming protocol): the 14 held-out live_141734 calls and false wakes
per hour on the held-out life talk (data/life_heldout.json, the _1030_late set the model never saw).

  ~/.venvs/oww/bin/python score_v2.py --model models/mochi_v2.onnx [--out results/mochi_v2_extra.json]
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score_oww import D, THRESHOLDS, WINDOW_S, Model, hits, scores  # noqa: E402

OWW = "/Users/shawnxiang/mochi-train/oww"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--heldout", default=os.path.join(OWW, "data", "duck_heldout.json"),
                    help="recording -> word starts never trained on (round 3: data/duck_heldout_v3.json, four recordings)")
    a = ap.parse_args()
    t0 = time.time()
    model = Model(wakeword_models=[a.model], inference_framework="onnx")
    key = os.path.splitext(os.path.basename(a.model))[0]
    mono = lambda nm: np.load(os.path.join(D, "mono16v2", nm + ".npy")).astype(np.float32)
    duck = json.load(open(a.heldout))
    life = json.load(open(os.path.join(OWW, "data", "life_heldout.json")))
    duck_sc = {nm: scores(model, key, mono(nm)) for nm in duck}
    life_sc = {nm: scores(model, key, mono(nm)) for nm in life}
    life_s = sum(t1 - t0_ for sp in life.values() for t0_, t1 in sp)
    res = {}
    for thr in THRESHOLDS:
        got = n = 0
        per = {}
        for nm, ons in duck.items():
            hs = hits(*duck_sc[nm], thr)
            g = sum(any(0.2 <= h - o <= 1.6 for h in hs) for o in ons)
            per[nm] = f"{g}/{len(ons)}"
            got += g
            n += len(ons)
        fa = {}
        for nm, sp in life.items():
            ts, ps = life_sc[nm]
            for s0, s1 in sp:
                sel = (ts >= s0 + WINDOW_S) & (ts <= s1)
                hs = hits(ts[sel], ps[sel], thr)
                if hs:
                    fa[f"{nm} {s0}-{s1}"] = [round(h, 1) for h in hs]
        nfa = sum(len(v) for v in fa.values())
        res[str(thr)] = dict(duck_heldout=f"{got}/{n}", duck_heldout_per_recording=per, life_false=nfa,
                             life_false_per_h=round(nfa / (life_s / 3600), 1), life_false_at=fa)
        print(f"  thr {thr}: held-out duck calls {got}/{n} {per}; held-out life talk ({life_s / 60:.1f} min): {nfa} false ({res[str(thr)]['life_false_per_h']}/h)")
    rep = dict(made=time.strftime("%Y-%m-%d %H:%M"), model=a.model, life_heldout_s=round(life_s), heldout=res, wall_s=round(time.time() - t0))
    if a.out:
        json.dump(rep, open(a.out, "w"), indent=1)
        print("report", a.out)


if __name__ == "__main__":
    main()
