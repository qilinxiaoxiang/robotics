"""Duck calls with per-call pitch and length: the existing real recordings, resampled (pitch) and overlap-add
stretched (length). No new audio assets.

Sources, in order: walk_wired.py's --sounds folder next to walk_brain.py (built by bringup/scripts/build_duck_calls.py),
then Pollen's microduck-simulator voices (duck1..duck4/chirp_*.wav), which that script cuts from. Rendered calls go to
pet/express/out/audio/, which git ignores: the recordings' licence is Pollen's and Commons', not ours to republish.

On the robot duck_sound.Voice plays a file per call with aplay; the plan there is a small bank rendered at start
(each recording at 5 pitches x 3 lengths) and the nearest variant played per call event.
"""
import glob
import os
import wave

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SOURCES = (
    os.path.join(ROOT, "microduck-sim", "guide", "firmware", "mac", "sounds", "*.wav"),
    os.path.join(ROOT, "microduck-sim", "microduck-simulator", "app", "public", "assets", "voices", "duck*", "chirp_*.wav"),
)


def find_calls():
    for pat in SOURCES:
        files = sorted(glob.glob(pat))
        if files:
            return files
    return []


def read_wav(path):
    with wave.open(path) as w:
        rate, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    x = np.frombuffer(raw, dtype={1: np.uint8, 2: np.int16, 4: np.int32}[sw]).astype(float)
    if sw == 1:
        x = x - 128
    x = x.reshape(-1, ch).mean(axis=1) / float(2 ** (8 * sw - 1))
    return x, rate


def write_wav(path, x, rate):
    y = np.clip(x, -1, 1)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((y * 32767).astype(np.int16).tobytes())


def resample(x, factor):
    """Play `factor` times faster: pitch x factor, length / factor (linear interpolation)."""
    n = max(2, int(round(len(x) / factor)))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)


def ola_stretch(x, factor, win=1024, tol=256):
    """Length x factor at the same pitch: WSOLA (waveform-similarity overlap-add). Each analysis frame is shifted by up
    to `tol` samples to line up with the natural continuation of the previous one, so tones keep their phase."""
    if abs(factor - 1.0) < 1e-3:
        return x.copy()
    if len(x) < win + 2 * tol:
        return resample(x, 1.0 / factor)
    hs = win // 2
    w = np.hanning(win)
    n_out = int(len(x) * factor)
    nfr = max(1, (n_out - win) // hs + 1)
    out = np.zeros(hs * (nfr - 1) + win)
    norm = np.zeros_like(out)
    xp = np.concatenate([np.zeros(tol), x, np.zeros(win + 2 * tol)])
    prev = 0
    for i in range(nfr):
        nominal = int(round(i * hs / factor))
        if i == 0:
            a = nominal
        else:
            want = xp[tol + prev + hs:tol + prev + hs + win]   # what would follow the previous frame naturally
            lo = max(0, nominal - tol)
            seg = xp[tol + lo:tol + nominal + tol + win]
            c = np.correlate(seg, want, mode="valid")
            a = lo + int(np.argmax(c))
        out[i * hs:i * hs + win] += xp[tol + a:tol + a + win] * w
        norm[i * hs:i * hs + win] += w
        prev = a
    return (out / np.maximum(norm, 1e-3))[:n_out]


def render_call(x, pitch=1.0, stretch=1.0, gain_db=0.0):
    """pitch: frequency factor; stretch: final length relative to the recording."""
    y = resample(x, pitch)
    y = ola_stretch(y, stretch * pitch)
    return y * 10 ** (gain_db / 20)


class CallPicker:
    """Random recording per call, never the same file twice in a row."""

    def __init__(self, files, rng):
        self.files, self.rng, self.last = list(files), rng, None

    def pick(self):
        if not self.files:
            return None
        choices = [f for f in self.files if f != self.last] or self.files
        self.last = choices[int(self.rng.integers(len(choices)))]
        return self.last
