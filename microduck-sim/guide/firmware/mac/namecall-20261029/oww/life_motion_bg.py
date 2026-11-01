#!/usr/bin/env python3
"""Round-4 motion background from recordings that already exist: the always-on life log (16 kHz, 3 mics) while the
duck turned its body or swept its head during name-call runs. Motion intervals come from the namecall logs (turn ->
turn_done, scan -> its steps x SCAN_DWELL_S); speech is masked out (+-2 s around every logged call, and every 50 ms
voiced 60 ms frame: 6 dB over the interval's median and periodic, padded 0.5 s) so no "Mochi" lands in the negatives.

Sessions (recordings/motion_sources): 10/30 20:21 and 21:00 (before the glue) and 10/31 20:19 (after the glue).
Held out: the two 10/31 body turns at 20:21:33 and 20:21:49, during which Shawn called and v3 scored under 0.1;
they feed eval_motion.py, never training.

  python3 oww/life_motion_bg.py --out oww/bg_motion      (MacBook; scp the train clips to the Mac mini)
Writes 2 s 16 kHz int16 mono clips (left ear, right ear, two-ear mix; hop 0.5 s) and hold/<interval>.npy (16 kHz,
3 mics, float32, speech kept) plus intervals.json.
"""
import argparse
import datetime
import glob
import json
import os
import wave

import numpy as np
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(HERE, "recordings")
FS = 16000
SCAN_DWELL_S = 0.7
SESSIONS = (("motion_sources/namecall_20261030-2021.jsonl", "life/20261030", "2026-10-30"),
            ("motion_sources/namecall_20261030-2100.jsonl", "life/20261030", "2026-10-30"),
            ("motion_sources/namecall_20261031-201951.jsonl", "life/20261031", "2026-10-31"))
HOLD_STARTS = ("2026-10-31 20:21:33", "2026-10-31 20:21:49")
EVENTS_2100 = os.path.join(HERE, "results", "events_2100_20261030.json")


def life_segments(sub, day):
    out = []
    for p in sorted(glob.glob(os.path.join(REC, sub, "*.wav"))):
        b = os.path.basename(p)
        t0 = datetime.datetime.strptime(day + " " + b[:6], "%Y-%m-%d %H%M%S").timestamp() + int(b[7:10]) / 1000
        with wave.open(p) as w:
            out.append((t0, t0 + w.getnframes() / FS, p))
    return out


def audio(segs, a, b):
    """16 kHz (n, 3) float32 for wall-clock [a, b) or None when the life log does not cover all of it."""
    parts, t = [], a
    for t0, t1, p in segs:
        if t1 <= t or t0 >= b:
            continue
        if t0 > t + 0.05:
            return None
        with wave.open(p) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, w.getnchannels())
        i0, i1 = int((t - t0) * FS), int((min(b, t1) - t0) * FS)
        parts.append(x[i0:i1, :3].astype(np.float32) / 32768)
        t = min(b, t1)
    return np.concatenate(parts) if parts and t >= b - 0.05 else None


def motion_intervals(log):
    rows = [json.loads(line) for line in open(log)]
    out, calls = [], [r["t"] if r.get("t") else r["ts"] for r in rows if r["kind"] == "call"]
    for i, r in enumerate(rows):
        if r["kind"] == "turn":
            done = next((q["ts"] for q in rows[i + 1:] if q["kind"] == "turn_done"), r["ts"] + r["dur_s"])
            out.append(("turn", r["ts"], min(done, r["ts"] + r["dur_s"])))
        elif r["kind"] == "scan":
            nxt = next((q["ts"] for q in rows[i + 1:] if q["kind"] in ("turn", "call", "scan", "attend_done")), 1e12)
            out.append(("scan", r["ts"], min(nxt, r["ts"] + (r["steps"] + 1) * SCAN_DWELL_S)))
    return out, calls


def harmonic(y, lo_hz=80, hi_hz=400):
    """largest normalised autocorrelation peak in the pitch range (namecall's harmonicity test, 60 ms window):
    0.6-0.9 for voice, under 0.4 for footsteps, servo whine bursts and touches."""
    y = y - y.mean()
    e = float(y @ y)
    if e <= 1e-18:
        return 0.0
    nfft = 1 << (2 * len(y) - 1).bit_length()
    W = np.fft.rfft(y, nfft)
    r = np.fft.irfft(W.real ** 2 + W.imag ** 2, nfft) / e
    return float(r[int(FS / hi_hz):int(FS / lo_hz)].max())


def speech_mask(x, sos):
    """voiced frames: 300-1500 Hz energy 6 dB over the interval's median AND periodic (harmonic >= 0.5), padded 0.5 s."""
    m = sosfilt(sos, x[:, :2].mean(axis=1))
    B, N = 800, 960
    n = (len(m) - N) // B + 1
    e = np.array([10 * np.log10(np.mean(m[i * B:i * B + N] ** 2) + 1e-12) for i in range(max(n, 0))])
    voiced = np.zeros(len(x), bool)
    if n <= 0:
        return voiced
    med = np.median(e)
    for i in range(n):
        if e[i] > med + 6 and harmonic(m[i * B:i * B + N]) >= 0.5:
            voiced[i * B:i * B + N] = True
    pad = int(0.5 * FS)
    return np.convolve(voiced.astype(float), np.ones(2 * pad + 1))[pad:pad + len(x)] > 0


def wwrite(path, y):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes(np.clip(y * 32767, -32768, 32767).astype("<i2").tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "train"), exist_ok=True)
    os.makedirs(os.path.join(a.out, "hold"), exist_ok=True)
    sos = butter(4, (300, 1500), "bandpass", fs=FS, output="sos")
    hold_t = [datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S").timestamp() for s in HOLD_STARTS]
    ev2100 = []
    for e in json.load(open(EVENTS_2100))["events"]:
        h, m, s = e["clock"].split(":")
        ev2100.append(datetime.datetime(2026, 10, 30, int(h), int(m)).timestamp() + float(s))
    report, n_clips = [], 0
    for log, sub, day in SESSIONS:
        segs = life_segments(sub, day)
        ivs, calls = motion_intervals(os.path.join(REC, log))
        calls = calls + ev2100
        for kind, t0, t1 in ivs:
            x = audio(segs, t0, t1)
            rec = dict(kind=kind, start=datetime.datetime.fromtimestamp(t0).strftime("%m-%d %H:%M:%S.%f")[:-4], dur_s=round(t1 - t0, 2))
            if x is None:
                report.append(dict(rec, use="no life audio"))
                continue
            name = f"{day[5:].replace('-', '')}_{datetime.datetime.fromtimestamp(t0).strftime('%H%M%S')}_{kind}"
            if any(abs(t0 - h) < 1.0 for h in hold_t):
                np.save(os.path.join(a.out, "hold", name + ".npy"), x)
                report.append(dict(rec, use="hold"))
                continue
            mask = speech_mask(x, sos)
            tt = t0 + np.arange(len(x)) / FS
            for c in calls:
                mask |= np.abs(tt - c) < 2.0
            kept = 0
            for c0 in range(0, len(x) - 2 * FS + 1, FS // 2):
                if mask[c0:c0 + 2 * FS].any():
                    continue
                for tag, y in (("L", x[c0:c0 + 2 * FS, 0]), ("R", x[c0:c0 + 2 * FS, 1]), ("mix", x[c0:c0 + 2 * FS, :2].mean(axis=1))):
                    wwrite(os.path.join(a.out, "train", f"{name}_{c0 // 8000:03d}_{tag}.wav"), y)
                kept += 1
            n_clips += kept
            report.append(dict(rec, use="train", speech_masked_s=round(mask.mean() * (t1 - t0), 1), windows=kept))
    json.dump(report, open(os.path.join(a.out, "intervals.json"), "w"), indent=1)
    for r in report:
        print(r)
    print(f"{n_clips} training windows x 3 streams")


if __name__ == "__main__":
    main()
