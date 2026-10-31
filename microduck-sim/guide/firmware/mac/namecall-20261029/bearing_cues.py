#!/usr/bin/env python3
"""Which microphone cues on this head carry the caller's direction? For every call whose true bearing is known
(tonight's camera-confirmed calls from the life log, the 10/29 eight-direction RoboClub recording) compute, on the
masked call bins (SNR over the pre-call noise on all three microphones, as CallLocaliser does):

  ILD  level difference in dB per band for left-right, ears-back
  lag  GCC-PHAT fractional lag per pair in the low and mid band (samples at 16 kHz; 77 mm ears = 3.6 samples max)

and print each cue's correlation with sin(bearing) (left-right) and with the folded bearing, plus a leave-one-out
ridge fit from all cues to (sin, cos) of the bearing: the error that a learned localiser would reach today.

  python3 bearing_cues.py --slices DIR --plan PLAN.json [--robo recordings/calls_221619.wav]
"""
import argparse
import json
import math
import os
import wave

import numpy as np

FS = 16000
NFFT, HOP = 512, 128
BANDS = [(300, 1200), (1200, 2500), (2500, 4000), (4000, 6000), (6000, 8000)]
LAG_BANDS = [(300, 1200), (1200, 2500), (2500, 5000)]
PAIRS = [("L", "R", 0, 1), ("L", "B", 0, 2), ("R", "B", 1, 2)]
SNR_DB = 3.0
ROBO_DEG = [0, 45, 90, 135, 180, -135, -90, -45]       # NAMECALL.md 10.4, calls_221619 word_starts in order


def read_wav(path):
    w = wave.open(path)
    fs, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
    dt = {2: np.int16, 4: np.int32}[sw]
    x = np.frombuffer(w.readframes(w.getnframes()), dt).reshape(-1, ch).astype(np.float32) / 2 ** (8 * sw - 1)
    if fs != FS:
        from scipy.signal import resample_poly
        x = resample_poly(x, FS, fs, axis=0).astype(np.float32)
    return x[:, :3]


def stft(x):
    win = np.hanning(NFFT).astype(np.float32)
    n = (len(x) - NFFT) // HOP + 1
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    return np.fft.rfft(x[idx] * win[None, :, None], axis=1)        # (frames, bins, ch)


def cues(x, t_on, pre=(0.0, 0.45), call=(-0.05, 0.85)):
    """x (n, 3) at 16 kHz, t_on the call onset in s -> dict of cue values, or None when too few bins."""
    x = x - x.mean(axis=0)
    F = stft(x)
    t = (np.arange(len(F)) * HOP + NFFT) / FS
    f = np.fft.rfftfreq(NFFT, 1 / FS)
    noise = F[(t >= pre[0]) & (t <= pre[1])]
    cal = F[(t >= t_on + call[0]) & (t <= t_on + call[1])]
    if len(noise) < 3 or len(cal) < 3:
        return None
    npsd = (np.abs(noise) ** 2).mean(axis=0) + 1e-14
    snr = (np.abs(cal) ** 2) / npsd[None]
    w = np.clip(10 * np.log10(snr.min(axis=2) + 1e-12) - SNR_DB, 0, 15) / 15.0      # (frames, bins)
    if (w > 0).sum() < 8:
        return None
    out = {"bins": int((w > 0).sum())}
    P = (np.abs(cal) ** 2) * w[:, :, None]
    for lo, hi in BANDS:
        sel = (f >= lo) & (f < hi)
        e = P[:, sel, :].sum(axis=(0, 1)) + 1e-14
        out[f"ild_LR_{lo}"] = 10 * math.log10(e[0] / e[1])
        out[f"ild_EB_{lo}"] = 10 * math.log10(math.sqrt(e[0] * e[1]) / e[2])
    lags = np.arange(-6, 6.01, 0.1)
    for lo, hi in LAG_BANDS:
        sel = (f >= lo) & (f < hi)
        fb = f[sel]
        E = np.exp(2j * math.pi * np.outer(lags / FS, fb))
        for a, b, i, j in PAIRS:
            g = cal[:, sel, i] * np.conj(cal[:, sel, j])
            g = g / (np.abs(g) + 1e-30)
            acc = (g * w[:, sel]).sum(axis=0) / max(w[:, sel].sum(), 1e-9)
            r = (E @ acc).real
            out[f"lag_{a}{b}_{lo}"] = float(lags[int(np.argmax(r))])
            out[f"pk_{a}{b}_{lo}"] = float(r.max())
    out.update(onset_cues(x, t_on))
    return out


ONSET_BAND = (1500.0, 6000.0)
ONSET_WIN_S = 0.02        # the first 20 ms of a rise: the direct path through the ear holes before the cavity fills


def onset_cues(x, t_on, search=(-0.1, 0.9), rise_db=5.0):
    """Precedence-effect lags: find the sharp rises of the high band inside the call, take ONSET_WIN_S from each,
    GCC-PHAT in ONSET_BAND, and report the lag of the strongest rise and the median over rises."""
    from scipy.signal import butter, sosfiltfilt
    sos = butter(4, [ONSET_BAND[0] / (FS / 2), ONSET_BAND[1] / (FS / 2)], btype="band", output="sos")
    hb = sosfiltfilt(sos, x, axis=0).astype(np.float32)
    env = np.sqrt(np.convolve((hb ** 2).mean(axis=1), np.ones(32) / 32, mode="same"))      # 2 ms envelope
    i0, i1 = int((t_on + search[0]) * FS), min(len(x), int((t_on + search[1]) * FS))
    floor = np.median(env[: int(0.4 * FS)]) + 1e-9
    db = 20 * np.log10(env / floor + 1e-9)
    rises = []
    k = i0
    while k < i1 - int(ONSET_WIN_S * FS):
        if db[k] >= rise_db and db[k] - db[max(0, k - 160)] >= rise_db:     # 10 ms earlier it was rise_db lower
            rises.append((float(db[k:k + 160].max()), k))
            k += int(0.05 * FS)                                            # one rise per 50 ms
        else:
            k += 8
    out = {}
    if not rises:
        return out
    n = int(ONSET_WIN_S * FS)
    lags = np.arange(-6, 6.01, 0.1)
    f = np.fft.rfftfreq(2 * n, 1 / FS)
    sel = (f >= ONSET_BAND[0]) & (f < ONSET_BAND[1])
    E = np.exp(2j * math.pi * np.outer(lags / FS, f[sel]))
    per = {p[0] + p[1]: [] for p in PAIRS}
    for _, k in rises:
        seg = hb[max(0, k - 16):max(0, k - 16) + n] * np.hanning(n)[:, None]
        if len(seg) < n:
            continue
        S = np.fft.rfft(seg, 2 * n, axis=0)
        for a, b, i, j in PAIRS:
            g = S[sel, i] * np.conj(S[sel, j])
            g = g / (np.abs(g) + 1e-30)
            r = (E @ g).real
            per[a + b].append(float(lags[int(np.argmax(r))]))
    for key, v in per.items():
        if v:
            out[f"lag_on_{key}_first"] = v[0]
            out[f"lag_on_{key}_med"] = float(np.median(v))
    out["onsets"] = len(rises)
    return out


def corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.std() < 1e-9 or b.std() < 1e-9:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def loo_fit(X, deg, lam=1.0):
    """Leave-one-out ridge from standardised cues to (sin, cos) of the bearing -> per-sample predicted degrees."""
    X = np.asarray(X, float)
    mu, sd = X.mean(axis=0), X.std(axis=0) + 1e-9
    Z = (X - mu) / sd
    Z = np.hstack([Z, np.ones((len(Z), 1))])
    y = np.stack([np.sin(np.radians(deg)), np.cos(np.radians(deg))], axis=1)
    pred = []
    for k in range(len(Z)):
        m = np.ones(len(Z), bool)
        m[k] = False
        A = Z[m].T @ Z[m] + lam * np.eye(Z.shape[1])
        W = np.linalg.solve(A, Z[m].T @ y[m])
        p = Z[k] @ W
        pred.append(math.degrees(math.atan2(p[0], p[1])))
    return np.array(pred)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slices", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--robo", default=None)
    ap.add_argument("--robo-starts", default=None, help="json with word_starts for the robo file")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rows = []
    for k, p in enumerate(json.load(open(a.plan))):
        x = read_wav(os.path.join(a.slices, f"c{k:02d}.wav"))
        c = cues(x, 0.6)
        if c:
            rows.append(dict(set="home", name=p["file"], true=p["true"], heard=p["heard"], **c))
    if a.robo and a.robo_starts:
        x = read_wav(a.robo)
        starts = json.load(open(a.robo_starts))["word_starts"]["calls_221619"]
        for t0, deg in zip(starts, ROBO_DEG):
            i0 = int((t0 - 0.6) * FS)
            c = cues(x[i0:i0 + int(2.2 * FS)], 0.6)
            if c:
                rows.append(dict(set="robo", name=f"calls_221619@{t0}", true=deg, heard=None, **c))
    keys = sorted({k for r in rows for k in r if k.startswith(("ild_", "lag_"))})
    print(f"rows with onset lags: {sum('lag_on_LR_med' in r for r in rows)}/{len(rows)}")
    print(f"{len(rows)} calls with a known bearing")
    for r in rows:
        print(f"  {r['set']:4s} true {r['true']:7.1f}  heard {str(r['heard']):7s} bins {r['bins']:4d} | "
              + " ".join(f"{k.replace('ild_', '').replace('lag_', 'lag')}={r[k]:+5.1f}" for k in keys if k in r and k in ("ild_LR_300", "lag_LR_1200", "lag_on_LR_first", "lag_on_LR_med", "lag_on_LB_med", "lag_on_RB_med")) + f" onsets={r.get('onsets')}")
    for subset in ("home", "all"):
        sel = [r for r in rows if subset == "all" or r["set"] == subset]
        if len(sel) < 6:
            continue
        true = np.array([r["true"] for r in sel], float)
        s, folded = np.sin(np.radians(true)), np.where(np.abs(true) <= 90, np.abs(true), 180 - np.abs(true))
        print(f"\n[{subset}] n={len(sel)}: correlation of each cue with sin(bearing) (left-right) and with the folded bearing")
        for k in keys:
            have = [i for i, r in enumerate(sel) if k in r]
            v = [sel[i][k] for i in have]
            print(f"  {k:18s} n {len(v):2d}  r_sin {corr(v, s[have]):+5.2f}   r_folded {corr(v, folded[have]):+5.2f}")
        keys_all = [k for k in keys if all(k in r for r in sel)]
        X = [[r[k] for k in keys_all] for r in sel]
        pred = loo_fit(X, true)
        err = np.abs(((pred - true) + 180) % 360 - 180)
        side_ok = int(np.sum(np.sign(pred) == np.sign(true)))
        base = np.abs(np.abs(true) - np.median(np.abs(true)))
        print(f"  leave-one-out ridge, all cues: mean |err| {err.mean():.1f} deg, median {np.median(err):.1f}, max {err.max():.0f}; "
              f"side right {side_ok}/{len(sel)}; the side*median prior would give mean |err| {base.mean():.1f}")
        ild = [k for k in keys_all if k.startswith("ild_")]
        pred = loo_fit([[r[k] for k in ild] for r in sel], true)
        err = np.abs(((pred - true) + 180) % 360 - 180)
        print(f"  leave-one-out ridge, loudness cues only: mean |err| {err.mean():.1f} deg, median {np.median(err):.1f}, max {err.max():.0f}")
        lag = [k for k in keys_all if k.startswith("lag_")]
        pred = loo_fit([[r[k] for k in lag] for r in sel], true)
        err = np.abs(((pred - true) + 180) % 360 - 180)
        print(f"  leave-one-out ridge, lag cues only:      mean |err| {err.mean():.1f} deg, median {np.median(err):.1f}, max {err.max():.0f}")
    if a.out:
        json.dump(rows, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
