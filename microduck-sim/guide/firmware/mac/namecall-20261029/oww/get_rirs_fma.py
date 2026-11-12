"""MIT room impulse responses (and, time permitting, 1 hour of FMA music) as in openWakeWord's
notebooks/automatic_model_training.ipynb, saved as 16 kHz wavs. Usage: get_rirs_fma.py [rirs|fma]"""
import os
import sys
import time
import wave

import numpy as np
import scipy.io.wavfile
import datasets
from scipy.signal import resample_poly
from math import gcd

OUT = "/Users/shawnxiang/mochi-train/oww/data"


def wwrite(path, y, fs=16000):
    y = np.clip(np.asarray(y, np.float32) * 32767, -32768, 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(fs)
        w.writeframes(y.tobytes())


def to16k(x, fs):
    x = np.asarray(x, np.float32)
    if x.ndim > 1:
        x = x.mean(axis=-1)
    if fs != 16000:
        g = gcd(16000, fs)
        x = resample_poly(x, 16000 // g, fs // g)
    return x


def rirs():
    d = os.path.join(OUT, "mit_rirs")
    os.makedirs(d, exist_ok=True)
    ds = datasets.load_dataset("davidscripka/MIT_environmental_impulse_responses", split="train", streaming=True)
    n = 0
    for row in ds:
        a = row["audio"]
        name = os.path.basename(a.get("path") or f"rir_{n}.wav")
        if not name.endswith(".wav"):
            name += ".wav"
        wwrite(os.path.join(d, name), to16k(a["array"], a["sampling_rate"]))
        n += 1
    print("rirs", n)


def fma(max_s=3600, budget_s=900):
    d = os.path.join(OUT, "fma")
    os.makedirs(d, exist_ok=True)
    t0 = time.time()
    ds = datasets.load_dataset("rudraml/fma", name="small", split="train", streaming=True)
    ds = iter(ds.cast_column("audio", datasets.Audio(sampling_rate=16000)))
    tot, n = 0.0, 0
    while tot < max_s and time.time() - t0 < budget_s:
        row = next(ds)
        a = row["audio"]
        x = to16k(a["array"], a["sampling_rate"])
        wwrite(os.path.join(d, f"fma_{n:04d}.wav"), x)
        tot += len(x) / 16000
        n += 1
    print("fma", n, round(tot), "s", round(time.time() - t0), "s wall")


if __name__ == "__main__":
    {"rirs": rirs, "fma": fma}[sys.argv[1]]()
