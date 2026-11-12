"""Shim so openwakeword/train.py (which does `from generate_samples import generate_samples` and passes no model) can
use piper-sample-generator 3.2.0 (package `piper_sample_generator`, generate_samples(model=...) required).

Adds the piper-sample-generator checkout to sys.path (its `piper_train` package is not installed by pip), fixes the
LibriTTS-R generator model path, drops the kwargs the old API had (auto_reduce_batch_size), and resamples the
22050 Hz output of the generator to 16 kHz in place, as the old generate_samples.py did.
"""
import os
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PSG = os.path.join(os.path.dirname(HERE), "piper-sample-generator")
if PSG not in sys.path:
    sys.path.insert(0, PSG)
MODEL = os.path.join(os.path.dirname(HERE), "dl", "en_US-libritts_r-medium.pt")

from piper_sample_generator.__main__ import generate_samples as _gen  # noqa: E402


def _to16k(path):
    with wave.open(path) as w:
        fs, n = w.getframerate(), w.getnframes()
        x = np.frombuffer(w.readframes(n), np.int16)
    if fs == 16000:
        return
    from math import gcd
    from scipy.signal import resample_poly
    g = gcd(16000, fs)
    y = resample_poly(x.astype(np.float32), 16000 // g, fs // g)
    y = np.clip(y, -32768, 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(y.tobytes())


def generate_samples(text, output_dir, max_samples=None, batch_size=1, file_names=None, **kw):
    kw.pop("auto_reduce_batch_size", None)
    # the VITS generator's torch.jit fused ops fail on Apple MPS ("Unknown device for graph fuser", torch 2.5.1),
    # so the generator runs on the CPU
    import torch
    torch.backends.mps.is_available = lambda: False
    before = set(os.listdir(output_dir)) if os.path.isdir(output_dir) else set()
    _gen(text=text, output_dir=output_dir, model=MODEL, max_samples=max_samples, batch_size=batch_size,
         file_names=file_names, max_speakers=900, **kw)
    for f in sorted(set(os.listdir(output_dir)) - before):
        if f.endswith(".wav"):
            _to16k(os.path.join(output_dir, f))
