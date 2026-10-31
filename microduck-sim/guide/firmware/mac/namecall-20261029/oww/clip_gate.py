#!/usr/bin/env python3
"""The clip gate for the Mochi spotter's positives (Shawn 2026-10-30 20:26: 你看看怎么确保切出来的短片段的正确性吧).

Round 2 trained on E3's energy spans of live_141734: 31 of 56 were 0.2-0.4 s fragments, not the word. From round 3
on, a positive clip must pass this gate, two checks on a 2.5 s window around each candidate call:

  word      Whisper small reads the name somewhere in the window (auto language, then English with the prompt
            "Mochi, Mochi."; mochi / モチ / 마치 / мочи and the usual mishearings). Required for open-ended recordings
            (life log, name-call sessions). Protocol recordings, where Shawn said every utterance is the name
            (calls_200910, calls_201411, calls_221619, live_073135, live_141734 110-226 s), record the reading but do
            not need it: Whisper cannot read a 2 m call under room noise (its word timestamps are useless there too:
            one "word" over the whole window), the protocol is the label.
  boundary  the voiced burst nearest the candidate time, from the 300-4000 Hz energy envelope of the ear mix (50 ms
            smoothing, threshold half-way in dB between the window's floor and its peak, gaps under 200 ms bridged),
            must be 0.30-1.0 s long: shorter is a fragment, longer is two calls or talk. The clip is that burst.
            When the envelope finds no such burst (a 2 m RoboClub call a few dB over the room), a protocol candidate
            becomes the labelled word start plus WORD_S ("protocol_fixed"), a Whisper-read candidate the WORD_S before
            its peak time ("asr_fixed"); an unread, unfound candidate fails.

Writes results/clip_gate_<date>.json:
  {"<recording>": {"file": ..., "protocol": bool, "passed": [{"t": cand, "start": s, "end": e, "by": "asr"|"protocol"|
                   "protocol_fixed"|"asr_fixed", "text": reading, "burst": [s, e] or null}],
                   "failed": [{"t": cand, "why": ..., "texts": [...]}]}}
Recording names match the mono16v2 names on the Mac mini (prep_v3.py consumes this file). Runs on the MacBook
(Whisper in ~/.venvs/duck-see); reads the duck recordings directly (A7Z .raw 48 kHz 4 ch, 48 kHz S32 .wav, 16 kHz
int16 life .wav).

  ~/.venvs/duck-see/bin/python clip_gate.py --out ../results/clip_gate_20261030.json
"""
import argparse
import glob
import json
import os
import re
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
NC = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, NC)
import namecall as nc  # noqa: E402

REC = os.path.join(os.path.dirname(HERE), "recordings")
SCRATCH = "/private/tmp/claude-501/-Users-xiangzheng-code-robotics/9d0176eb-ac98-4d4e-af9f-5113eeae3ed8/scratchpad"
FS = 16000
WIN_PRE, WIN_POST = 1.2, 1.3          # window around a candidate time (the E3 span start or the known word start)
MIN_S, MAX_S = 0.30, 1.0
BURST_DB = 6.0                        # a frame is part of the word this far over the window's floor in either band
WORD_S = 0.65                         # the labelled word length (mochi_labels.json) when the envelope cannot find it
PROTOCOL = {"calls_200910", "calls_201411", "calls_221619", "live_073135", "live_141734"}
NAME = re.compile(r"(mo+t?ch?i+e*|mo+ji|mo+shi|mo+ti|mo+cci|ma+c?chi|mochee|muchi|モチ|もち|マチ|マジ|まち|まじ|마치|모치|мочи|мати|моти|machi|mowchi)", re.I)
NFFT, HOP = 512, 160


def load(path):
    """(samples, channels) float32 and rate; A7Z .raw and S32 .wav are 48 kHz 4 ch, life .wav 16 kHz int16 3 ch."""
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


def ear_mix16(path):
    x, fs = load(path)
    mix = x[:, :2].mean(axis=1)
    if fs == 48000:
        mix = nc.Decimate3()(mix)
    elif fs != FS:
        raise SystemExit(f"{path}: {fs} Hz")
    return mix.astype(np.float32)


def burst(win, t_cand):
    """(start, end) in s within the window of the voiced burst nearest t_cand, or None."""
    n = (len(win) - NFFT) // HOP + 1
    if n < 10:
        return None
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    P = np.abs(np.fft.rfft(win[idx] * np.hanning(NFFT)[None, :], axis=1)) ** 2
    f = np.fft.rfftfreq(NFFT, 1 / FS)
    # two bands over their own floors: the voiced "Mo" lives under 1.2 kHz, the "chi" above; a word is loud in either
    es = []
    for lo, hi in ((250, 1200), (1200, 4000)):
        e = 10 * np.log10(P[:, (f >= lo) & (f < hi)].mean(axis=1) + 1e-12)
        e = np.convolve(e, np.ones(5) / 5, mode="same")
        es.append(e - np.percentile(e, 10))
    e = np.maximum(*es)
    if e.max() < BURST_DB + 3:
        return None
    loud = e > BURST_DB
    i = 0
    while i < n:                                   # bridge gaps under 200 ms
        if not loud[i]:
            j = i
            while j < n and not loud[j]:
                j += 1
            if 0 < i and j < n and j - i < 20:
                loud[i:j] = True
            i = j
        else:
            i += 1
    k = int(t_cand * FS / HOP)
    cand = np.nonzero(loud)[0]
    if not len(cand):
        return None
    j = cand[np.argmin(np.abs(cand - k))]
    if abs(j - k) * HOP / FS > 0.6:
        return None
    a = j
    while a > 0 and loud[a - 1]:
        a -= 1
    b = j
    while b < n - 1 and loud[b + 1]:
        b += 1
    return a * HOP / FS, (b + 1) * HOP / FS + NFFT / FS / 2


def candidates():
    """recording name -> (path, [candidate word-start times])."""
    L = os.path.dirname(HERE)
    out = {}
    e3 = json.load(open(os.path.join(L, "results", "mochi_own.json")))["data"]["spans"]["live_141734"]
    out["live_141734"] = (os.path.join(REC, "raw", "live_141734.raw"), [s for s, e in e3])
    m = json.load(open(os.path.join(L, "mochi_labels.json")))
    out["calls_201411"] = (os.path.join(REC, "calls_201411.wav"), m["calls_found"]["calls_201411"])
    out["calls_221619"] = (os.path.join(REC, "calls_221619.wav"), m["word_starts"]["calls_221619"])
    out["live_073135"] = (os.path.join(REC, "raw", "live_073135.raw"), m["calls_heldout"]["live_073135"])
    for nm, ts in json.load(open(os.path.join(L, "life_labels.json")))["calls_found"].items():
        out[nm] = (os.path.join(REC, "raw", nm + ".raw"), ts)
    for nm, ts in json.load(open(os.path.join(L, "life_labels_1030_live.json")))["calls_found"].items():
        if ts:
            out[nm] = (os.path.join(REC, "life", "20261030", nm.split("_", 2)[2] + ".wav"), ts)
    eight = json.load(open(os.path.join(L, "eightdir_20261030.json")))
    p = os.path.join(REC, "calls_200910.wav")
    if not os.path.exists(p):
        p = os.path.join(SCRATCH, "calls_200910.wav")
    out["calls_200910"] = (p, [c["t_s"] for c in eight["calls"]])
    # tonight's live run: the transcript-checked events (results/events_2100_20261030.json), by life segment
    ev = json.load(open(os.path.join(L, "results", "events_2100_20261030.json")))["events"]
    segs = sorted(glob.glob(os.path.join(REC, "life", "20261030", "21*.wav")) or glob.glob(os.path.join(SCRATCH, "life2100", "21*.wav")))

    def t0_of(pth):
        b = os.path.basename(pth)[:10]
        return int(b[:2]) * 3600 + int(b[2:4]) * 60 + int(b[4:6]) + int(b[7:10]) / 1000
    for e in ev:
        if e["kind"] != "call":
            continue
        h, mnt, s = e["clock"].split(":")
        t = int(h) * 3600 + int(mnt) * 60 + float(s)
        for pth in segs:
            t0 = t0_of(pth)
            if t0 <= t < t0 + 61:
                nm = "life_20261030_" + os.path.basename(pth)[:-4]
                out.setdefault(nm, (pth, []))[1].append(round(t - t0, 2))
                break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="small")
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args()
    import whisper
    model = whisper.load_model(a.model)
    res = {}
    for nm, (path, ts) in candidates().items():
        if a.only and nm not in a.only:
            continue
        if not os.path.exists(path):
            res[nm] = dict(file=path, missing=True)
            print(nm, "MISSING", path, flush=True)
            continue
        y = ear_mix16(path)
        protocol = nm in PROTOCOL
        rec = dict(file=path, protocol=protocol, passed=[], failed=[])
        for t in ts:
            i0, i1 = max(0, int((t - WIN_PRE) * FS)), min(len(y), int((t + WIN_POST) * FS))
            win = y[i0:i1]
            peak = float(np.abs(win).max())
            win = win / peak * 0.5 if peak > 0 else win
            texts, read = [], None
            for lang in (None, "en"):
                r = model.transcribe(win, fp16=False, language=lang, temperature=0.0, condition_on_previous_text=False,
                                     initial_prompt="Mochi, Mochi." if lang == "en" else None)
                txt = " ".join(s["text"].strip() for s in r["segments"])
                texts.append((lang or r.get("language"), txt))
                if NAME.search(txt.lower().replace(" ", "")):
                    read = txt
                    break
            b = burst(win, t - i0 / FS)
            s, e = (i0 / FS + b[0], i0 / FS + b[1]) if b is not None else (None, None)
            found = b is not None and MIN_S <= e - s <= MAX_S
            why = "no burst at the candidate" if b is None else f"burst {e - s:.2f} s"
            if found:
                by = "asr" if read else "protocol"
            elif protocol:
                # a 2 m RoboClub call sits a few dB over the room: the envelope cannot find it, the label's word start
                # and the labelled word length are the clip (calls_201411 by template match and Shawn's ear, calls_221619
                # by hand, calls_200910 by the protocol)
                s, e, by = t, t + WORD_S, "protocol_fixed"
            elif read:
                # the quiet calls Whisper still reads (the ones round 2 missed): the candidate time is the spotter's or
                # E3's peak, about the word's end
                s, e, by = t - WORD_S + 0.1, t + 0.1, "asr_fixed"
            else:
                rec["failed"].append(dict(t=t, why=why if b is None or not found else "Whisper read no name", texts=texts))
                continue
            if read is None and not protocol:
                rec["failed"].append(dict(t=t, why="Whisper read no name", texts=texts, burst=[round(s, 2), round(e, 2)]))
                continue
            rec["passed"].append(dict(t=t, start=round(max(0.0, s), 2), end=round(e, 2), by=by, text=read,
                                      burst=None if b is None else [round(i0 / FS + b[0], 2), round(i0 / FS + b[1], 2)]))
        res[nm] = rec
        n_asr = sum(w["by"] == "asr" for w in rec["passed"])
        print(f"{nm}: {len(rec['passed'])} passed ({n_asr} read by Whisper), {len(rec['failed'])} failed of {len(ts)}", flush=True)
        for f in rec["failed"]:
            print("   failed", f["t"], f["why"], [t for _, t in f["texts"]][:2], flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(res, open(a.out, "w"), ensure_ascii=False, indent=1)
    tot_p = sum(len(r.get("passed", [])) for r in res.values())
    tot_f = sum(len(r.get("failed", [])) for r in res.values())
    print(f"total passed {tot_p}, failed {tot_f}; written {a.out}")


if __name__ == "__main__":
    main()
