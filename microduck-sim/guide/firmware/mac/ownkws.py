"""The duck's own name spotter: a small log-mel time-convolution network trained on Shawn's recorded "Mochi" calls (namecall-20261029/
train_mochi.py), run in numpy on the A7Z. It replaces the public sherpa-onnx keyword model, which transcribed his
calls as ONCE / MONTY / I and never fired on the robot (PET_ROBOT_LOG 2026-10-30).

Features: the two ears downmixed to 16 kHz (namecall.Decimate3), 40 log-mel bands over 25 ms frames every 10 ms,
a WINDOW_S window, the mean over time removed per band (level and channel colour drop out). Model (the recipe of the
Edge Impulse keyword lab, 18-763 lecture 21: spectral features, a small time convolution, the keyword against
"other speech" and "noise / silence" classes): three conv + max-pool layers over time, a global max over time (so the
word may sit anywhere in the window), a dense softmax; weights in an .npz (OwnModel). Scoring runs
every SCORE_EVERY blocks (100 ms) on the newest window; a hit is the first score at or over the threshold, then
REFRACTORY_S of quiet. OwnSpotter.feed() has the KeywordGate interface (t, block, silent) -> hit dict or None, so
namecall.NameCall uses it unchanged (its detector onsets still fix the word start and the direction).
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

FS16 = 16000
N_FFT = 512
WIN = 400            # 25 ms
HOP = 160            # 10 ms
N_MELS = 40
F_LO, F_HI = 100.0, 7000.0
WINDOW_S = 1.0       # scored window; a call is 0.3-0.6 s, PRE_S of it before the detector onset
PRE_S = 0.15
N_FRAMES = (int(WINDOW_S * FS16) - WIN) // HOP + 1           # 98, what logmel() yields for a WINDOW_S signal
SCORE_EVERY = 5      # blocks of 20 ms
REFRACTORY_S = 1.0
MODEL_DEFAULT = os.path.join(HERE, "namecall-20261029", "models", "mochi_own.npz")


def _hz_to_mel(f):
    return 2595.0 * np.log10(1.0 + f / 700.0)


def _mel_to_hz(m):
    return 700.0 * (10 ** (m / 2595.0) - 1.0)


def mel_filterbank(n_mels=N_MELS, n_fft=N_FFT, fs=FS16, f_lo=F_LO, f_hi=F_HI):
    edges = _mel_to_hz(np.linspace(_hz_to_mel(f_lo), _hz_to_mel(f_hi), n_mels + 2))
    bins = np.floor((n_fft + 1) * edges / fs).astype(int)
    fb = np.zeros((n_mels, n_fft // 2 + 1), np.float32)
    for m in range(n_mels):
        a, b, c = bins[m], bins[m + 1], bins[m + 2]
        if b == a:
            b = a + 1
        if c == b:
            c = b + 1
        fb[m, a:b] = (np.arange(a, b) - a) / (b - a)
        fb[m, b:c] = (c - np.arange(b, c)) / (c - b)
    return fb


_FB = mel_filterbank()
_HANN = np.hanning(WIN).astype(np.float32)


def logmel(y):
    """(frames, N_MELS) log-mel of a 16 kHz float signal, mean over time removed per band."""
    y = np.asarray(y, np.float32)
    n = (len(y) - WIN) // HOP + 1
    if n < 1:
        return np.zeros((0, N_MELS), np.float32)
    idx = np.arange(WIN)[None, :] + HOP * np.arange(n)[:, None]
    frames = y[idx] * _HANN
    spec = np.abs(np.fft.rfft(frames, N_FFT, axis=1)) ** 2
    mel = spec @ _FB.T
    lm = np.log10(mel + 1e-10)
    return (lm - lm.mean(axis=0, keepdims=True)).astype(np.float32)


def window_features(y16, start_s):
    """Flattened log-mel of the WINDOW_S window starting at start_s (zero padded), or None when it runs past the end."""
    i0 = int(round(start_s * FS16))
    n = int(WINDOW_S * FS16)
    if i0 < 0:
        y = np.concatenate([np.zeros(-i0, np.float32), y16[: max(0, n + i0)]])
    else:
        y = y16[i0:i0 + n]
    if len(y) < n:
        if len(y) < 0.6 * n:
            return None
        y = np.concatenate([y, np.zeros(n - len(y), np.float32)])
    lm = logmel(y)
    return lm[:N_FRAMES].reshape(-1)


class OwnModel:
    """Time-convolution classifier over a log-mel window, numpy only.

    npz keys: conv{i}_w (k, c_in, c_out), conv{i}_b, pool{i} (time max-pool after conv i, 1 = none), dense_w (c, n_cls),
    dense_b, mu / sd (per mel band, applied before conv0), threshold, classes (str array; "mochi" is the target).
    Layers: conv (same padding) -> ReLU -> max-pool, repeated; global max over time; dense; softmax."""

    def __init__(self, path=MODEL_DEFAULT):
        d = np.load(path, allow_pickle=False)
        self.convs = []
        i = 0
        while f"conv{i}_w" in d:
            self.convs.append((d[f"conv{i}_w"].astype(np.float32), d[f"conv{i}_b"].astype(np.float32), int(d[f"pool{i}"])))
            i += 1
        self.dw, self.db = d["dense_w"].astype(np.float32), d["dense_b"].astype(np.float32)
        self.mu, self.sd = d["mu"].astype(np.float32), d["sd"].astype(np.float32)
        self.threshold = float(d["threshold"])
        self.classes = [str(c) for c in d["classes"]]
        self.target = self.classes.index("mochi")
        self.path = path

    @staticmethod
    def _conv(x, w, b):
        """x (B, T, C_in), w (k, C_in, C_out), same padding."""
        k = w.shape[0]
        p = k // 2
        xp = np.pad(x, ((0, 0), (p, k - 1 - p), (0, 0)))
        out = np.zeros((x.shape[0], x.shape[1], w.shape[2]), np.float32)
        for j in range(k):
            out += xp[:, j:j + x.shape[1], :] @ w[j]
        return out + b

    def probs(self, feats):
        x = np.asarray(feats, np.float32).reshape(-1, N_FRAMES, N_MELS)
        x = (x - self.mu) / self.sd
        for w, b, pool in self.convs:
            x = np.maximum(self._conv(x, w, b), 0.0)
            if pool > 1:
                t = x.shape[1] // pool * pool
                x = x[:, :t].reshape(x.shape[0], t // pool, pool, x.shape[2]).max(axis=2)
        z = x.max(axis=1) @ self.dw + self.db
        z = z - z.max(axis=1, keepdims=True)
        e = np.exp(z)
        return e / e.sum(axis=1, keepdims=True)

    def score(self, feats):
        """P(mochi) for one flattened window (float) or a batch of rows (array)."""
        p = self.probs(feats)[:, self.target]
        return p if p.shape[0] > 1 else float(p[0])


class OwnSpotter:
    """KeywordGate stand-in: feed(t, block, silent) -> None or dict(t_hit, keyword, tokens, span_s)."""

    def __init__(self, model_path=MODEL_DEFAULT, ears=(0, 1), threshold=None, gain_db=0.0):
        import namecall as nc
        self.nc = nc
        self.model = OwnModel(model_path)
        self.threshold = self.model.threshold if threshold is None else float(threshold)
        self.ears = list(ears)
        self.gain = 10 ** (gain_db / 20.0)
        self.model_dir, self.keywords_file = model_path, None
        self.hits = 0
        self.reset()

    def reset(self):
        self.dec = self.nc.Decimate3()
        self.ring = np.zeros(int(WINDOW_S * FS16) + 3200, np.float32)
        self.n_blocks = 0
        self.last_hit_t = -1e9
        self.last_p = 0.0

    def feed(self, t, block, silent=False):
        x = block[:, self.ears].mean(axis=1) if block.ndim == 2 else block
        y = self.dec(x) * self.gain
        if silent:
            y = np.zeros_like(y)
        self.ring = np.concatenate([self.ring[len(y):], y.astype(np.float32)])
        self.n_blocks += 1
        if self.n_blocks % SCORE_EVERY:
            return None
        t_end = t + len(x) / self.nc.FS
        if t_end - self.last_hit_t < REFRACTORY_S:
            return None
        n = int(WINDOW_S * FS16)
        feats = logmel(self.ring[-n:])[:N_FRAMES].reshape(-1)
        p = self.model.score(feats)
        self.last_p = p
        if p >= self.threshold:
            self.hits += 1
            self.last_hit_t = t_end
            return dict(t_hit=round(t_end, 3), keyword="MOCHI", tokens=[round(p, 3)], span_s=None)
        return None
