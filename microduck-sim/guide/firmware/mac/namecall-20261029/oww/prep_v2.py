#!/usr/bin/env python3
"""openWakeWord "mochi" round 2 on the Mac mini: put the duck's own ears into the training data.

Round 1 (models/mochi.onnx, 2026-10-30 16:57) trained on piper TTS and web clips only and found 1 of 22 duck calls:
nothing in its positives had passed through the duck's head cavity. This adds, with the same absolute paths as
build_data.py:

  data/duck_pos/      the duck-ear calls as 1 s clips, K jittered copies each (gain -6..+6 dB, start +-80 ms):
                      live_141734 training calls (E3's word spans with start < 190 s; the 14 later ones stay held out
                      for score_v2.py), the 14:38 / 14:55 home calls (life_labels.json calls_found) and the three
                      confirmed life calls of the 16:22-16:54 run (life_labels_1030_live.json), each also from the left
                      and right ear alone where mono16v2 has the @ch0 / @ch1 copies. Copied into
                      work/mochi/positive_train next to the TTS and web clips (label 1).
  data/real_neg/life_*.wav   Shawn's ordinary talk and room sounds the life log heard (negative_spans of life_labels.json,
                      _1030_evening and _1030_live) as 2 s clips every 1 s; make_extra_features.py embeds them with the
                      other real negatives (label 0). The _1030_late set is kept out and listed in data/life_heldout.json
                      so score_v2.py can give false wakes per hour on talk the model never saw.
  data/duck_heldout.json     the held-out live_141734 call starts.

  ~/.venvs/oww/bin/python prep_v2.py
"""
import glob
import json
import os
import wave

import numpy as np

D = "/Users/shawnxiang/mochi-train/data"
MAC = "/Users/shawnxiang/mochi-train/mac/namecall-20261029"
OWW = "/Users/shawnxiang/mochi-train/oww"
OUT = os.path.join(OWW, "data")
POS_TRAIN = os.path.join(OWW, "work", "mochi", "positive_train")
FS = 16000
K = 30                     # copies per call from the two-ear mix
K_EAR = 10                 # copies per call from each single ear
PRE_S, POST_S = 0.30, 0.10
WORD_S = 0.65              # mochi_labels.json word_len_s
HOLDOUT_FROM_S = 190.0     # live_141734 spans from here on are E3's test calls
rng = np.random.default_rng(1)


def wwrite(path, y):
    y = np.clip(np.asarray(y, np.float32) * 32767, -32768, 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes(y.tobytes())


def mono(nm):
    p = os.path.join(D, "mono16v2", nm + ".npy")
    return np.load(p).astype(np.float32) if os.path.exists(p) else None


def cut_calls(y, spans, tag, k):
    """spans: (start, end) of the word in s -> k jittered 1 s clips each, word ending near the clip end."""
    n = 0
    for j, (s, e) in enumerate(spans):
        for c in range(k):
            s0 = s - PRE_S + rng.uniform(-0.08, 0.08)
            e0 = e + POST_S
            i0, i1 = max(0, int(s0 * FS)), min(len(y), int(e0 * FS))
            seg = y[i0:i1] * 10 ** (rng.uniform(-6, 6) / 20)
            peak = np.abs(seg).max()
            if peak > 0.98:
                seg = seg * 0.98 / peak
            wwrite(os.path.join(OUT, "duck_pos", f"duck_{tag}_{j:03d}_{c:02d}.wav"), seg)
            n += 1
    return n


def main():
    for d in ("duck_pos", "real_neg"):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
    for p in glob.glob(os.path.join(OUT, "duck_pos", "*.wav")):
        os.remove(p)
    counts = {}

    # 1. positives: live_141734 training calls (E3's spans), the home calls, the confirmed life calls
    e3 = json.load(open(os.path.join(MAC, "results", "mochi_own.json")))["data"]["spans"]["live_141734"]
    train_spans = [(s, e) for s, e in e3 if s < HOLDOUT_FROM_S]
    held = [s for s, e in e3 if s >= HOLDOUT_FROM_S]
    json.dump({"live_141734": held}, open(os.path.join(OUT, "duck_heldout.json"), "w"), indent=1)
    calls = {"live_141734": train_spans}
    for lab in ("life_labels.json", "life_labels_1030_live.json"):
        for nm, ts in json.load(open(os.path.join(MAC, lab)))["calls_found"].items():
            if ts:
                calls.setdefault(nm, []).extend((t, t + WORD_S) for t in ts)
    n_calls, n_clips, missing = 0, 0, []
    for nm, spans in calls.items():
        y = mono(nm)
        if y is None:
            missing.append(nm)
            continue
        n_calls += len(spans)
        n_clips += cut_calls(y, spans, nm, K)
        for ch in ("@ch0", "@ch1"):
            ye = mono(nm + ch)
            if ye is not None:
                n_clips += cut_calls(ye, spans, nm + ch.replace("@", "_"), K_EAR)
    counts.update(duck_calls=n_calls, duck_pos_clips=n_clips, duck_heldout_calls=len(held), duck_missing_files=missing)
    for p in glob.glob(os.path.join(POS_TRAIN, "duck_*.wav")):
        os.remove(p)
    for p in glob.glob(os.path.join(OUT, "duck_pos", "*.wav")):
        os.link(p, os.path.join(POS_TRAIN, os.path.basename(p)))
    counts["positive_train_total"] = len(os.listdir(POS_TRAIN))

    # 2. negatives: the life log's talk and room sounds, 2 s every 1 s; the late set stays held out
    for p in glob.glob(os.path.join(OUT, "real_neg", "life_*.wav")):
        os.remove(p)
    n_neg, neg_s, missing = 0, 0.0, []
    for lab in ("life_labels.json", "life_labels_1030_evening.json", "life_labels_1030_live.json"):
        for nm, spans in json.load(open(os.path.join(MAC, lab)))["negative_spans"].items():
            y = mono(nm)
            if y is None:
                missing.append(nm)
                continue
            for t0, t1 in spans:
                i0, i1 = int(t0 * FS), min(len(y), int(t1 * FS))
                for a in range(i0, i1 - 2 * FS + 1, FS):
                    wwrite(os.path.join(OUT, "real_neg", f"life_{nm}_{a // FS:04d}.wav"), y[a:a + 2 * FS])
                    n_neg += 1
                neg_s += (i1 - i0) / FS
    held = {}
    for nm, spans in json.load(open(os.path.join(MAC, "life_labels_1030_late.json")))["negative_spans"].items():
        if mono(nm) is not None:
            held[nm] = spans
    json.dump(held, open(os.path.join(OUT, "life_heldout.json"), "w"), indent=1)
    counts.update(life_neg_clips=n_neg, life_neg_seconds=round(neg_s), life_neg_missing=missing,
                  life_heldout_files=len(held),
                  life_heldout_seconds=round(sum(t1 - t0 for sp in held.values() for t0, t1 in sp)),
                  real_neg_total=len(os.listdir(os.path.join(OUT, "real_neg"))))
    json.dump(counts, open(os.path.join(OUT, "counts_v2.json"), "w"), indent=1)
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
