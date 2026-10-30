"""Duck recordings (A7Z .raw / 4-channel or 2-channel .wav) -> 16 kHz float32 .npy for train_mochi.py.

Per recording NAME it writes NAME.npy, the two ears averaged exactly as the spotter hears them on the robot
(namecall.Decimate3 of mean(ch0, ch1)), and NAME@ch0.npy, NAME@ch1.npy, NAME@ch2.npy, each microphone alone (left
ear, right ear, back mic; ch3 is empty), so every microphone's copy of a call or a non-call is its own training
sample. A channel more than 60 dB under the loudest is skipped (not fitted / dead).

  python3 to_mono16.py --out DIR recordings/raw/*.raw recordings/*.wav
"""
import argparse
import os
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import namecall as nc  # noqa: E402

try:
    from scipy.signal import resample_poly
except ImportError:                     # only needed for recordings not at 48 kHz
    resample_poly = None


def load(path):
    """(samples, channels) float in -1..1 and the rate."""
    if path.endswith(".raw"):
        x = np.fromfile(path, "<i4")
        x = x[: len(x) // 4 * 4].reshape(-1, 4) >> 8
        return x.astype(np.float32) / 2 ** 23, 48000
    with wave.open(path) as w:
        n, sw, fs = w.getnchannels(), w.getsampwidth(), w.getframerate()
        b = w.readframes(w.getnframes())
    if sw == 4:
        x = (np.frombuffer(b, "<i4").reshape(-1, n) >> 8).astype(np.float32) / 2 ** 23
    else:
        x = np.frombuffer(b, "<i2").reshape(-1, n).astype(np.float32) / 32768
    return x, fs


def to16(m, fs):
    if fs == 16000:                     # life_log.py segments are already the decimated stream
        return m.astype(np.float32)
    if fs == 48000:
        d = nc.Decimate3()
        return np.concatenate([d(m[i:i + 960]) for i in range(0, len(m), 960)]).astype(np.float32)
    g = np.gcd(16000, fs)
    return resample_poly(m, 16000 // g, fs // g).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--prefix", default="", help="prepended to each name (life log: life_20261030_ for day folder 20261030)")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for p in a.files:
        name = a.prefix + os.path.splitext(os.path.basename(p))[0]
        x, fs = load(p)
        np.save(os.path.join(a.out, name + ".npy"), to16(x[:, :2].mean(axis=1), fs))
        lv = [20 * np.log10(np.sqrt((x[:, c].astype(np.float64) ** 2).mean()) + 1e-12) for c in range(x.shape[1])]
        kept = [c for c in range(min(3, x.shape[1])) if lv[c] > max(lv) - 60]
        for c in kept:
            np.save(os.path.join(a.out, f"{name}@ch{c}.npy"), to16(x[:, c], fs))
        print(f"{name}: {len(x) / fs:.1f} s, channels {kept}")


if __name__ == "__main__":
    main()
