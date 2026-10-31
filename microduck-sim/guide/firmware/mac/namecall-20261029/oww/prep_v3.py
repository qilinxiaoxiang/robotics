#!/usr/bin/env python3
"""openWakeWord "mochi" round 3 on the Mac mini: gated positives, tonight's calls, RoboClub room noise.

Round 2 (models/mochi_v2.onnx) heard 9 of 17 home calls on 2026-10-30 21:00 and about 1 in 5 at RoboClub: its duck
positives were E3's energy spans (31 of 56 live_141734 spans were 0.2-0.4 s fragments) and it had never heard the
quieter calls. Round 3 changes the data only (same recipe, mochi.yml, 50000 steps):

  positives   every duck call that passed the clip gate (clip_gate.py: a Whisper word reading as the name, 0.45-1.0 s;
              results/clip_gate_20261030.json), from the training recordings: live_141734 words before 190 s, the
              14:38 / 14:55 home calls, the 16:24 / 16:52 life calls, calls_221619 (RoboClub, corridor loudspeaker,
              after the ear repair) and tonight's 21:00-21:08 live calls (the eight unanswered quiet ones included).
              K jittered copies of the two-ear mix and K_EAR of each ear alone -> data/duck_pos -> positive_train.
  held out    calls_200910 (the eight-direction home calls at 2 m), calls_201411 (RoboClub, before the ear repair),
              live_073135 (six home table calls), live_141734 gated words from 190 s: data/duck_heldout_v3.json for
              score_v2.py --heldout. Never trained on.
  negatives   the life talk of round 2 (life_labels*.json negative_spans) plus calls_200910 0-520 s: 8.7 min of Shawn
              talking and moving at home with no call (he confirmed), the very sound E3 answered.
  background  data/bg_roboclub: 2 s chunks of calls_221510 (RoboClub, no call) and of the gaps between the calls of
              calls_201411 / calls_221619 (room, corridor loudspeaker), for mochi.yml background_paths (run_v3.sh adds
              the path with duplication rate 3 so the duck's own rooms are mixed under the positives often).

  ~/.venvs/oww/bin/python prep_v3.py
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
GATE = os.path.join(MAC, "results", "clip_gate_20261030.json")
FS = 16000
K = 30                     # copies per call from the two-ear mix
K_EAR = 10                 # copies per call from each single ear
PRE_S, POST_S = 0.30, 0.10
HOLDOUT_FROM_S = 190.0     # live_141734 words from here on stay held out (as in round 2)
TRAIN = ("live_141734", "live_nc_143806", "live_nc_145512", "life_20261030_162450_812", "life_20261030_165257_248", "calls_221619")
HELD = ("calls_200910", "calls_201411", "live_073135")
rng = np.random.default_rng(3)


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


def cut_calls(y, spans, tag, k, out_dir):
    """spans: (start, end) of the word in s -> k jittered clips each (PRE_S before the word, POST_S after)."""
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
            wwrite(os.path.join(out_dir, f"duck_{tag}_{j:03d}_{c:02d}.wav"), seg)
            n += 1
    return n


def clear(pattern):
    for p in glob.glob(pattern):
        os.remove(p)


def main():
    for d in ("duck_pos", "real_neg", "bg_roboclub"):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
    clear(os.path.join(OUT, "duck_pos", "*.wav"))
    gate = json.load(open(GATE))
    counts = dict(gate_file=GATE)

    # 1. positives: gated words of the training recordings (tonight's life segments by prefix)
    train_names = [nm for nm in gate if nm in TRAIN or nm.startswith("life_20261030_21")]
    n_calls, n_clips, missing, per = 0, 0, [], {}
    for nm in train_names:
        spans = [(w["start"], w["end"]) for w in gate[nm].get("passed", [])]
        if nm == "live_141734":
            spans = [(s, e) for s, e in spans if s < HOLDOUT_FROM_S]
        if not spans:
            continue
        y = mono(nm)
        if y is None:
            missing.append(nm)
            continue
        per[nm] = len(spans)
        n_calls += len(spans)
        n_clips += cut_calls(y, spans, nm, K, os.path.join(OUT, "duck_pos"))
        for ch in ("@ch0", "@ch1"):
            ye = mono(nm + ch)
            if ye is not None:
                n_clips += cut_calls(ye, spans, nm + ch.replace("@", "_"), K_EAR, os.path.join(OUT, "duck_pos"))
    counts.update(duck_calls=n_calls, duck_calls_per_recording=per, duck_pos_clips=n_clips, duck_missing_files=missing)
    clear(os.path.join(POS_TRAIN, "duck_*.wav"))
    for p in glob.glob(os.path.join(OUT, "duck_pos", "*.wav")):
        os.link(p, os.path.join(POS_TRAIN, os.path.basename(p)))
    counts["positive_train_total"] = len(os.listdir(POS_TRAIN))

    # 2. held out: word starts of the recordings never trained on, for score_v2.py --heldout
    held = {}
    for nm in HELD:
        if nm in gate and mono(nm) is not None:
            held[nm] = [w["start"] for w in gate[nm].get("passed", [])]
    if "live_141734" in gate:
        held["live_141734"] = [w["start"] for w in gate["live_141734"].get("passed", []) if w["start"] >= HOLDOUT_FROM_S]
    json.dump(held, open(os.path.join(OUT, "duck_heldout_v3.json"), "w"), indent=1)
    counts["duck_heldout_calls"] = {k: len(v) for k, v in held.items()}
    # the gate's failures: candidates where Whisper read no name; kept out of both sides, listed for a look
    counts["gate_failed"] = {nm: len(r.get("failed", [])) for nm, r in gate.items() if r.get("failed")}

    # 3. negatives: round-2 life talk plus calls_200910 0-520 s (Shawn's talk at home, no call: his words 20:26)
    clear(os.path.join(OUT, "real_neg", "life_*.wav"))
    clear(os.path.join(OUT, "real_neg", "talk_*.wav"))
    neg_spans = {}
    for lab in ("life_labels.json", "life_labels_1030_evening.json", "life_labels_1030_live.json"):
        for nm, spans in json.load(open(os.path.join(MAC, lab)))["negative_spans"].items():
            neg_spans.setdefault(nm, []).extend(spans)
    neg_spans["calls_200910"] = [[0.0, 520.0]]
    n_neg, neg_s, missing = 0, 0.0, []
    for nm, spans in neg_spans.items():
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
    held_life = {}
    for nm, spans in json.load(open(os.path.join(MAC, "life_labels_1030_late.json")))["negative_spans"].items():
        if mono(nm) is not None:
            held_life[nm] = spans
    json.dump(held_life, open(os.path.join(OUT, "life_heldout.json"), "w"), indent=1)
    counts.update(life_neg_clips=n_neg, life_neg_seconds=round(neg_s), life_neg_missing=missing,
                  life_heldout_files=len(held_life),
                  life_heldout_seconds=round(sum(t1 - t0 for sp in held_life.values() for t0, t1 in sp)),
                  real_neg_total=len(os.listdir(os.path.join(OUT, "real_neg"))))

    # 4. background: RoboClub room sound in 2 s chunks (no call within 1.5 s)
    clear(os.path.join(OUT, "bg_roboclub", "*.wav"))
    n_bg = 0
    starts = {"calls_221510": [], "calls_201411": [w["t"] for w in gate.get("calls_201411", {}).get("passed", [])] +
              [w["t"] for w in gate.get("calls_201411", {}).get("failed", [])],
              "calls_221619": [w["t"] for w in gate.get("calls_221619", {}).get("passed", [])] +
              [w["t"] for w in gate.get("calls_221619", {}).get("failed", [])]}
    for nm, ts in starts.items():
        y = mono(nm)
        if y is None:
            continue
        for a in range(0, len(y) - 2 * FS + 1, 2 * FS):
            t0, t1 = a / FS, a / FS + 2.0
            if any(t - 1.5 < t1 and t + 2.0 > t0 for t in ts):
                continue
            wwrite(os.path.join(OUT, "bg_roboclub", f"{nm}_{a // FS:04d}.wav"), y[a:a + 2 * FS])
            n_bg += 1
    counts["bg_roboclub_clips"] = n_bg
    json.dump(counts, open(os.path.join(OUT, "counts_v3.json"), "w"), indent=1)
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
