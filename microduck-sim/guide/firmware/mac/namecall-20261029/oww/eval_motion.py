#!/usr/bin/env python3
"""Does the spotter hear "Mochi" while the duck moves? Scores spotter models with the robot's own scorer
(ownkws.OwwSpotter, max over the two ear streams) on the eight held-out calls of calls_200910.wav (home, 2 m, eight
directions, eightdir_20261030.json) with the duck's own motion noise (record_motion_noise.py, the held-out first 20 %
of each motion segment) added sample by sample at its recorded level, both at 48 kHz on the same microphones.
Also counts false peaks on the motion noise alone.

  ~/.venvs/duck-see/bin/python eval_motion.py motion_noise_X.raw --models mochi_v3.onnx mochi_v4.onnx [--out f.json]
(MacBook; reads recordings/calls_200910.wav)
"""
import argparse
import json
import os
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import namecall as nc  # noqa: E402
import ownkws as ok  # noqa: E402

THR = (0.5, 0.7)
F = ok.OWW_FRAME


def ears16(x48):
    return np.stack([nc.Decimate3()(x48[:, c]) for c in (0, 1)], axis=1).astype(np.float32)


def stream(sp, x):
    sp.reset()
    out = []
    for k in range(0, len(x) - F + 1, F):
        ps = []
        for st, c in zip(sp.streams, (0, 1)):
            sp._frame(x[k:k + F, c], st)
            ps.append(sp.score(st))
        out.append(((k + F) / 16000, max(ps)))
    return np.array(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    with wave.open(os.path.join(HERE, "recordings", "calls_200910.wav")) as w:
        calls = (np.frombuffer(w.readframes(w.getnframes()), np.int32).reshape(-1, w.getnchannels()) >> 8).astype(np.float64) / 2 ** 23
    t_calls = [c["t_s"] for c in json.load(open(os.path.join(HERE, "eightdir_20261030.json")))["calls"]]
    meta = json.load(open(a.raw + ".json"))
    noise = (np.fromfile(a.raw, "<i4").reshape(-1, 4) >> 8).astype(np.float64) / 2 ** 23
    noise -= noise.mean(axis=0)
    holds = []
    for s in meta["segments"]:
        a0 = int(s["start_s"] * 48000)
        holds.append((s["kind"], noise[a0:a0 + int(0.2 * (s["end_s"] - s["start_s"]) * 48000)]))
    res = {}
    for m in a.models:
        sp = ok.OwwSpotter(m)
        r = dict(by_kind={}, noise_false={})
        for kind in sorted({k for k, _ in holds}):
            segs = [h for k, h in holds if k == kind]
            nz = np.concatenate(segs)
            peaks, hit = [], {thr: 0 for thr in THR}
            for i, tc in enumerate(t_calls):
                c0 = int((tc - 1.0) * 48000)
                clip = calls[c0:c0 + 3 * 48000].copy()
                off = (i * 48000) % max(1, len(nz) - len(clip))
                clip[:, :4] += nz[off:off + len(clip), :4] if len(nz) >= len(clip) else 0
                rows = stream(sp, ears16(clip))
                p = float(rows[(rows[:, 0] >= 1.0) & (rows[:, 0] <= 2.6), 1].max())
                peaks.append(round(p, 2))
                for thr in THR:
                    hit[thr] += p >= thr
            rows = stream(sp, ears16(nz))
            r["by_kind"][kind] = dict(peaks=peaks, **{f"hits_{thr}": f"{hit[thr]}/{len(t_calls)}" for thr in THR})
            r["noise_false"][kind] = {f"thr{thr}": int((rows[:, 1] >= thr).sum() > 0) for thr in THR}
        clean = stream(sp, ears16(calls[int((t_calls[0] - 1) * 48000):int((t_calls[-1] + 2) * 48000)]))
        r["clean_peaks"] = [round(float(clean[(clean[:, 0] >= tc - t_calls[0] + 1.0) & (clean[:, 0] <= tc - t_calls[0] + 2.6), 1].max()), 2) for tc in t_calls]
        res[os.path.basename(m)] = r
        print(os.path.basename(m), json.dumps(r), flush=True)
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
