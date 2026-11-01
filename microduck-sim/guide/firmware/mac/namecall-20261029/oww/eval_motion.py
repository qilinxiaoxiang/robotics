#!/usr/bin/env python3
"""Does the spotter hear "Mochi" while the duck turns? Scores spotter models with the robot's own scorer
(ownkws.OwwSpotter, max over the two ear streams) on the eight held-out calls of calls_200910.wav (home, 2 m, eight
directions, eightdir_20261030.json), decimated to 16 kHz, with the held-out body-turn noise of the 10/31 20:21 run
(life_motion_bg.py hold/*.npy, cut from the duck's own life log) added at -6 dB (the post-glue live call level relative to these pre-glue calls), its recorded level and +6 dB.
Also counts false peaks on the turn noise alone and prints the peaks over the voiced spans inside it (speech of
unknown content: reported, never counted as calls).

  ~/.venvs/duck-see/bin/python oww/eval_motion.py recordings/bg_motion_life --models a.onnx b.onnx [--out f.json]
"""
import argparse
import glob
import json
import os
import sys
import wave

import numpy as np
from scipy.signal import butter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [HERE, os.path.dirname(HERE), os.path.join(HERE, "oww")]
import namecall as nc  # noqa: E402
import ownkws as ok  # noqa: E402
import life_motion_bg as lb  # noqa: E402

THR = (0.5, 0.7)
F = ok.OWW_FRAME
FS = 16000


def stream(sp, x):
    sp.reset()
    out = []
    for k in range(0, len(x) - F + 1, F):
        ps = []
        for st, c in zip(sp.streams, (0, 1)):
            sp._frame(x[k:k + F, c], st)
            ps.append(sp.score(st))
        out.append(((k + F) / FS, max(ps)))
    return np.array(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bg_dir")
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    with wave.open(os.path.join(HERE, "recordings", "calls_200910.wav")) as w:
        x48 = (np.frombuffer(w.readframes(w.getnframes()), np.int32).reshape(-1, w.getnchannels()) >> 8).astype(np.float64) / 2 ** 23
    calls = np.stack([nc.Decimate3()(x48[:, c]) for c in (0, 1)], axis=1).astype(np.float32)
    t_calls = [c["t_s"] for c in json.load(open(os.path.join(HERE, "eightdir_20261030.json")))["calls"]]
    holds = {os.path.basename(p): np.load(p)[:, :2] for p in sorted(glob.glob(os.path.join(a.bg_dir, "hold", "*.npy")))}
    noise = np.concatenate(list(holds.values()))
    sos = butter(4, (300, 1500), "bandpass", fs=FS, output="sos")
    res = {}
    for m in a.models:
        sp = ok.OwwSpotter(m)
        r = {}
        for gain_db in (-6, 0, 6):
            g = 10 ** (gain_db / 20)
            peaks = []
            for i, tc in enumerate(t_calls):
                c0 = int((tc - 1.0) * FS)
                clip = calls[c0:c0 + 3 * FS].copy()
                off = (i * 2 * FS) % (len(noise) - len(clip))
                clip += g * noise[off:off + len(clip)]
                rows = stream(sp, clip)
                peaks.append(round(float(rows[(rows[:, 0] >= 1.0) & (rows[:, 0] <= 2.6), 1].max()), 2))
            r[f"turn_noise_{gain_db:+d}dB"] = dict(peaks=peaks, **{f"hits_{t}": f"{sum(p >= t for p in peaks)}/{len(peaks)}" for t in THR})
        rows = stream(sp, calls[int((t_calls[0] - 1) * FS):int((t_calls[-1] + 2) * FS)])
        r["clean_peaks"] = [round(float(rows[(rows[:, 0] >= tc - t_calls[0] + 1.0) & (rows[:, 0] <= tc - t_calls[0] + 2.6), 1].max()), 2) for tc in t_calls]
        r["clean_hits_0.7"] = f"{sum(p >= 0.7 for p in r['clean_peaks'])}/{len(t_calls)}"
        false, voiced = {}, {}
        for name, h in holds.items():
            rows = stream(sp, h)
            false[name] = {f"thr{t}": int((rows[:, 1] >= t).any()) for t in THR}
            mk = lb.speech_mask(np.pad(h, ((0, 0), (0, 1))), sos)
            d = np.diff(np.r_[0, mk.astype(int), 0])
            for s0, s1 in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
                sel = (rows[:, 0] >= s0 / FS) & (rows[:, 0] <= s1 / FS + 0.6)
                voiced[f"{name}@{s0 / FS:.1f}s"] = round(float(rows[sel, 1].max()), 2)
        r["turn_noise_alone_any_peak"] = false
        r["voiced_spans_in_turns_peak"] = voiced
        res[os.path.basename(m)] = r
        print(os.path.basename(m), json.dumps(r), flush=True)
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
