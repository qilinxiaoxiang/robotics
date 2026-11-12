#!/usr/bin/env python3
"""Export the "mochi" wake-word data as cut clips for a teammate to train on (Ryan, task A, 2026-11-12).

Shawn's call (2026-11-12): share only cut clips, never the raw life-log recordings, so nobody can listen to continuous
talk at home. Every clip here is a call cut around its voiced span, or a talk / room clip of at most 2 s.

  positives/train/   each training call once, no augmentation: the two-ear mix and each ear alone
                     (77 gated calls of 10/29-10/30 plus the round-6 calls mined from the life log of 11-02..11-11)
  positives/heldout/ calls never trained on: duck_heldout_v3 (32), the 11-11 evening calls and the four calls Shawn
                     counted on 11-12 00:56 (also as one 13 s three-channel clip, counted_20261112_0056_3ch.wav)
  negatives/train/   round-6 real negatives (2 s, one per 4 s, opaque names): talk at home with no call, the duck's
                     own quack, RoboClub room
  negatives/heldout_talk/ the held-out no-call talk of 10/30 late, 2 s clips one per 4 s (false-wake check)
  background/        RoboClub room and robot-motion noise used as augmentation background
  synthetic_set/     macOS TTS evaluation set (manifest.json: pos, pos_zh, neg_word, speech)
  web/               clips cut from public videos (web_pos, web_neg); sources in web_heldout.json
  models/            mochi_v4.onnx (deployed) and the openWakeWord training config
  manifest.jsonl     one row per positive clip: file, source, start/end in its recording, channel, split

  ~/.venvs/oww/bin/python export_share.py --out ~/mochi-train/share/mochi_kws_20261112
"""
import argparse
import glob
import hashlib
import re
import json
import os
import shutil
import wave

import numpy as np

import prep_v3 as p3
import prep_v6 as p6

FS = 16000
PRE, POST = 0.30, 0.35
GAP_S = 4                   # one 2 s talk clip per 4 s: no two shared clips touch, so talk cannot be re-joined
SALT = os.urandom(8).hex()  # opaque clip names, new on every export
D = p3.D
OWW = p3.OWW


def wwrite(path, y, ch=1):
    y = np.clip(np.asarray(y, np.float32) * 32767, -32768, 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes(y.tobytes())


def mono(nm):
    p = os.path.join(D, "mono16v2", nm + ".npy")
    return np.load(p).astype(np.float32) if os.path.exists(p) else None


def cut(y, s, e):
    return y[max(0, int(s * FS)):min(len(y), int(e * FS))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = os.path.expanduser(a.out)
    dirs = ["positives/train", "positives/heldout", "negatives/train", "negatives/heldout_talk", "background",
            "synthetic_set", "web", "models"]
    for d in dirs:
        os.makedirs(os.path.join(out, d), exist_ok=True)
    rows = []

    def emit(split, y, s, e, src, ch, pre=PRE, post=POST):
        nm = f"{src}_{ch}_{s:07.2f}.wav"
        wwrite(os.path.join(out, "positives", split, nm), cut(y, s - pre, e + post))
        rows.append(dict(file=f"positives/{split}/{nm}", source=src, start=round(s, 2), end=round(e, 2), channel=ch,
                         split=split))

    # training calls of rounds 3/4 (gated, 10/29-10/30)
    gate = json.load(open(p3.GATE))
    for nm in gate:
        if not (nm in p3.TRAIN or nm.startswith("life_20261030_21")):
            continue
        spans = [(w["start"], w["end"]) for w in gate[nm].get("passed", [])]
        if nm == "live_141734":
            spans = [(s, e) for s, e in spans if s < p3.HOLDOUT_FROM_S]
        for ch, key in (("mix", nm), ("ear0", nm + "@ch0"), ("ear1", nm + "@ch1")):
            y = mono(key)
            if y is not None:
                for s, e in spans:
                    emit("train", y, s, e, nm, ch)

    # round-6 calls mined from the life log (same accept rule as prep_v6 at zc 3, v4min 0.05)
    counts = json.load(open(os.path.join(OWW, "data", "counts_v6.json")))
    zc, vmin = counts["rule"]["zc"], counts["rule"]["v4min"]
    mine = json.load(open(p6.MINE))
    index = p6.live_index()
    for nm, r in sorted(mine.items()):
        if nm.split("_")[1] not in p6.TRAIN_DAYS or nm >= p6.HELD_FROM:
            continue
        acc = [c for c in r["cands"] if p6.accept(c, zc, vmin, index.get(nm, ([], []))[1])]
        if not acc:
            continue
        mix, x = p6.read_life(r["file"])
        for ch, y in (("mix", mix), ("ear0", x[:, 0]), ("ear1", x[:, 1])):
            for c in acc:
                emit("train", y, c["burst"][0], c["burst"][1], nm, ch)

    # held-out calls: round-3 set (starts only, 1 s before to 2 s after)
    for nm, starts in json.load(open(os.path.join(OWW, "data", "duck_heldout_v3.json"))).items():
        for ch, key in (("mix", nm), ("ear0", nm + "@ch0"), ("ear1", nm + "@ch1")):
            y = mono(key)
            if y is not None:
                for s in starts:
                    emit("heldout", y, s, s, nm, ch, pre=1.0, post=2.0)
    # held-out calls: 11-11 evening and the four counted calls of 11-12
    for nm, h in json.load(open(os.path.join(OWW, "data", "new_heldout_v6.json"))).items():
        mix, x = p6.read_life(h["file"])
        for ch, y in (("mix", mix), ("ear0", x[:, 0]), ("ear1", x[:, 1])):
            for s in h["starts"]:
                emit("heldout", y, s, s, nm, ch, pre=1.0, post=2.0)
                rows[-1]["counted_by_shawn"] = bool(h.get("counted_by_shawn"))
        if h.get("counted_by_shawn"):
            wwrite(os.path.join(out, "positives", "heldout", "counted_20261112_0056_3ch.wav"),
                   x[int(15.5 * FS):int(28.5 * FS), :3].reshape(-1), ch=3)

    # negatives: round-6 real negatives as built by prep_v6, which cuts 2 s clips every 1 s. Overlapping clips with
    # times in their names can be stitched back into continuous talk, so only a clip every GAP_S seconds is kept
    # (2 s of each 4 s) and each gets an opaque name that keeps only its kind (life, life6, live, calls, own).
    n_neg, kinds = 0, {}
    for p in sorted(glob.glob(os.path.join(OWW, "data", "real_neg", "*.wav"))):
        m = re.match(r"([a-z0-9]+)_(.*)_(\d{4})\.wav$", os.path.basename(p))
        if m is None or int(m.group(3)) % GAP_S:
            continue
        tag = hashlib.sha256((SALT + os.path.basename(p)).encode()).hexdigest()[:12]
        shutil.copy2(p, os.path.join(out, "negatives", "train", f"{m.group(1)}_{tag}.wav"))
        kinds[m.group(1)] = kinds.get(m.group(1), 0) + 1
        n_neg += 1
    # held-out no-call talk, cut into 2 s clips
    n_ht = 0
    for nm, spans in json.load(open(os.path.join(OWW, "data", "life_heldout.json"))).items():
        y = mono(nm)
        for t0, t1 in spans:
            for s in np.arange(t0, t1 - 2.0 + 1e-6, float(GAP_S)):
                tag = hashlib.sha256(f"{SALT}{nm}{s:.1f}".encode()).hexdigest()[:12]
                wwrite(os.path.join(out, "negatives", "heldout_talk", f"talk_{tag}.wav"), cut(y, s, s + 2.0))
                n_ht += 1

    # background, synthetic set, web clips, models, config
    shutil.copytree(os.path.join(OWW, "data", "bg_roboclub"), os.path.join(out, "background", "roboclub"), dirs_exist_ok=True)
    shutil.copytree(os.path.join(OWW, "data", "bg_motion", "train.v4"), os.path.join(out, "background", "robot_motion"),
                    dirs_exist_ok=True)
    shutil.copytree(os.path.join(D, "set"), os.path.join(out, "synthetic_set"), dirs_exist_ok=True)
    for d in ("web_pos", "web_neg"):
        shutil.copytree(os.path.join(OWW, "data", d), os.path.join(out, "web", d), dirs_exist_ok=True)
    shutil.copy2(os.path.join(OWW, "data", "web_heldout.json"), os.path.join(out, "web"))
    shutil.copy2(os.path.join(OWW, "models", "mochi_v4.onnx"), os.path.join(out, "models"))
    shutil.copy2(os.path.join(OWW, "mochi.yml"), os.path.join(out, "models", "mochi_v4_train_config.yml"))

    with open(os.path.join(out, "manifest.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    cnt = lambda sub: len(os.listdir(os.path.join(out, sub)))
    summ = dict(train_calls=len({(r["source"], r["start"]) for r in rows if r["split"] == "train"}),
                heldout_calls=len({(r["source"], r["start"]) for r in rows if r["split"] == "heldout"}),
                counted_calls=len({r["start"] for r in rows if r.get("counted_by_shawn")}),
                positive_clips=len(rows), negatives_train=n_neg, negatives_train_by_kind=kinds, heldout_talk_clips=n_ht,
                heldout_talk_min=round(n_ht * 2 / 60, 1))
    json.dump(summ, open(os.path.join(out, "summary.json"), "w"), indent=1)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
