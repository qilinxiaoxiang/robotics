"""Tune and judge the "Mochi" keyword spotter of namecall.py --name mochi on robot-format audio.

Every clip of mochi_set.py (say voices) and every duck call the robot plays (pet/express recordings, raw and the
QuackBank pitch x length variants) and synthetic claps is rendered as a far-field source at a random azimuth onto the
head's three microphones (namecall.render geometry, fractional delays), into 4-channel 48 kHz noise in the robot's
format (ch0 left ear, ch1 right ear, ch2 back mic, ch3 zero; pink noise plus mains hum at the room floor the detector
read on the robot, -35 dB in its units), at 20 and 10 dB SNR (speech RMS over its active span against the noise RMS).

  grid   stage 1: recall on the tuning voices (even-indexed voices) for keyword sets x boost x threshold; stage 2: the
         best stage-1 settings on all negatives (words, own calls, claps, 22 min of continuous speech). Spotter only,
         on the ear downmix at 16 kHz made by namecall.Decimate3, exactly as KeywordGate feeds it.
  final  the chosen keywords file through the whole namecall chain (NameCall with KeywordGate, 20 ms blocks):
         detection per SNR, voice and accent, held-out voices separately, false alarms per hour of speech, own-call
         wakes, direction error at the word, latency from the end of the name to the decision, spot-minus-start lags.

  nice -n 19 pet/.venv/bin/python kws_mochi_eval.py --set DIR grid  --out results/kws_mochi_grid.json
  nice -n 19 pet/.venv/bin/python kws_mochi_eval.py --set DIR final --keywords keywords_mochi.txt --out results/kws_mochi.json
"""
import argparse
import glob
import json
import math
import os
import sys
import time
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
sys.path.insert(0, MAC)
import namecall as nc  # noqa: E402
from pet.express.voice import find_calls, read_wav, render_call  # noqa: E402

FS = nc.FS
FLOOR_DB = -35.0              # detector floor (band energy, namecall units) on the robot, 2026-10-29
LEAD_S, TAIL_S = 1.5, 1.6
MATCH_AFTER_S = 1.3           # a spot up to this long after the clip's speech ends belongs to it

# v1/v2: the spelling. v5-v7: what the model itself writes for "Mochi" when it decodes the say clips as a plain
# recogniser (results/kws_mochi_heard.txt): MARCHY above all, MALCHY / MALCHI / MACHI, MORGY, MARGIE, MUTCHY; the
# Chinese voices' "Mochi" comes out as MOTION, which only v7 accepts (and "motion" is a negative word).
_V5 = [("MOCHI", "▁MO CH I"), ("MO CHI", "▁MO ▁CHI"), ("MARCHY", "▁MAR CH Y"), ("MALCHY", "▁MA L CH Y"),
       ("MALCHI", "▁MA L CH I"), ("MACHI", "▁MA CH I"), ("MARCHI", "▁MAR CH I")]
_V6 = _V5 + [("MORGY", "▁MO R G Y"), ("MARGIE", "▁MAR G I E"), ("MUTCHY", "▁MU T CH Y")]
VARIANTS = {
    "v1": [("MOCHI", "▁MO CH I")],
    "v2": [("MOCHI", "▁MO CH I"), ("MO CHI", "▁MO ▁CHI")],
    "v5": _V5,
    "v6": _V6,
    "v7": _V6 + [("MOTION", "▁MO TION")],
}


def keywords_text(variant, boost, thr):
    return "".join(f"{toks} :{boost} #{thr} @MOCHI\n" for _, toks in VARIANTS[variant])


# ------------------------------------------------------------------------------------------------ audio

def read48(path):
    x, rate = read_wav(path)
    if rate != FS:
        n = int(round(len(x) * FS / rate))
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)
    return x.astype(np.float32)


def robot_noise(n, rng, level=1.0):
    """(n, 4) pink noise plus mains hum on ch0-2, ch3 zero; unit-free, scaled by the caller."""
    out = np.zeros((n, 4), np.float32)
    f = np.fft.rfftfreq(n, 1 / FS)
    shape = 1 / np.sqrt(np.maximum(f, 20.0))
    t = np.arange(n) / FS
    hum = sum(a * np.sin(2 * math.pi * h * 60 * t + rng.uniform(0, 6.3)) for h, a in ((1, 1.0), (2, 0.5), (3, 0.3)))
    for ch in range(3):
        w = np.fft.irfft(np.fft.rfft(rng.standard_normal(n)) * shape, n)
        w = w / (w.std() + 1e-12)
        out[:, ch] = (w + 0.3 * hum) * level
    return out


def noise_scale():
    """Noise level whose detector floor reads FLOOR_DB."""
    rng = np.random.default_rng(1)
    x = robot_noise(FS * 2, rng)
    det = nc.OnsetDetector()
    e = np.median([det.level(x[i:i + nc.BLOCK])[0] for i in range(0, len(x) - nc.BLOCK, nc.BLOCK)])
    return 10 ** ((FLOOR_DB - e) / 20)


def place(sig, az, n, at):
    """Far-field source `sig` from azimuth az onto the four channels, starting at sample `at` of an n-sample scene."""
    out = np.zeros((n, 4), np.float32)
    m = len(sig) + 256
    S = np.fft.rfft(sig, m)
    f = np.fft.rfftfreq(m, 1 / FS)
    u = np.array([math.cos(az), math.sin(az)])
    for name, ch in nc.CHANNELS.items():
        d = -(u @ (np.asarray(nc.MICS_MM[name], float) / 1000.0)) / nc.C_SOUND + 64 / FS   # +64 samples so no wrap
        y = np.fft.irfft(S * np.exp(-2j * math.pi * f * d), m).astype(np.float32)
        k = min(m, n - at)
        out[at:at + k, ch] = y[:k]
    return out, 64 / FS


def band_rms(x, band=nc.BAND):
    """RMS of x (n,) or (n, k) inside the voice band (300-4000 Hz), averaged over columns."""
    x = np.asarray(x, np.float64)
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(len(x), 1 / FS)
    X[(f < band[0]) | (f > band[1])] = 0
    y = np.fft.irfft(X, len(x), axis=0)
    return float(np.sqrt(np.mean(y ** 2))) + 1e-12


class RobotBed:
    """Noise taken from a real robot recording (4 channels as captured), random excerpts."""

    def __init__(self, path):
        self.x = nc.WavSource(path).x

    def __call__(self, n, rng, level=None):
        i = int(rng.integers(0, len(self.x)))
        return np.take(self.x, np.arange(i, i + n), axis=0, mode="wrap").astype(np.float32)


NOISE = {"bed": None}       # set to a RobotBed to mix into real robot noise instead of the synthetic floor


def segments(items, snr_db, seed, nscale):
    """items: dicts with sig, span (start, end in the clip). Yields (segment (n, 4), meta) with meta times inside the
    segment: word start/end (speech span), azimuth. SNR is in the voice band (300-4000 Hz): the speech's band RMS
    over its active span against the noise's band RMS on the microphone channels."""
    rng = np.random.default_rng(seed)
    for it in items:
        sig = it["sig"]
        s0, s1 = it["span"]
        act = sig[int(s0 * FS):max(int(s1 * FS), int(s0 * FS) + 256)]
        rms = band_rms(act)
        n = int((LEAD_S + TAIL_S) * FS) + len(sig) + 512
        noise = NOISE["bed"](n, rng) if NOISE["bed"] is not None else robot_noise(n, rng, nscale)
        nrms = band_rms(noise[:, :3]) if n < FS * 30 else band_rms(noise[: FS * 30, :3])
        gain = nrms * 10 ** (snr_db / 20) / rms
        az = float(rng.uniform(-math.pi, math.pi))
        at = int(LEAD_S * FS)
        src, pad = place(sig * gain, az, len(noise), at)
        meta = dict(it.get("meta", {}), az=az, start=LEAD_S + pad + s0, end=LEAD_S + pad + s1,
                    dur=len(noise) / FS)
        yield noise + src, meta


def downmix16(seg, dec):
    return dec(seg[:, :2].mean(axis=1))


# ------------------------------------------------------------------------------------------------ spotter only

class Spot:
    def __init__(self, model, kw_text, tmpdir, tag):
        import sherpa_onnx
        p = os.path.join(tmpdir, f"kw_{tag}.txt")
        open(p, "w").write(kw_text)
        one = lambda s: nc.model_file(model, s)
        self.k = sherpa_onnx.KeywordSpotter(tokens=os.path.join(model, "tokens.txt"), encoder=one("encoder"),
                                            decoder=one("decoder"), joiner=one("joiner"), keywords_file=p,
                                            num_threads=1)

    def run(self, x16, hop=1600):
        s = self.k.create_stream()
        hits = []
        for i in range(0, len(x16) - hop + 1, hop):
            s.accept_waveform(16000, x16[i:i + hop])
            while self.k.is_ready(s):
                self.k.decode_stream(s)
                r = self.k.keyword_spotter.get_result(s)
                if r.keyword.strip():
                    hits.append((i + hop) / 16000.0)
                    self.k.reset_stream(s)
        return hits


def build_stream16(items, snr, seed, nscale):
    """Concatenated 16 kHz ear downmix of all segments, with each item's (start, end) in stream seconds."""
    dec = nc.Decimate3()
    parts, metas, t = [], [], 0.0
    for seg, meta in segments(items, snr, seed, nscale):
        n = len(seg) - len(seg) % nc.BLOCK
        parts.append(np.concatenate([downmix16(seg[i:i + nc.BLOCK], dec) for i in range(0, n, nc.BLOCK)]))
        metas.append(dict(meta, start=t + meta["start"], end=t + meta["end"], t0=t))
        t += n / FS
    return np.concatenate(parts).astype(np.float32), metas


def score_hits(hits, metas, positive):
    """Per item: hit inside [start - 0.2, end + MATCH_AFTER_S] (positives) and the rest as false alarms."""
    got = [False] * len(metas)
    stray = []
    for h in hits:
        owner = None
        for i, m in enumerate(metas):
            if m["start"] - 0.2 <= h <= m["end"] + MATCH_AFTER_S:
                owner = i
                break
        if owner is not None:
            got[owner] = True
            if not positive:
                stray.append(h)
        else:
            stray.append(h)
    return got, stray


# ------------------------------------------------------------------------------------------------ sets

def load_set(set_dir):
    rows = json.load(open(os.path.join(set_dir, "manifest.json")))
    for r in rows:
        r["sig"] = read48(os.path.join(set_dir, r["file"]))
        r["span"] = (r["speech_start"], r["speech_end"])
        r["meta"] = {k: r[k] for k in ("file", "kind", "text", "voice", "accent", "rate", "mochi_last", "group")}
    return rows


def duck_calls():
    """Every recording the robot can play, raw, plus the QuackBank variants it actually plays (first 4 sources x
    4 pitches x 3 lengths)."""
    out = []
    srcs = find_calls()
    for si, p in enumerate(srcs):
        x, rate = read_wav(p)
        out.append((os.path.basename(p), 1.0, 1.0, x, rate))
        if si < 4:
            for pi in nc.QuackBank.PITCHES:
                for st in nc.QuackBank.STRETCHES:
                    out.append((os.path.basename(p), pi, st, render_call(x, pi, st, 0.0) * 0.9, rate))
    items = []
    for name, pi, st, x, rate in out:
        if rate != FS:
            x = np.interp(np.linspace(0, len(x) - 1, int(round(len(x) * FS / rate))), np.arange(len(x)), x)
        x = np.asarray(x, np.float32)
        e = np.abs(x) > 0.02 * np.abs(x).max()
        span = (np.argmax(e) / FS, (len(x) - np.argmax(e[::-1])) / FS)
        items.append(dict(sig=x, span=span, meta=dict(kind="quack", file=name, pitch=pi, stretch=st)))
    return items


def claps(n=24):
    items = []
    for s in range(n):
        x = nc.synth_call(kind="clap", seed=100 + s)
        if s % 3 == 2:   # double clap
            x = np.concatenate([x[:int(0.25 * FS)], x])
        items.append(dict(sig=x.astype(np.float32), span=(0.0, len(x) / FS), meta=dict(kind="clap", seed=s)))
    return items


# ------------------------------------------------------------------------------------------------ grid

def grid(a):
    rows = load_set(a.set)
    nscale = noise_scale()
    pos_tune = [r for r in rows if r["kind"] in ("pos", "pos_zh") and r["group"] == "tune"]
    tmp = a.tmp
    os.makedirs(tmp, exist_ok=True)
    t0 = time.time()
    streams = {}
    for snr in (20, 10):
        streams[f"pos{snr}"] = build_stream16(pos_tune, snr, 7 + snr, nscale)
    if a.bed:
        NOISE["bed"] = RobotBed(a.bed)
        streams["posR10"] = build_stream16(pos_tune, 10, 17, nscale)
        NOISE["bed"] = None
    print(f"tune streams built in {time.time() - t0:.0f} s", flush=True)
    stage1 = []
    for v in a.variants.split(","):
        for boost in (1.0, 2.0, 3.0):
            for thr in (0.05, 0.10, 0.20):
                sp = Spot(a.model, keywords_text(v, boost, thr), tmp, "g")
                res = dict(variant=v, boost=boost, thr=thr)
                for key, (x16, metas) in streams.items():
                    got, stray = score_hits(sp.run(x16), metas, True)
                    pos = [g for g, m in zip(got, metas) if m["kind"] == "pos"]
                    res[key] = round(sum(pos) / len(pos), 3)
                    res[key + "_strays"] = len(stray)
                keys = [k for k in streams]
                res["recall"] = round(sum(res[k] for k in keys) / len(keys), 3)
                stage1.append(res)
                print(json.dumps(res), flush=True)
    stage1.sort(key=lambda r: -r["recall"])
    # stage 2: negatives for the best settings (and the strictest setting of each variant for contrast)
    negs = [r for r in rows if r["kind"] == "neg_word"]
    speech = [r for r in rows if r["kind"] == "speech"]
    neg_streams = dict(words=build_stream16(negs, 20, 31, nscale), speech=build_stream16(speech, 20, 32, nscale),
                       quack=build_stream16(duck_calls(), 20, 33, nscale), quack30=build_stream16(duck_calls(), 30, 34, nscale),
                       clap=build_stream16(claps(), 20, 35, nscale))
    speech_h = sum(m["end"] - m["start"] for m in neg_streams["speech"][1]) / 3600
    pick = stage1[:a.top]
    stage2 = []
    for r in pick:
        sp = Spot(a.model, keywords_text(r["variant"], r["boost"], r["thr"]), tmp, "g2")
        res = dict(r)
        for key, (x16, metas) in neg_streams.items():
            hits = sp.run(x16)
            got, _ = score_hits(hits, metas, False)
            res[key + "_hits"] = len(hits)
            if key == "words":
                res["words_woke"] = sorted({m["text"] for g, m in zip(got, metas) if g})
        res["fa_per_h"] = round(res["speech_hits"] / speech_h, 1)
        stage2.append(res)
        print(json.dumps(res, ensure_ascii=False), flush=True)
    out = dict(made=time.strftime("%Y-%m-%d %H:%M"), set=a.set, model=a.model, floor_db=FLOOR_DB,
               n_tune_pos=len(pos_tune), speech_hours=round(speech_h, 3), stage1=stage1, stage2=stage2)
    json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
    print(f"wrote {a.out} in {time.time() - t0:.0f} s")


# ------------------------------------------------------------------------------------------------ final (whole chain)

def chain_args(a):
    p = nc.parse_args(["--name", "mochi", "--no-head", "--no-sound", "--mute", "--no-gate", "--kws-keywords", a.keywords,
                       "--kws-model", a.model, "--quiet"])
    return p


def run_chain(a, items, snr, seed, nscale, positive):
    """Concatenate the segments and stream them through one NameCall (as the robot would hear them in a row)."""
    n = nc.NameCall(chain_args(a), nc.Log(None, echo=False), now=lambda: 0.0)
    metas, t, calls = [], 0.0, []
    cpu0 = time.process_time()
    audio = 0.0
    for seg, meta in segments(items, snr, seed, nscale):
        m = len(seg) - len(seg) % nc.BLOCK
        metas.append(dict(meta, start=t + meta["start"], end=t + meta["end"]))
        dets = n.run_blocks(((t + i / FS, seg[i:i + nc.BLOCK]) for i in range(0, m, nc.BLOCK)))
        calls += dets
        t += m / FS
        audio += m / FS
    cpu = time.process_time() - cpu0
    hits = [c["t_hit"] for c in calls]
    got, stray = score_hits(hits, metas, positive)
    per = []
    for i, m in enumerate(metas):
        mine = [c for c in calls if m["start"] - 0.2 <= c["t_hit"] <= m["end"] + MATCH_AFTER_S]
        rec = dict(m, hit=bool(mine))
        if mine:
            c = mine[0]
            err = (c["az_rad"] - m["az"] + math.pi) % (2 * math.pi) - math.pi
            rec.update(az_err_deg=round(abs(math.degrees(err)), 1), onset_from=c["onset_from"],
                       t_onset_minus_start=round(c["t"] - m["start"], 3), spot_minus_start=round(c["t_hit"] - m["start"], 3),
                       spot_minus_end=round(c["t_hit"] - m["end"], 3), decide_minus_end=round(c["decided_t"] - m["end"], 3))
        per.append(rec)
    return dict(per=per, strays=len(stray), kw_hits=n.kw_hits, audio_s=round(audio, 1), cpu_s=round(cpu, 2),
                hours=sum(m["end"] - m["start"] for m in metas) / 3600)


def pct(v, q):
    return round(float(np.percentile(v, q)), 3) if len(v) else None


def summarise_pos(per):
    def rate(rows):
        return dict(n=len(rows), detected=sum(r["hit"] for r in rows),
                    rate=round(sum(r["hit"] for r in rows) / len(rows), 3) if rows else None)
    out = dict(all=rate(per), tune=rate([r for r in per if r["group"] == "tune"]),
               heldout=rate([r for r in per if r["group"] == "test"]),
               en=rate([r for r in per if r["accent"] == "en"]), zh=rate([r for r in per if r["accent"] == "zh"]))
    out["by_voice"] = {v: rate([r for r in per if r["voice"] == v]) for v in sorted({r["voice"] for r in per})}
    out["by_text"] = {v: rate([r for r in per if r["text"] == v]) for v in sorted({r["text"] for r in per})}
    hit = [r for r in per if r["hit"]]
    last = [r for r in hit if r["mochi_last"]]
    first = [r for r in hit if r["text"].startswith("Mochi")]
    out["az_err_deg"] = dict(mean=round(float(np.mean([r["az_err_deg"] for r in hit])), 2) if hit else None,
                             p90=pct([r["az_err_deg"] for r in hit], 90), max=max([r["az_err_deg"] for r in hit], default=None),
                             over_20=sum(r["az_err_deg"] > 20 for r in hit))
    out["onset_from"] = {k: sum(r["onset_from"] == k for r in hit) for k in ("detector", "keyword")}
    out["decide_after_end_s"] = dict(n=len(last), p10=pct([r["decide_minus_end"] for r in last], 10),
                                     p50=pct([r["decide_minus_end"] for r in last], 50),
                                     p90=pct([r["decide_minus_end"] for r in last], 90),
                                     max=max([r["decide_minus_end"] for r in last], default=None))
    out["spot_after_word_start_s"] = dict(n=len(first), p10=pct([r["spot_minus_start"] for r in first], 10),
                                          p50=pct([r["spot_minus_start"] for r in first], 50),
                                          p90=pct([r["spot_minus_start"] for r in first], 90))
    return out


def final(a):
    rows = load_set(a.set)
    nscale = noise_scale()
    t0 = time.time()
    res = dict(made=time.strftime("%Y-%m-%d %H:%M"), keywords=open(a.keywords).read(), model=a.model, floor_db=FLOOR_DB,
               ring_s=nc.RING_NAME_S, kw_back_s=nc.KW_BACK_S, kw_onset_win=nc.KW_ONSET_WIN,
               snr="voice band (300-4000 Hz) RMS of the speech's active span over the noise's, microphone channels")
    pos = [r for r in rows if r["kind"] == "pos"]
    pos_zh = [r for r in rows if r["kind"] == "pos_zh"]
    negs = [r for r in rows if r["kind"] == "neg_word"]
    speech = [r for r in rows if r["kind"] == "speech"]
    conds = [("synthetic", None)] + ([("robot", RobotBed(a.bed))] if a.bed else [])
    for cname, bed in conds:
        NOISE["bed"] = bed
        out = res.setdefault(cname, {})
        for snr in (20, 10):
            r = run_chain(a, pos, snr, 50 + snr, nscale, True)
            out[f"pos_{snr}db"] = dict(summarise_pos(r["per"]), strays=r["strays"])
            out[f"pos_{snr}db_cost_mac"] = dict(audio_s=r["audio_s"], cpu_s=r["cpu_s"],
                                                cpu_share=round(r["cpu_s"] / r["audio_s"], 4))
            r2 = run_chain(a, pos_zh, snr, 60 + snr, nscale, True)
            out[f"pos_zh_phonetic_{snr}db"] = dict(summarise_pos(r2["per"]), strays=r2["strays"])
            print(f"[{cname}] {snr} dB: {out[f'pos_{snr}db']['all']} zh-phonetic {out[f'pos_zh_phonetic_{snr}db']['all']}"
                  f"  {time.time() - t0:.0f} s", flush=True)
        for snr in ((20, 10) if bed is None else (10,)):
            w = run_chain(a, negs, snr, 70 + snr, nscale, False)
            out[f"neg_words_{snr}db"] = dict(n=len(negs), woke=sum(r["hit"] for r in w["per"]),
                                             words=sorted({r["text"] for r in w["per"] if r["hit"]}), kw_hits=w["kw_hits"])
            s = run_chain(a, speech, snr, 80 + snr, nscale, False)
            out[f"speech_{snr}db"] = dict(minutes=round(s["hours"] * 60, 1), kw_hits=s["kw_hits"],
                                          fa_per_hour=round(s["kw_hits"] / s["hours"], 1),
                                          at=[r["file"] for r in s["per"] if r["hit"]])
            print(f"[{cname}] negatives {snr} dB: words {out[f'neg_words_{snr}db']['woke']}/{len(negs)}, speech "
                  f"{s['kw_hits']} in {s['hours'] * 60:.1f} min  {time.time() - t0:.0f} s", flush=True)
        for snr in ((30, 20, 10) if bed is None else (20,)):
            q = run_chain(a, duck_calls(), snr, 90 + snr, nscale, False)
            out[f"own_calls_{snr}db"] = dict(n=len(q["per"]), woke=sum(r["hit"] for r in q["per"]), kw_hits=q["kw_hits"])
        if bed is None:
            c = run_chain(a, claps(), 20, 99, nscale, False)
            out["claps_20db"] = dict(n=len(c["per"]), woke=sum(r["hit"] for r in c["per"]), kw_hits=c["kw_hits"])
        print(f"[{cname}] own calls {[v['kw_hits'] for k, v in out.items() if k.startswith('own_calls')]}", flush=True)
    NOISE["bed"] = None
    if a.bed:   # the robot recording itself, as heard
        n = nc.NameCall(chain_args(a), nc.Log(None, echo=False), now=lambda: 0.0)
        src = nc.WavSource(a.bed)
        n.run_blocks(src.blocks())
        res["robot_recording_as_is"] = dict(file=os.path.basename(a.bed), seconds=round(len(src.x) / FS, 1),
                                            kw_hits=n.kw_hits, responses=n.responses)
    json.dump(res, open(a.out, "w"), indent=1, ensure_ascii=False)
    print(f"wrote {a.out} in {time.time() - t0:.0f} s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, help="mochi_set.py output folder")
    ap.add_argument("--model", default=nc.find_kws_model())
    ap.add_argument("--tmp", default="/tmp/kws_mochi_eval")
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--variants", default="v2,v5,v6,v7")
    ap.add_argument("--keywords", default=nc.KEYWORDS["mochi"])
    ap.add_argument("--bed", default=None, help="a 4-channel robot recording: also mix into its real noise")
    ap.add_argument("--out", required=True)
    ap.add_argument("what", choices=("grid", "final"))
    a = ap.parse_args()
    (grid if a.what == "grid" else final)(a)


if __name__ == "__main__":
    main()
