#!/usr/bin/env python3
"""Round-6 acceptance on calls the model never trained on, scored the way the robot hears them.

For every held-out call in data/new_heldout_v6.json (the 11-11 evening life calls and the four calls Shawn counted on
2026-11-12 00:56), each ear is streamed alone through the model (namecall.py's per-ear OwwSpotter) at eight 10 ms
offsets of the 80 ms frame grid; a call's score at one offset is the larger ear's best frame within -0.3..+1.6 s of
its burst start. A call counts as heard at an offset when that score reaches --thr.

  ~/.venvs/oww/bin/python score_v6.py --model models/mochi_v6.onnx [--model models/mochi_v4.onnx ...] --out results/v6_new.json
"""
import argparse
import json
import os
import wave

import numpy as np
from openwakeword.model import Model

OWW = "/Users/shawnxiang/mochi-train/oww"
FS = 16000
OFFSETS = range(0, 1280, 160)


def read(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, w.getnchannels())


def ear_scores(m, key, x16, off):
    m.reset()
    y = np.concatenate([np.zeros(FS * 2 + off, np.int16), x16])
    n = len(y) // 1280
    ts = (np.arange(1, n + 1) * 1280 - 2 * FS - off) / FS
    ps = np.array([m.predict(y[i * 1280:(i + 1) * 1280])[key] for i in range(n)])
    return ts, ps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", required=True)
    ap.add_argument("--heldout", default=os.path.join(OWW, "data", "new_heldout_v6.json"))
    ap.add_argument("--thr", type=float, default=0.7)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    held = json.load(open(a.heldout))
    res = {}
    for path in a.model:
        key = os.path.splitext(os.path.basename(path))[0]
        m = Model(wakeword_models=[path], inference_framework="onnx")
        calls = []
        for nm, h in held.items():
            x = read(h["file"])
            per_off = {s: [] for s in h["starts"]}
            for off in OFFSETS:
                tr = [ear_scores(m, key, x[:, ch].copy(), off) for ch in (0, 1)]
                for s in h["starts"]:
                    best = 0.0
                    for ts, ps in tr:
                        sel = (ts >= s - 0.3) & (ts <= s + 1.6)
                        if sel.any():
                            best = max(best, float(ps[sel].max()))
                    per_off[s].append(best)
            for s, v in per_off.items():
                calls.append(dict(file=nm, start=s, scores=[round(p, 3) for p in v], counted=bool(h.get("counted_by_shawn"))))
        def summ(cs):
            if not cs:
                return {}
            heard = [sum(p >= a.thr for p in c["scores"]) for c in cs]
            return dict(n=len(cs), heard_at_7_of_8=sum(h >= 7 for h in heard), heard_at_any=sum(h >= 1 for h in heard),
                        mean_offsets_heard=round(float(np.mean(heard)) / 8, 3),
                        median_score=round(float(np.median([np.median(c["scores"]) for c in cs])), 3))
        res[key] = dict(all=summ(calls), counted_1112=summ([c for c in calls if c["counted"]]),
                        evening_1111=summ([c for c in calls if not c["counted"]]), calls=calls)
        print(key, json.dumps({k: v for k, v in res[key].items() if k != "calls"}))
    json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
