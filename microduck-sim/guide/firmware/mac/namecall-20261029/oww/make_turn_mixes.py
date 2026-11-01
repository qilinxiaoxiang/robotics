#!/usr/bin/env python3
"""Fixed test mixtures for front-end trials (denoisers, impact suppression): the eight held-out home calls
(calls_200910.wav, decimated to 16 kHz, ears 0/1) each 3 s long, with the held-out 10/31 turn noise (life_motion_bg
hold/*.npy) added at -6 dB (the live post-glue call level), 0 dB and +6 dB; plus each call clean and 3 s of the noise
alone per call. 1 s of noise leads every clip. Writes 2-channel 16 kHz int16 wavs and mixes.json (call window per clip).

  python3 oww/make_turn_mixes.py recordings/bg_motion_life2 OUT_DIR
"""
import glob
import json
import os
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import namecall as nc  # noqa: E402

FS = 16000


def wwrite(path, y):
    with wave.open(path, "wb") as w:
        w.setnchannels(y.shape[1])
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes(np.clip(y * 32767, -32768, 32767).astype("<i2").tobytes())


def main():
    bg, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    with wave.open(os.path.join(HERE, "recordings", "calls_200910.wav")) as w:
        x48 = (np.frombuffer(w.readframes(w.getnframes()), np.int32).reshape(-1, w.getnchannels()) >> 8).astype(np.float64) / 2 ** 23
    calls = np.stack([nc.Decimate3()(x48[:, c]) for c in (0, 1)], axis=1)
    tcs = [c["t_s"] for c in json.load(open(os.path.join(HERE, "eightdir_20261030.json")))["calls"]]
    noise = np.concatenate([np.load(p)[:, :2] for p in sorted(glob.glob(os.path.join(bg, "hold", "*.npy")))]).astype(float)
    meta = {}
    for i, tc in enumerate(tcs):
        c0 = int((tc - 1) * FS)
        clip = calls[c0:c0 + 3 * FS]
        off = (i * 2 * FS) % (len(noise) - 4 * FS)
        n = noise[off:off + 4 * FS]
        for tag, g in (("clean", None), ("m6", -6), ("p0", 0), ("p6", 6), ("noise", "only")):
            y = np.zeros((4 * FS, 2))
            if g == "only":
                y += n
            else:
                y[FS:] += clip
                if g is not None:
                    y += 10 ** (g / 20) * n
            name = f"call{i}_{tag}.wav"
            wwrite(os.path.join(out, name), y)
            meta[name] = dict(call=i, cond=tag, window_s=[2.0, 3.6] if g != "only" else None)
    json.dump(meta, open(os.path.join(out, "mixes.json"), "w"), indent=1)
    print(len(meta), "clips ->", out)


if __name__ == "__main__":
    main()
