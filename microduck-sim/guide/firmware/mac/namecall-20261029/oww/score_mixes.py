#!/usr/bin/env python3
"""Score a folder of make_turn_mixes.py clips (raw or after a front end) with spotter models, the robot's scorer
(ownkws.OwwSpotter, max over the two ears): hits at 0.5/0.7 per condition, peaks, and the highest score on the
turn noise alone.

  ~/.venvs/duck-see/bin/python oww/score_mixes.py DIR --models a.onnx b.onnx
"""
import argparse
import glob
import json
import os
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [HERE, os.path.dirname(HERE), os.path.join(HERE, "oww")]
import ownkws as ok  # noqa: E402
import eval_motion as em  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--meta", default=None, help="mixes.json (default: DIR/mixes.json, else ../in/mixes.json)")
    a = ap.parse_args()
    mp = a.meta or next(p for p in (os.path.join(a.dir, "mixes.json"), os.path.join(a.dir, "..", "in", "mixes.json")) if os.path.exists(p))
    meta = json.load(open(mp))
    res = {}
    for m in a.models:
        sp = ok.OwwSpotter(m)
        by = {}
        for name, info in sorted(meta.items()):
            with wave.open(os.path.join(a.dir, name)) as w:
                x = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, w.getnchannels()).astype(np.float32) / 32768
            r = em.stream(sp, x)
            if info["window_s"]:
                lo, hi = info["window_s"]
                p = float(r[(r[:, 0] >= lo) & (r[:, 0] <= hi), 1].max())
            else:
                p = float(r[:, 1].max())
            by.setdefault(info["cond"], []).append(round(p, 2))
        out = {}
        for cond, ps in by.items():
            if cond == "noise":
                out[cond] = dict(max=max(ps), over_0_5=sum(p >= 0.5 for p in ps))
            else:
                out[cond] = dict(hits_0_7=f"{sum(p >= 0.7 for p in ps)}/{len(ps)}", hits_0_5=f"{sum(p >= 0.5 for p in ps)}/{len(ps)}", peaks=ps)
        res[os.path.basename(m)] = out
        print(os.path.basename(m), json.dumps({k: (v.get("hits_0_7"), v.get("hits_0_5")) if "peaks" in v else v for k, v in out.items()}), flush=True)
    return res


if __name__ == "__main__":
    main()
