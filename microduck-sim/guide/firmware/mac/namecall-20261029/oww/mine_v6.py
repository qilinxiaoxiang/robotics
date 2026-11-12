#!/usr/bin/env python3
"""Round 6 positives: find Shawn's Mochi calls in the life log since 2026-10-31 without labelling by hand.

Why: v4 learned 77 real calls from 10/29-10/30 only. On 2026-11-12 00:56 four quiet-room calls (voice-band SNR
17-24 dB) scored 0.60, 0.21, 0.49, 0.90, and the same call moved 0.01-0.62 when the 80 ms frame grid shifted 10 ms:
the model sits on the edge for new calls. The life log since then holds many more of his calls, unlabelled.

A candidate is a template-match peak (mine_calls.py's method: 0.6 s per-band-normalised log-mel, best normalised
correlation with any of the 77 training calls, z-scored against the file's own scores) whose voiced burst
(300-4000 Hz envelope, BURST_DB over the window floor, gaps under 0.2 s bridged) is 0.30-1.0 s long. Each candidate
also carries v4's best score over four 20 ms frame offsets and the live index score near it. Whisper is not used:
on these quiet life segments it invents "Mochi" when prompted and reads nothing when not (2026-11-12).

--validate runs the same miner on recordings whose truth is known (held-out duck calls from duck_heldout_v3.json;
Shawn's no-call talk in life_heldout.json) and prints found / false candidates per rule, so the accept rule is
chosen on data the round-6 model is never trained or tested on.

  ~/.venvs/oww/bin/python mine_v6.py --validate
  ~/.venvs/oww/bin/python mine_v6.py --life ~/mochi-train/life_v6 --out ~/mochi-train/oww/data/mine_v6.json
"""
import argparse
import glob
import json
import os
import wave

import numpy as np
from scipy.signal import butter, sosfiltfilt

D = "/Users/shawnxiang/mochi-train/data"
MAC = "/Users/shawnxiang/mochi-train/mac/namecall-20261029"
OWW = "/Users/shawnxiang/mochi-train/oww"
GATE = os.path.join(MAC, "results", "clip_gate_20261030.json")
TRAIN = ("live_141734", "live_nc_143806", "live_nc_145512", "life_20261030_162450_812", "life_20261030_165257_248",
         "calls_221619")
HOLDOUT_FROM_S = 190.0
FS = 16000
T_LEN = 0.6
NFFT, HOP, NMEL = 400, 160, 40
BURST_DB = 6.0
MIN_S, MAX_S = 0.30, 1.0
PHASES = (0, 320, 640, 960)            # 0 / 20 / 40 / 60 ms offsets of the 80 ms oww frame grid


def mel_fb():
    f = np.linspace(0, FS / 2, NFFT // 2 + 1)
    mel = lambda h: 2595 * np.log10(1 + h / 700)
    pts = 700 * (10 ** (np.linspace(mel(60), mel(7600), NMEL + 2) / 2595) - 1)
    fb = np.zeros((NMEL, len(f)))
    for i in range(NMEL):
        lo, c, hi = pts[i:i + 3]
        fb[i] = np.clip(np.minimum((f - lo) / (c - lo), (hi - f) / (hi - c)), 0, None)
    return fb


FB = mel_fb()


def feats(y):
    n = 1 + (len(y) - NFFT) // HOP
    if n <= 0:
        return np.zeros((0, NMEL))
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    spec = np.abs(np.fft.rfft(y[idx] * np.hanning(NFFT), axis=1)) ** 2
    lm = np.log(spec @ FB.T + 1e-10)
    return (lm - lm.mean(axis=0)) / (lm.std(axis=0) + 1e-6)


def templates(calls):
    n = int(T_LEN * FS / HOP)
    out = []
    for nm, ts in calls.items():
        f = feats(np.load(os.path.join(D, "mono16v2", nm + ".npy")).astype(np.float32))
        for t in ts:
            i = int(round(t * FS / HOP))
            if 0 <= i and i + n <= len(f):
                w = f[i:i + n] - f[i:i + n].mean()
                out.append(w / (np.linalg.norm(w) + 1e-9))
    return np.stack(out)


def scan(y, tpl):
    f = feats(y)
    n = tpl.shape[1]
    if len(f) <= n + 10:
        return np.zeros(0), np.zeros(0)
    s = np.empty(len(f) - n)
    flat = tpl.reshape(len(tpl), -1)
    for a in range(0, len(s), 2000):                       # chunks keep memory bounded on hour-long files
        b = min(len(s), a + 2000)
        idx = np.arange(n)[None, :] + np.arange(a, b)[:, None]
        win = f[idx]
        win = win - win.mean(axis=(1, 2), keepdims=True)
        win = win.reshape(b - a, -1)
        win = win / (np.linalg.norm(win, axis=1)[:, None] + 1e-9)
        s[a:b] = (win @ flat.T).max(axis=1)
    z = (s - np.median(s)) / (1.4826 * np.median(np.abs(s - np.median(s))) + 1e-9)
    return np.arange(len(s)) * HOP / FS, z


def peaks(ts, z, thr, gap=1.5):
    out = []
    for i in np.argsort(-z):
        if z[i] < thr:
            break
        if all(abs(ts[i] - p) >= gap for p, _ in out):
            out.append((float(ts[i]), float(z[i])))
    return sorted(out)


SOS = butter(4, [300, 4000], "bandpass", fs=FS, output="sos")


def burst(y, t):
    """The voiced burst nearest t (s) inside t-0.6..t+1.4: (start, end) or None."""
    a, b = max(0, int((t - 0.6) * FS)), min(len(y), int((t + 1.4) * FS))
    if b - a < FS // 2:
        return None
    w = sosfiltfilt(SOS, y[a:b])
    e = 10 * np.log10(np.convolve(w ** 2, np.ones(800) / 800, "same")[::160] + 1e-12)   # 10 ms, 50 ms smoothing
    on = e > np.percentile(e, 10) + BURST_DB
    runs, i = [], 0
    while i < len(on):
        if on[i]:
            j = i
            while j < len(on) and on[j]:
                j += 1
            runs.append([i, j])
            i = j
        else:
            i += 1
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] < 20:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    if not merged:
        return None
    tc = (t - 0.6 - a / FS) * 100 + 60                     # candidate time in envelope frames
    r = min(merged, key=lambda r: 0 if r[0] <= tc <= r[1] else min(abs(r[0] - tc), abs(r[1] - tc)))
    return (a / FS + r[0] / 100, a / FS + r[1] / 100)


class Oww:
    def __init__(self, model):
        from openwakeword.model import Model
        self.m = Model(wakeword_models=[model], inference_framework="onnx")
        self.key = os.path.splitext(os.path.basename(model))[0]

    def best(self, y, t0, t1):
        """Largest P(mochi) over the frame offsets for frame ends in t0..t1 (s) of y."""
        a, b = max(0, int((t0 - 2.0) * FS)), min(len(y), int((t1 + 0.2) * FS))
        seg = y[a:b]
        out = 0.0
        for ph in PHASES:
            self.m.reset()
            x = np.clip(np.concatenate([np.zeros(FS * 2 + ph, np.float32), seg]) * 32767, -32768, 32767).astype(np.int16)
            for i in range(len(x) // 1280):
                p = self.m.predict(x[i * 1280:(i + 1) * 1280])[self.key]
                tend = a / FS + ((i + 1) * 1280 - 2 * FS - ph) / FS
                if t0 <= tend <= t1:
                    out = max(out, float(p))
        return out


def candidates(y, tpl, oww, zmin):
    ts, z = scan(y, tpl)
    out = []
    for t, zz in peaks(ts, z, zmin):
        bu = burst(y, t)
        rec = dict(t=round(t, 2), z=round(zz, 2), burst=None if bu is None else [round(bu[0], 2), round(bu[1], 2)])
        rec["burst_ok"] = bu is not None and MIN_S <= bu[1] - bu[0] <= MAX_S
        rec["v4"] = round(oww.best(y, t, t + 1.6), 3) if oww is not None else None
        out.append(rec)
    return out


def train_calls():
    gate = json.load(open(GATE))
    out = {}
    for nm in gate:
        if nm in TRAIN or nm.startswith("life_20261030_21"):
            ts = [w["start"] for w in gate[nm].get("passed", [])]
            if nm == "live_141734":
                ts = [t for t in ts if t < HOLDOUT_FROM_S]
            if ts and os.path.exists(os.path.join(D, "mono16v2", nm + ".npy")):
                out[nm] = ts
    return out


def read_life(path):
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, w.getnchannels())
    return x[:, :2].astype(np.float32).mean(axis=1) / 32768, x.astype(np.float32) / 32768


def rule(c, zc, vmin):
    return c["z"] >= zc and c["burst_ok"] and (c["v4"] or 0) >= vmin


RULES = [(zc, v) for zc in (3.0, 4.0, 5.0, 6.0) for v in (0.0, 0.05, 0.2)]


def validate(tpl, oww):
    pos = json.load(open(os.path.join(OWW, "data", "duck_heldout_v3.json")))
    neg = json.load(open(os.path.join(OWW, "data", "life_heldout.json")))
    mono = lambda nm: np.load(os.path.join(D, "mono16v2", nm + ".npy")).astype(np.float32)
    pc = {nm: candidates(mono(nm), tpl, oww, 3.0) for nm in pos}
    nc_ = {nm: candidates(mono(nm), tpl, oww, 3.0) for nm in neg}
    neg_s = sum(t1 - t0 for sp in neg.values() for t0, t1 in sp)
    res = {}
    for zc, v in RULES:
        found = sum(any(rule(c, zc, v) and -0.5 <= c["t"] - t <= 0.8 for c in pc[nm]) for nm, ts in pos.items() for t in ts)
        n_pos = sum(len(ts) for ts in pos.values())
        other = sum(1 for nm, ts in pos.items() for c in pc[nm]
                    if rule(c, zc, v) and not any(-0.5 <= c["t"] - t <= 0.8 for t in ts))
        false = sum(1 for nm, sp in neg.items() for c in nc_[nm] if rule(c, zc, v) and any(t0 <= c["t"] <= t1 for t0, t1 in sp))
        res[f"z{zc}_v{v}"] = dict(found=found, of=n_pos, other_in_call_recordings=other, false_in_talk=false,
                                  talk_min=round(neg_s / 60, 1))
        print(f"z>={zc} v4>={v}: {found}/{n_pos} held-out calls, {other} other peaks in those recordings, "
              f"{false} labels in {neg_s / 60:.1f} min of no-call talk")
    return dict(rules=res, pos=pc, neg=nc_)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--life", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=os.path.join(OWW, "models", "mochi_v4.onnx"))
    a = ap.parse_args()
    tpl = templates(train_calls())
    print(f"{len(tpl)} templates")
    oww = Oww(a.model)
    if a.validate:
        json.dump(validate(tpl, oww), open(a.out, "w"), indent=1)
        return
    res = {}
    for p in sorted(glob.glob(os.path.join(a.life, "*", "*.wav"))):
        try:
            y, _ = read_life(p)
        except (EOFError, wave.Error) as e:             # a segment cut off when the life log stopped
            print(f"skip {p}: {e!r}")
            continue
        if len(y) < FS:
            continue
        nm = "life_" + os.path.basename(os.path.dirname(p)) + "_" + os.path.basename(p)[:-4]
        res[nm] = dict(file=p, dur_s=round(len(y) / FS, 2), cands=candidates(y, tpl, oww, 3.0))
    json.dump(res, open(a.out, "w"), indent=1)
    print(f"{len(res)} files, {sum(len(r['cands']) for r in res.values())} candidates at z >= 3")


if __name__ == "__main__":
    main()
