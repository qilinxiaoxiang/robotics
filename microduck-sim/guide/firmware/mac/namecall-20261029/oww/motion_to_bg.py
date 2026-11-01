#!/usr/bin/env python3
"""Turn a record_motion_noise.py capture (A7Z, 4 ch S32_LE 48 kHz) into round-4 background clips: 2 s, 16 kHz mono
int16 wav, one set per ear and one of the two-ear mix (the spotter scores each ear stream), hopping 1 s. The first and
the last 20 % of every segment are cut into separate files named _hold so the held-out motion test (eval_motion.py)
never sees training chunks.

  python3 motion_to_bg.py motion_noise_X.raw --out bg_motion/   (MacBook; scp the folder to the Mac mini)
"""
import argparse
import json
import os
import wave

import numpy as np
from scipy.signal import resample_poly

FS_IN, FS = 48000, 16000


def wwrite(path, y):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes(np.clip(y * 32767, -32768, 32767).astype("<i2").tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    meta = json.load(open(a.raw + ".json"))
    x = (np.fromfile(a.raw, "<i4").reshape(-1, 4)[:, :2] >> 8).astype(np.float64) / 2 ** 23
    x -= x.mean(axis=0)
    streams = {"L": x[:, 0], "R": x[:, 1], "mix": x.mean(axis=1)}
    y = {k: resample_poly(v, 1, 3) for k, v in streams.items()}
    stem = os.path.splitext(os.path.basename(a.raw))[0]
    n_train = n_hold = 0
    for i, s in enumerate(meta["segments"]):
        a0, a1 = int(s["start_s"] * FS), int(s["end_s"] * FS)
        cut = int(0.2 * (a1 - a0))
        for part, (b0, b1) in (("train", (a0 + cut, a1 - cut)), ("hold", (a0, a0 + cut))):
            for k, v in y.items():
                for c0 in range(b0, b1 - 2 * FS + 1, FS):
                    name = f"{stem}_{i:02d}_{s['kind']}_{k}_{c0 // FS:04d}{'_hold' if part == 'hold' else ''}.wav"
                    wwrite(os.path.join(a.out, name), v[c0:c0 + 2 * FS])
                    n_train += part == "train"
                    n_hold += part == "hold"
    print(f"{n_train} training clips, {n_hold} held-out clips -> {a.out}")


if __name__ == "__main__":
    main()
