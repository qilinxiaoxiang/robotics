#!/usr/bin/env python3
"""openWakeWord "mochi" round 6 on the Mac mini: round 3/4 data plus Shawn's calls and talk from the life log since
2026-11-02, and positives cut with a wider time and level spread.

Why (2026-11-12 00:56, NAMECALL REQUIREMENTS R2): four quiet-room calls scored 0.60, 0.21, 0.49, 0.90 on v4; the
same call moved 0.01-0.62 when the frame grid shifted 10 ms, and raising the gain made it worse (call 3: median
0.21 at +0, 0.05 at +14 dB), so the model, not the level, is the problem. v4's real positives were 77 calls from
10/29-10/30, at a median level 7-9 dB above these calls.

  positives   prep_v3's gated calls, cut with JIT_PRE / POST_RANGE / GAIN_DB (was +-0.08 s, 0.10 s, +-6 dB), plus
              mine_v6.py candidates that pass the accept rule (--zc / --v4min, chosen by mine_v6.py --validate), from
              the TRAIN_DAYS life files only: the ear mix and each ear alone, cut on the candidate's voiced burst.
  held out    life files of HELD_FROM on (the 11-11 evening session) and the 11-12 test segment: written to
              data/new_heldout_v6.json (file -> burst starts) for score_v6.py; never trained on.
  negatives   prep_v3's, plus 2 s chunks of the TRAIN_DAYS life files at least NEG_GAP_S from any candidate
              (z >= 3 at all) and from any live score >= 0.1: Shawn talking at home since 11-02 with no call.

  ~/.venvs/oww/bin/python prep_v6.py --zc 4 --v4min 0.05
"""
import argparse
import glob
import json
import os
import wave

import numpy as np

import prep_v3 as p3

OWW = p3.OWW
OUT = p3.OUT
FS = p3.FS
MINE = os.path.join(OUT, "mine_v6.json")
LIFE_INDEX = "/Users/shawnxiang/mochi-train/life_v6/life_index.jsonl"
TRAIN_DAYS = ("20261102", "20261104", "20261106", "20261111")
HELD_FROM = "life_20261111_200000_000"          # names sort by time: this file name and later stay held out
JIT_PRE = 0.12
POST_RANGE = (0.05, 0.35)
GAIN_DB = (-12.0, 6.0)
NEG_GAP_S = 2.0
K_NEW, K_NEW_EAR = 30, 10
rng = np.random.default_rng(6)


def cut_calls(y, spans, tag, k, out_dir):
    """prep_v3.cut_calls with a wider spread: start jitter +-JIT_PRE, trailing room POST_RANGE, gain GAIN_DB."""
    n = 0
    for j, (s, e) in enumerate(spans):
        for c in range(k):
            s0 = s - p3.PRE_S + rng.uniform(-JIT_PRE, JIT_PRE)
            e0 = e + rng.uniform(*POST_RANGE)
            i0, i1 = max(0, int(s0 * FS)), min(len(y), int(e0 * FS))
            seg = y[i0:i1] * 10 ** (rng.uniform(*GAIN_DB) / 20)
            peak = np.abs(seg).max() if len(seg) else 0
            if peak > 0.98:
                seg = seg * 0.98 / peak
            p3.wwrite(os.path.join(out_dir, f"duck_{tag}_{j:03d}_{c:02d}.wav"), seg)
            n += 1
    return n


def read_life(path):
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, w.getnchannels()).astype(np.float32) / 32768
    return x[:, :2].mean(axis=1), x


def live_index():
    """file -> (times of live scores >= 0.1, times of the duck's own answers)."""
    out = {}
    for line in open(LIFE_INDEX):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        nm = "life_" + r["file"].replace("/", "_")[:-4]
        out[nm] = ([t for t, p in (r.get("scores") or []) if p >= 0.1],
                   [n["t"] for n in (r.get("notes") or []) if n.get("kind") == "answer"])
    return out


QUACK_AFTER_ANSWER_S = (0.0, 3.0)     # the duck's own quack follows its answer note; on 11-12 00:56 the quack 0.65 s
                                      # after the answer matched the call templates best of all (z 6.3, v4 0.001)


def accept(c, zc, v4min, answers=()):
    own = any(QUACK_AFTER_ANSWER_S[0] <= c["burst"][0] - t <= QUACK_AFTER_ANSWER_S[1] for t in answers) if c["burst"] else False
    return c["z"] >= zc and c["burst_ok"] and (c["v4"] or 0) >= v4min and not own


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zc", type=float, required=True)
    ap.add_argument("--v4min", type=float, required=True)
    a = ap.parse_args()
    p3.cut_calls = cut_calls                     # the round-3 calls get the same wider spread
    p3.main()                                    # rebuilds duck_pos, real_neg, bg_roboclub, held-out lists
    counts = json.load(open(os.path.join(OUT, "counts_v3.json")))

    mine = json.load(open(MINE))
    index = live_index()
    new_calls, held, n_clips, n_neg, neg_s = {}, {}, 0, 0, 0.0
    p3.clear(os.path.join(OUT, "real_neg", "life6_*.wav"))
    for nm, r in sorted(mine.items()):
        day = nm.split("_")[1]
        if day not in TRAIN_DAYS:
            continue
        live, answers = index.get(nm, ([], []))
        acc = [c for c in r["cands"] if accept(c, a.zc, a.v4min, answers)]
        if nm >= HELD_FROM:
            if acc:
                held[nm] = dict(file=r["file"], starts=[c["burst"][0] for c in acc])
            continue
        mix, x = read_life(r["file"])
        if acc:
            spans = [tuple(c["burst"]) for c in acc]
            new_calls[nm] = len(spans)
            n_clips += cut_calls(mix, spans, nm, K_NEW, os.path.join(OUT, "duck_pos"))
            for ch in (0, 1):
                n_clips += cut_calls(x[:, ch], spans, f"{nm}_ch{ch}", K_NEW_EAR, os.path.join(OUT, "duck_pos"))
        busy = [c["t"] for c in r["cands"]] + live + [t + 1.5 for t in answers]
        for s in range(0, len(mix) - 2 * FS + 1, FS):
            t0, t1 = s / FS, s / FS + 2.0
            if any(t - NEG_GAP_S < t1 and t + NEG_GAP_S > t0 for t in busy):
                continue
            p3.wwrite(os.path.join(OUT, "real_neg", f"life6_{nm}_{s // FS:04d}.wav"), mix[s:s + 2 * FS])
            n_neg += 1
            neg_s += 2.0
    # the test segment of 11-12 00:56 (four calls Shawn counted) is held out by its own file
    held["life_20261112_005609_732"] = dict(file="/Users/shawnxiang/mochi-train/life_test/20261112/005609_732.wav",
                                            starts=[17.37, 19.84, 22.36, 24.74], counted_by_shawn=True)
    for p in glob.glob(os.path.join(OUT, "duck_pos", "duck_life_*.wav")):
        dst = os.path.join(p3.POS_TRAIN, os.path.basename(p))
        if not os.path.exists(dst):
            os.link(p, dst)
    json.dump(held, open(os.path.join(OUT, "new_heldout_v6.json"), "w"), indent=1)
    counts.update(rule=dict(zc=a.zc, v4min=a.v4min), new_calls=sum(new_calls.values()), new_calls_per_file=new_calls,
                  new_pos_clips=n_clips, new_heldout_calls={k: len(v["starts"]) for k, v in held.items()},
                  new_life_neg_clips=n_neg, new_life_neg_minutes=round(neg_s / 60, 1),
                  positive_train_total=len(os.listdir(p3.POS_TRAIN)),
                  real_neg_total=len(os.listdir(os.path.join(OUT, "real_neg"))),
                  spread=dict(jit_pre=JIT_PRE, post=POST_RANGE, gain_db=GAIN_DB))
    json.dump(counts, open(os.path.join(OUT, "counts_v6.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in counts.items() if k != "new_calls_per_file"}, indent=1))


if __name__ == "__main__":
    main()
