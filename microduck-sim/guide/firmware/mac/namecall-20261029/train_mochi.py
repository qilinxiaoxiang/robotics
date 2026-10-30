"""Train the duck's own "Mochi" spotter (ownkws.OwnModel) from Shawn's recorded calls.

Recipe of the Edge Impulse keyword lab (18-763 lecture 21): one-second windows, spectral features, a small time
convolution, the keyword against "other speech" and "noise / silence". Here:

  mochi   Shawn's calls on the robot's ears: the events of the call recordings listed in the labels file
          (call_spans: voiced runs 0.2-1.0 s long, see events()), plus fixed held-out call times (calls_heldout). Augmented: window start jittered so the word sits anywhere a scoring window holds it,
          home-floor noise at 3-20 dB SNR, speed 0.9-1.1, gain.
  speech  other speech: Google Speech Commands v0.02 (35 words, thousands of speakers, the lab's dataset), mixed into
          the robot's home floor noise at 5-25 dB; the no-call lab conversation recordings; the duck's own quacks;
          the synthetic neg_word clips of mochi_set.py (near-misses: mocha, macho, Mickey, moshi).
  noise   quiet and non-voice stretches of the robot recordings and the Speech Commands background noise files.

Held out (never trained on): the last HOLDOUT_FRAC of each call recording's events, the six calls of
live_073135 (another session), and the 22 minutes of synthetic continuous speech (false wakes per hour). The
spotter is run on them exactly as on the robot (a 1 s window every 100 ms, REFRACTORY_S), and the threshold is
the lowest whose false wakes stay under --fa-per-h.

  <scratch venv with torch>/python train_mochi.py --mono16 DIR --labels mochi_labels.json --speech-commands DIR \\
      --set SETDIR --out models/mochi_own.npz --report results/mochi_own.json
"""
import argparse
import glob
import json
import os
import sys
import time
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
for p in (HERE, MAC):
    if p not in sys.path:
        sys.path.insert(0, p)
import ownkws as ok  # noqa: E402

FS = ok.FS16
WIN_N = int(ok.WINDOW_S * FS)
CLASSES = ["mochi", "speech", "noise"]
HOLDOUT_FRAC = 0.25


def unmatched_cues(pos, neg):
    """Cues (speaker, synthetic voice, room kept around the word) that some positives carry and no negative does: the
    model can then learn the cue instead of the word. 2026-10-30: synthetic-voice Mochi without synthetic-voice
    speech gave 2000+ false wakes/h, RoboClub calls on their own background without enough of that room's babble
    taught 'babble = mochi'; both times the source was dropped instead of matched."""
    return sorted(c for c, n in pos.items() if n and not neg.get(c))


# ------------------------------------------------------------------------------------------------- audio helpers

def band_db(x):
    X = np.fft.rfft(x * np.hanning(len(x)))
    f = np.fft.rfftfreq(len(x), 1 / FS)
    b = (f >= 300) & (f <= 4000)
    return 10 * np.log10(np.mean(np.abs(X[b]) ** 2) + 1e-14)


def levels(y, hop=0.02, win=0.04):
    n, h = int(win * FS), int(hop * FS)
    return np.array([band_db(y[i:i + n]) for i in range(0, len(y) - n, h)])


def onsets(y, lv=None, hop=0.02, rise_db=8.0, min_gap=0.4):
    lv = levels(y) if lv is None else lv
    fl = np.percentile(lv, 20)
    out, last = [], -9.0
    for i, v in enumerate(lv):
        t = i * hop
        if v < fl + 6:
            fl += (min(v, fl + 0.5) - fl) * 0.02
        if v > fl + rise_db and t - last > min_gap:
            out.append(t)
            last = t
    return out


def events(y, t0, t1, rise_db=8.0, bridge_s=0.25, min_s=0.2, max_s=1.0):
    """Utterances in [t0, t1]: voiced runs (voice-band level over the 20th-percentile floor by rise_db, 20 ms hops)
    joined across gaps shorter than bridge_s (the stop inside "Mo-chi"), kept when min_s..max_s long. A name call is
    0.3-0.7 s; "Mochi, come here" runs longer and is skipped."""
    lv = levels(y)
    fl = np.percentile(lv, 20)
    on = lv > fl + rise_db
    nb = int(round(bridge_s / 0.02))
    out, i = [], 0
    while i < len(on):
        if not on[i]:
            i += 1
            continue
        j = i
        while j < len(on) and (on[j] or on[j:j + nb].any()):
            j += 1
        s, e = i * 0.02, j * 0.02
        if t0 <= s <= t1 and min_s <= e - s <= max_s:
            out.append((round(s, 2), round(e, 2)))
        i = j
    return out


def read_wav16(path):
    w = wave.open(path)
    fs, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16 if sw == 2 else np.int32).reshape(-1, ch)
    x = x.mean(axis=1).astype(np.float32) / 2 ** (8 * sw - 1)
    if fs != FS:
        from math import gcd
        from scipy.signal import resample_poly
        g = gcd(FS, fs)
        x = resample_poly(x, FS // g, fs // g).astype(np.float32)   # anti-aliased (ESC-50 is 44.1 kHz)
    return x


def fit_len(x, n=WIN_N, at=None, rng=None):
    if len(x) >= n:
        i = (len(x) - n) // 2 if at is None else at
        return x[i:i + n]
    pad = n - len(x)
    a = pad // 2 if rng is None else int(rng.integers(0, pad + 1))
    return np.concatenate([np.zeros(a, np.float32), x, np.zeros(pad - a, np.float32)])


def speed(y, f):
    return np.interp(np.linspace(0, len(y) - 1, int(len(y) / f)), np.arange(len(y)), y).astype(np.float32)


def mix(sig, noise, snr_db):
    ps = np.mean(sig ** 2) + 1e-12
    pn = np.mean(noise ** 2) + 1e-12
    return sig + np.sqrt(ps / (pn * 10 ** (snr_db / 10))) * noise


def feat(w):
    return ok.logmel(w)[: ok.N_FRAMES]


# ------------------------------------------------------------------------------------------------- data

def build(a, rng):
    lab = json.load(open(a.labels))
    for p in a.extra_labels:           # mine_life.py fragments: calls_found and negative_spans of everyday recordings
        x = json.load(open(p))
        for key in ("calls_found", "negative_spans"):
            for nm, v in x.get(key, {}).items():
                if nm not in lab.get(key, {}) and nm not in lab.get("heldout_negative_spans", {}) \
                        and nm not in lab.get("call_spans", {}) and v:
                    lab.setdefault(key, {})[nm] = v
    mono = {os.path.basename(p)[:-4]: np.load(p) for p in glob.glob(os.path.join(a.mono16, "*.npy"))}

    def copies(nm, n):
        """(signal, repeats) for a recording: the ear mix the robot hears with n repeats, or with --mics also each
        microphone alone (to_mono16.py NAME@chK.npy), the n repeats split over the copies with at least half each."""
        mics = [mono[k] for k in sorted(mono) if k.startswith(nm + "@ch")] if a.mics else []
        if not mics:
            return [(mono[nm], n)]
        per = max(1, (n + 1) // 2)
        return [(mono[nm], per)] + [(m, per) for m in mics]

    # home floor noise: the quietest 1 s windows of the home recordings
    floor = []
    for nm in lab["home_files"]:
        y = mono[nm]
        lv = sorted((band_db(y[i:i + WIN_N]), i) for i in range(0, len(y) - WIN_N, WIN_N // 2))
        floor += [y[i:i + WIN_N] for _, i in lv[: max(10, len(lv) // 4)]]
    rng.shuffle(floor)

    # ---- mochi events
    train_ev, test_ev = [], []                      # (file, onset, end)
    spans_used = {}
    for nm, (t0, t1) in lab["call_spans"].items():
        ev = events(mono[nm], t0, t1)
        spans_used[nm] = ev
        k = len(ev) if a.final else int(round(len(ev) * (1 - HOLDOUT_FRAC)))
        train_ev += [(nm, s, e) for s, e in ev[:k]]
        test_ev += [(nm, s, e) for s, e in ev[k:]]
    for nm, ts in lab.get("calls_heldout", {}).items():
        (train_ev if a.final else test_ev).extend((nm, t, t + 0.6) for t in ts)   # --final: the deployed fit uses every home call

    X, Y = [], []
    pos_cues, neg_cues = {}, {}
    speaker_of = lab.get("speakers", {})                    # file -> who speaks in it (default: Shawn)

    def add(w, c):
        X.append(feat(fit_len(w)))
        Y.append(c)

    def cue(d, c, n=1):
        d[c] = d.get(c, 0) + n

    # Positives: the word alone, cut tight from its recording and laid onto a background from somewhere else (our
    # other recordings' call-free stretches, the home floor), so the only thing all positives share is the word.
    # 2026-10-30: windows taken whole from the one call session taught the model that session's background
    # (it fired every second between the calls as well).
    bg = list(floor)
    for nm, spans in lab.get("negative_spans", {}).items():
        y = mono[nm]
        for t0, t1 in spans:
            for i in range(int(t0 * FS), min(len(y), int(t1 * FS)) - WIN_N, WIN_N):
                bg.append(y[i:i + WIN_N])
    taper = np.hanning(int(0.04 * FS))
    for nm, s, e, y, per in ((nm, s, e, y, per) for nm, s, e in train_ev for y, per in copies(nm, a.pos_aug)):
        cue(pos_cues, "speaker:" + speaker_of.get(nm, "shawn"))
        word = y[max(0, int((s - 0.08) * FS)): int((e + 0.12) * FS)].copy()
        k = len(taper) // 2
        word[:k] *= taper[:k]
        word[-k:] *= taper[k:]
        for _ in range(per):
            wd = speed(word, rng.uniform(0.9, 1.1))[:WIN_N]
            b = bg[rng.integers(len(bg))].copy()
            b_rms = np.sqrt((b ** 2).mean()) + 1e-9
            w_rms = np.sqrt((wd ** 2).mean()) + 1e-9
            wd = wd * (b_rms / w_rms) * 10 ** (rng.uniform(3, 25) / 20)
            end = int(rng.uniform(0.35, 0.98) * WIN_N)                 # the word ends anywhere a scoring window holds it
            st = max(0, end - len(wd))
            b[st:st + len(wd)] += wd[: WIN_N - st]
            add(b * 10 ** (rng.uniform(-10, 10) / 20), 0)
    # calls marked by start time (the 10/29 RoboClub calls in a noisy room). --robo-fold 0/1 trains the odd/even calls
    # and holds out the others; --robo-train trains them all. Half of each call's windows keep its own noisy room
    # around it, half are laid onto other backgrounds; the room's loudspeaker babble without a call is a weighted
    # negative (--robo-neg-copies), so babble alone cannot be the cue (2026-10-30: without those negatives the own
    # background taught 'babble = mochi', 36 false wakes/h)
    # calls_found: calls located by template match and confirmed by ear (10/29 calls_201411, ears not yet repaired),
    # handled like word_starts
    wl = lab.get("word_len_s", 0.65)
    marked = dict(lab.get("word_starts", {}))
    marked.update(lab.get("calls_found", {}))
    for nm, starts in marked.items():
        if a.robo_fold in (0, 1):
            trained = [s for i, s in enumerate(starts) if i % 2 != a.robo_fold]
        else:
            trained = list(starts) if a.robo_train else []
        for s0, y, per in ((s0, y, per) for s0 in trained for y, per in copies(nm, a.pos_aug)):
            cue(pos_cues, "speaker:" + speaker_of.get(nm, "shawn"))
            cue(pos_cues, "room:" + nm)                           # half its windows keep its own room
            word = y[int(s0 * FS): int((s0 + wl) * FS)].copy()
            for j in range(per):
                if j % 2 == 0:
                    end = s0 + wl + rng.uniform(-0.6, 0.0)                # the word ends inside the window
                    w = y[int((end - ok.WINDOW_S) * FS): int(end * FS)]
                    w = fit_len(speed(w, rng.uniform(0.95, 1.05)))
                else:
                    wd = speed(word, rng.uniform(0.9, 1.1))[:WIN_N]
                    w = bg[rng.integers(len(bg))].copy()
                    wd = wd * (np.sqrt((w ** 2).mean()) + 1e-9) / (np.sqrt((wd ** 2).mean()) + 1e-9) * 10 ** (rng.uniform(3, 20) / 20)
                    e_i = int(rng.uniform(0.6, 0.98) * WIN_N)
                    st = max(0, e_i - len(wd))
                    w[st:st + len(wd)] += wd[: WIN_N - st]
                add(w * 10 ** (rng.uniform(-10, 10) / 20), 0)
        test_ev += [(nm, s0, s0 + wl) for s0 in starts if s0 not in trained]
    # synthetic "Mochi" in many voices (mochi_set.py, macOS voices, en and zh accents): the word without Shawn's voice
    # or our rooms, laid onto our backgrounds, so the shared cue of all positives is the word (openWakeWord recipe)
    if a.tts_pos and a.set and os.path.isdir(a.set):
        for r in json.load(open(os.path.join(a.set, "manifest.json"))):
            if r["kind"] not in ("pos", "pos_zh"):
                continue
            cue(pos_cues, "voice:" + r["voice"])
            x = read_wav16(os.path.join(a.set, r["file"]))
            e_s = r.get("speech_end") or len(x) / FS
            word = x[max(0, int((e_s - 0.75) * FS)): int((e_s + 0.05) * FS)]
            for _ in range(a.tts_pos):
                wd = speed(word, rng.uniform(0.9, 1.1))[:WIN_N]
                w = bg[rng.integers(len(bg))].copy()
                wd = wd * (np.sqrt((w ** 2).mean()) + 1e-9) / (np.sqrt((wd ** 2).mean()) + 1e-9) * 10 ** (rng.uniform(3, 25) / 20)
                e_i = int(rng.uniform(0.35, 0.98) * WIN_N)
                st = max(0, e_i - len(wd))
                w[st:st + len(wd)] += wd[: WIN_N - st]
                add(w * 10 ** (rng.uniform(-10, 10) / 20), 0)
    # real people saying "mochi" in YouTube videos (~/data/mochi_web, files VIDEOID_NNN*.wav): the lab recipe of
    # 18-763 lecture 21 (Speech Commands "on"/"off" from thousands of speakers, no own recording) needs many voices per
    # word, so the word is the only thing all positives share. pos_ctx = the word in its own 1.5 s of audio (cropped
    # to 1 s around it), pos = the word alone, laid onto our robot backgrounds so the duck's microphones are covered;
    # the rest of the same sentence (neg_adjacent) and of the same video (neg) are negatives. Videos whose id hashes to
    # 0 mod 10 are held out (web_test).
    web_test = []
    if a.web and os.path.isdir(a.web):
        import zlib
        held = lambda f: zlib.crc32(os.path.basename(f)[:11].encode()) % 10 == 0
        for p in sorted(glob.glob(os.path.join(a.web, "pos_ctx", "*.wav"))):
            if held(p):
                web_test.append(p)
                continue
            cue(pos_cues, "web:" + os.path.basename(p)[:11])
            x = read_wav16(p)
            for _ in range(a.web_aug):
                i0 = int(rng.uniform(0.1, 0.45) * FS)
                add(fit_len(speed(x, rng.uniform(0.95, 1.05))[i0:i0 + WIN_N]) * 10 ** (rng.uniform(-10, 10) / 20), 0)
        for p in sorted(glob.glob(os.path.join(a.web, "pos", "*.wav"))):
            if held(p):
                continue
            word = read_wav16(p)
            for _ in range(a.web_aug):
                wd = speed(word, rng.uniform(0.9, 1.1))[:WIN_N]
                w = bg[rng.integers(len(bg))].copy()
                wd = wd * (np.sqrt((w ** 2).mean()) + 1e-9) / (np.sqrt((wd ** 2).mean()) + 1e-9) * 10 ** (rng.uniform(3, 25) / 20)
                e_i = int(rng.uniform(0.6, 0.98) * WIN_N)
                st = max(0, e_i - len(wd))
                w[st:st + len(wd)] += wd[: WIN_N - st]
                add(w * 10 ** (rng.uniform(-10, 10) / 20), 0)
    n_pos = len(Y)
    if a.web and os.path.isdir(a.web):
        for sub in ("neg_adjacent", "neg"):
            for p in sorted(glob.glob(os.path.join(a.web, sub, "*.wav"))):
                if held(p):
                    web_test.append(p)
                    continue
                cue(neg_cues, "web:" + os.path.basename(p)[:11])
                add(fit_len(read_wav16(p)) * 10 ** (rng.uniform(-10, 10) / 20), 1)

    # ---- speech: Speech Commands words in home noise
    sc = a.speech_commands
    words = sorted(d for d in os.listdir(sc) if os.path.isdir(os.path.join(sc, d)) and not d.startswith("_"))
    per = max(1, a.sc_words // len(words))
    for wd in words:
        fs = sorted(glob.glob(os.path.join(sc, wd, "*.wav")))
        for p in rng.choice(fs, min(per, len(fs)), replace=False):
            x = fit_len(read_wav16(p), rng=rng)
            if floor:
                x = mix(x, floor[rng.integers(len(floor))], rng.uniform(5, 25))
            add(x * 10 ** (rng.uniform(-30, -5) / 20), 1)
    # lab conversation without the name, the duck's quacks, synthetic near-miss words
    for nm in lab["no_call_files"]:
        y = mono[nm]
        for i in range(0, len(y) - WIN_N, WIN_N // 4):
            add(y[i:i + WIN_N], 1)
    for p in sorted(glob.glob(os.path.join(a.sounds, "*.wav"))):
        x = read_wav16(p)
        for _ in range(4):
            w = fit_len(x, rng=rng)
            if floor:
                w = mix(w, floor[rng.integers(len(floor))], rng.uniform(5, 25))
            add(w * 10 ** (rng.uniform(-30, -5) / 20), 1)
    if a.set and os.path.isdir(a.set):
        for r in json.load(open(os.path.join(a.set, "manifest.json"))):
            if r["kind"] == "neg_word":
                cue(neg_cues, "voice:" + r["voice"])
                x = read_wav16(os.path.join(a.set, r["file"]))[int(r["speech_start"] * FS) - 1600: int(r["speech_end"] * FS) + 1600]
                for _ in range(2):
                    w = fit_len(x, rng=rng)
                    if floor:
                        w = mix(w, floor[rng.integers(len(floor))], rng.uniform(5, 25))
                    add(w * 10 ** (rng.uniform(-30, -5) / 20), 1)
    # every stretch of our own recordings that holds no call (speech, footsteps, standing up, quacks, quiet):
    # 1 s windows every 0.25 s, twice with gain jitter (2026-10-30: walking and standing up woke the spotter)
    for nm, spans in lab.get("negative_spans", {}).items():
        cue(neg_cues, "room:" + nm)
        for s in lab.get("speech_negatives", {}).get(nm, []):
            cue(neg_cues, "speaker:" + s)
        reps = a.robo_neg_copies if nm in marked else 2
        for y, per in copies(nm, reps):
            for t0, t1 in spans:
                i1 = min(len(y), int(t1 * FS))
                for i in range(int(t0 * FS), i1 - WIN_N, WIN_N // 4):
                    for _ in range(per):
                        add(y[i:i + WIN_N] * 10 ** (rng.uniform(-8, 8) / 20), 1)
    # the gaps between the calls of a call recording: same speaker, same room, same moment, only the word missing
    # (Shawn 2026-10-30: in one utterance only the name is positive, everything around it is negative). 1 s windows
    # every 0.25 s that keep 0.15 s clear of every voiced event of the span.
    for nm, (t0, t1) in lab.get("call_spans", {}).items():
        busy = [(s - 0.15, e + 0.15) for s, e in spans_used[nm]]
        cue(neg_cues, "room:" + nm)
        for y, per in copies(nm, 2):
            for i in range(int(t0 * FS), min(len(y), int(t1 * FS)) - WIN_N, WIN_N // 4):
                w0, w1 = i / FS, i / FS + ok.WINDOW_S
                if all(w1 <= b0 or w0 >= b1 for b0, b1 in busy):
                    for _ in range(per):
                        add(y[i:i + WIN_N] * 10 ** (rng.uniform(-8, 8) / 20), 1)
    # synthetic everyday speech in the same voices as the synthetic Mochi positives (tts_speech.py), laid onto our
    # backgrounds like them: a synthetic voice alone is not the cue (2026-10-30: positives without these negatives
    # gave over 2000 false wakes per hour on synthetic speech)
    if a.tts_speech and os.path.isdir(a.tts_speech):
        for r in json.load(open(os.path.join(a.tts_speech, "manifest.json"))):
            cue(neg_cues, "voice:" + r["voice"])
            x = read_wav16(os.path.join(a.tts_speech, r["file"]))
            for i in range(0, len(x) - WIN_N, WIN_N // 2):
                w = bg[rng.integers(len(bg))].copy()
                s = x[i:i + WIN_N]
                s = s * (np.sqrt((w ** 2).mean()) + 1e-9) / (np.sqrt((s ** 2).mean()) + 1e-9) * 10 ** (rng.uniform(0, 25) / 20)
                add((w + s) * 10 ** (rng.uniform(-10, 10) / 20), 1)
    n_speech = len(Y) - n_pos
    missing = unmatched_cues(pos_cues, neg_cues)
    if missing and not a.allow_unmatched:
        raise SystemExit(f"positives carry cues no negative carries: {missing[:8]}{' ...' if len(missing) > 8 else ''} "
                         f"({len(missing)}). Add negatives with the same voice / speaker / room (e.g. --tts-speech for "
                         f"synthetic voices) or pass --allow-unmatched for a study run.")

    # ---- noise: robot-recording stretches away from any voice, background noise files
    for nm in lab["home_files"] + lab["no_call_files"]:
        y = mono[nm]
        lv = np.array([band_db(y[i:i + WIN_N]) for i in range(0, len(y) - WIN_N, WIN_N // 2)])
        cut = np.percentile(lv, 50)
        for j, v in enumerate(lv):
            if v <= cut:
                add(y[j * (WIN_N // 2): j * (WIN_N // 2) + WIN_N], 2)
    for p in glob.glob(os.path.join(sc, "_background_noise_", "*.wav")):
        x = read_wav16(p)
        for i in range(0, len(x) - WIN_N, WIN_N):
            add(x[i:i + WIN_N] * 10 ** (rng.uniform(-40, -10) / 20), 2)
    if a.esc50 and os.path.isdir(a.esc50):
        for p in sorted(glob.glob(os.path.join(a.esc50, "*.wav"))):
            x = read_wav16(p)
            for i in range(0, max(1, len(x) - WIN_N + 1), WIN_N):
                w = fit_len(x[i:i + WIN_N])
                if np.abs(w).max() < 1e-4:
                    continue
                w = w / (np.sqrt((w ** 2).mean()) + 1e-9) * 10 ** (rng.uniform(-45, -20) / 20)
                if floor:
                    w = w + floor[rng.integers(len(floor))]
                add(w, 2)
    n_noise = len(Y) - n_pos - n_speech
    info = dict(train_events=len(train_ev), test_events=len(test_ev), rows=dict(mochi=n_pos, speech=n_speech, noise=n_noise),
                unmatched_cues=missing, web_test=web_test,
                spans=spans_used, test=[(n, s) for n, s, _ in test_ev])
    return np.stack(X).astype(np.float32), np.array(Y), mono, train_ev, test_ev, lab, info


# ------------------------------------------------------------------------------------------------- model

def train_torch(X, Y, a, seed):
    import torch
    import torch.nn as nn
    torch.set_num_threads(a.threads)   # 2026-10-30: default threading on a loaded MacBook stretched a 7 min run past 45 min
    torch.manual_seed(seed)
    mu = X.reshape(-1, ok.N_MELS).mean(axis=0)
    sd = X.reshape(-1, ok.N_MELS).std(axis=0) + 1e-3
    Xn = torch.tensor(((X - mu) / sd).astype(np.float32))
    Yt = torch.tensor(Y, dtype=torch.long)
    ch, ks, pools = (24, 32, 48), (5, 5, 7), (2, 2, 1)

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            layers, c_in = [], ok.N_MELS
            for c, k, p in zip(ch, ks, pools):
                layers += [nn.Conv1d(c_in, c, k, padding=k // 2), nn.BatchNorm1d(c), nn.ReLU()]
                if p > 1:
                    layers.append(nn.MaxPool1d(p))
                c_in = c
            self.body = nn.Sequential(*layers)
            self.drop = nn.Dropout(0.3)
            self.head = nn.Linear(c_in, len(CLASSES))

        def forward(self, x):                      # x (B, T, M)
            h = self.body(x.transpose(1, 2))
            return self.head(self.drop(h.max(dim=2).values))

    net = Net()
    w = torch.tensor([1.0 / max(1, (Y == c).sum()) for c in range(len(CLASSES))])
    w = (w / w.sum() * len(CLASSES)).float()
    lossf = nn.CrossEntropyLoss(weight=w)
    opt = torch.optim.AdamW(net.parameters(), lr=2e-3, weight_decay=1e-3)
    n = len(Yt)
    # 2026-10-30: a constant 2e-3 and the last epoch's weights gave seeds of one recipe 7/20 to 16/20 held-out calls;
    # cosine decay to zero and an exponential moving average of the weights (exported) settle them
    steps = a.epochs * ((n + 127) // 128)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=2e-3, total_steps=max(1, steps), pct_start=0.1)
    ema = torch.optim.swa_utils.AveragedModel(net, multi_avg_fn=torch.optim.swa_utils.get_ema_multi_avg_fn(0.998),
                                              use_buffers=True)
    for ep in range(a.epochs):
        net.train()
        perm = torch.randperm(n)
        tot = 0.0
        for i in range(0, n, 128):
            idx = perm[i:i + 128]
            xb = Xn[idx]
            # SpecAugment-style masks: a band and a time stretch
            if True:
                m0 = np.random.randint(0, ok.N_MELS - 6)
                xb = xb.clone()
                xb[:, :, m0:m0 + np.random.randint(0, 6)] = 0
                t0 = np.random.randint(0, ok.N_FRAMES - 10)
                xb[:, t0:t0 + np.random.randint(0, 10), :] = 0
            opt.zero_grad()
            loss = lossf(net(xb), Yt[idx])
            loss.backward()
            opt.step()
            sched.step()
            ema.update_parameters(net)
            tot += float(loss.detach()) * len(idx)
        if ep % 5 == 4 or ep == a.epochs - 1:
            print(f"  epoch {ep + 1}: loss {tot / n:.4f}", flush=True)
    net = ema.module
    net.eval()
    d = dict(mu=mu.astype(np.float32), sd=sd.astype(np.float32), classes=np.array(CLASSES))
    convs = [m for m in net.body if isinstance(m, nn.Conv1d)]
    bns = [m for m in net.body if isinstance(m, nn.BatchNorm1d)]
    for i, (c, bn, p) in enumerate(zip(convs, bns, pools)):
        # batch norm folded into the conv, so ownkws.OwnModel runs unchanged: w * g / s, (b - mean) * g / s + beta
        g = (bn.weight / torch.sqrt(bn.running_var + bn.eps)).detach()
        wt = (c.weight.detach() * g[:, None, None]).numpy()
        bt = ((c.bias.detach() - bn.running_mean) * g + bn.bias.detach()).numpy()
        d[f"conv{i}_w"] = wt.transpose(2, 1, 0).astype(np.float32)   # (k, c_in, c_out)
        d[f"conv{i}_b"] = bt.astype(np.float32)
        d[f"pool{i}"] = np.int32(p)
    global LAST_TORCH_PROBS          # for the export test: the trained network's own probabilities

    def LAST_TORCH_PROBS(F):
        with torch.no_grad():
            x = torch.tensor(((np.asarray(F, np.float32).reshape(-1, ok.N_FRAMES, ok.N_MELS) - mu) / sd).astype(np.float32))
            return torch.softmax(net(x), dim=1).numpy()
    d["dense_w"] = net.head.weight.detach().numpy().T.astype(np.float32)
    d["dense_b"] = net.head.bias.detach().numpy().astype(np.float32)
    return d


# ------------------------------------------------------------------------------------------------- evaluation

def scores(model, y, step_s=0.1):
    idx = list(range(WIN_N, len(y), int(step_s * FS)))
    if not idx:
        return np.array([]), np.array([])
    out = []
    for k in range(0, len(idx), 256):
        F = np.stack([feat(y[i - WIN_N:i]) for i in idx[k:k + 256]])
        out.append(np.atleast_1d(model.score(F)))
    return np.array(idx) / FS, np.concatenate(out)


def hits(ts, ps, thr):
    out, last = [], -1e9
    for t, p in zip(ts, ps):
        if p >= thr and t - last >= ok.REFRACTORY_S:
            out.append(t)
            last = t
    return out


def evaluate(model, mono, test_ev, lab, a):
    thresholds = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.98]
    by_file = {}
    for nm, s, e in test_ev:
        by_file.setdefault(nm, []).append(s)
    cache = {}
    for nm in set(by_file) | set(lab.get("scan_files", [])):
        cache[nm] = scores(model, mono[nm])
    speech = []
    if a.set and os.path.isdir(a.set):
        for r in json.load(open(os.path.join(a.set, "manifest.json"))):
            if r["kind"] == "speech":
                speech.append(read_wav16(os.path.join(a.set, r["file"])) * 10 ** (-12 / 20))
    floor_src = mono[lab["home_files"][0]]
    sp_scores = []
    sp_hours = 0.0
    for x in speech:
        nz = np.resize(floor_src, len(x))
        sp_scores.append(scores(model, mix(x, nz, 15.0)))
        sp_hours += len(x) / FS / 3600
    res = {}
    for thr in thresholds:
        rec, n, other = 0, 0, 0
        for nm, ons in by_file.items():
            ts, ps = cache[nm]
            hs = hits(ts, ps, thr)
            for o in ons:
                n += 1
                rec += any(0.2 <= h - o <= 1.6 for h in hs)
            # hits not near any utterance of the file's call span count as "other"
        fa = sum(len(hits(ts, ps, thr)) for ts, ps in sp_scores)
        per = {}
        for nm, ons in by_file.items():
            ts, ps = cache[nm]
            hs = hits(ts, ps, thr)
            per[nm] = f"{sum(any(0.2 <= h - o <= 1.6 for h in hs) for o in ons)}/{len(ons)}"
        res[str(thr)] = dict(recall=f"{rec}/{n}", per_file=per, recall_frac=round(rec / max(1, n), 3), fa_speech=fa,
                             fa_per_h=round(fa / sp_hours, 1) if sp_hours else None)
    scan = {}
    for nm in lab.get("scan_files", []):
        ts, ps = cache[nm]
        scan[nm] = {str(t): [round(h, 1) for h in hits(ts, ps, t)] for t in (0.8, 0.9)}
    neg = {}
    for nm, spans in lab.get("heldout_negative_spans", {}).items():
        ts, ps = scores(model, mono[nm])
        for t0, t1 in spans:
            sel = (ts >= t0 + ok.WINDOW_S) & (ts <= t1)
            neg[f"{nm} {t0}-{t1}"] = (ts[sel], ps[sel])
    neg_s = sum(t1 - t0 for spans in lab.get("heldout_negative_spans", {}).values() for t0, t1 in spans)
    for thr in thresholds:
        res[str(thr)]["heldout_real_false"] = {k: [round(h, 1) for h in hits(ts, ps, thr)] for k, (ts, ps) in neg.items()}
        res[str(thr)]["heldout_real_false_n"] = sum(len(v) for v in res[str(thr)]["heldout_real_false"].values())
    return res, dict(speech_hours=round(sp_hours, 3), heldout_real_negative_s=round(neg_s, 1)), scan


def web_heldout(model, files, thr):
    """Held-out web videos: share of pos_ctx clips the model wakes on (best of three crops round the word) and share
    of the same videos' negative clips it wakes on, per threshold."""
    pos, neg = [], []
    for p in files:
        x = read_wav16(p)
        if "/pos_ctx/" in p:
            pos.append(max(model.probs(fit_len(x[int(o * FS):int(o * FS) + WIN_N]))[0] for o in (0.1, 0.25, 0.45)))
        else:
            neg.append(model.probs(fit_len(x))[0])
    pos, neg = np.array(pos), np.array(neg)
    return {str(t): dict(recall=f"{int((pos >= t).sum())}/{len(pos)}", false=f"{int((neg >= t).sum())}/{len(neg)}") for t in thr}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default=None, help="~/data/mochi_web: real people saying mochi in YouTube videos (pos, pos_ctx, neg, neg_adjacent)")
    ap.add_argument("--web-aug", type=int, default=3, help="augmented windows per web positive clip")
    ap.add_argument("--mono16", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--speech-commands", required=True)
    ap.add_argument("--set", default=None)
    ap.add_argument("--esc50", default=None, help="ESC-50 audio folder (environmental sounds, noise class)")
    ap.add_argument("--robo-train", action="store_true", help="train on the RoboClub calls (else all are held out)")
    ap.add_argument("--robo-fold", type=int, default=-1, help="0/1: train the odd/even RoboClub calls, hold out the rest")
    ap.add_argument("--robo-neg-copies", type=int, default=2, help="copies of each call-free window of a RoboClub call file")
    ap.add_argument("--tts-pos", type=int, default=0, help="augmented windows per synthetic Mochi clip (0: none)")
    ap.add_argument("--tts-speech", default=None, help="folder of synthetic everyday speech (tts_speech.py), speech class")
    ap.add_argument("--allow-unmatched", action="store_true", help="train although positives carry cues no negative has")
    ap.add_argument("--extra-labels", action="append", default=[], help="mine_life.py output to merge (repeatable)")
    ap.add_argument("--mics", action="store_true", help="also train on each microphone alone (NAME@chK.npy from to_mono16.py)")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--final", action="store_true", help="train on every home call (recipe chosen on the held-out run); real negatives stay held out")
    ap.add_argument("--sounds", default=os.path.join(MAC, "sounds"))
    ap.add_argument("--out", default=os.path.join(HERE, "models", "mochi_own.npz"))
    ap.add_argument("--report", default=os.path.join(HERE, "results", "mochi_own.json"))
    ap.add_argument("--fa-per-h", type=float, default=1.0)
    ap.add_argument("--sc-words", type=int, default=6000)
    ap.add_argument("--pos-aug", type=int, default=40)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    np.random.seed(a.seed)
    t0 = time.time()
    X, Y, mono, train_ev, test_ev, lab, info = build(a, rng)
    print(f"data: {info['rows']} rows; {info['train_events']} training calls, {info['test_events']} held out; "
          f"{time.time() - t0:.0f} s", flush=True)
    d = train_torch(X, Y, a, a.seed)
    tmp = a.out + ".tmp.npz"
    d["threshold"] = np.float32(0.9)
    np.savez(tmp, **d)
    model = ok.OwnModel(tmp)
    res, extra, scan = evaluate(model, mono, test_ev, lab, a)
    if info["web_test"]:
        extra["web_heldout"] = web_heldout(model, info["web_test"], [0.5, 0.7, 0.9])
        print(f"  web held-out videos: {extra['web_heldout']}")
    info["web_test"] = len(info["web_test"])
    chosen = next((float(t) for t, r in res.items() if r["fa_per_h"] is not None and r["fa_per_h"] <= a.fa_per_h
                   and r.get("heldout_real_false_n", 0) == 0), 0.98)
    d["threshold"] = np.float32(chosen)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    np.savez(a.out, **d)
    os.remove(tmp)
    rep = dict(made=time.strftime("%Y-%m-%d %H:%M"), classes=CLASSES, data=info, heldout=res, threshold=chosen,
               fa_budget_per_h=a.fa_per_h, model_bytes=os.path.getsize(a.out), scan=scan, wall_s=round(time.time() - t0, 1), **extra)
    os.makedirs(os.path.dirname(a.report), exist_ok=True)
    json.dump(rep, open(a.report, "w"), indent=1)
    for t, r in res.items():
        print(f"  thr {t}: held-out calls {r['recall']} {r['per_file']}, false wakes on {extra['speech_hours'] * 60:.0f} min speech: "
              f"{r['fa_speech']} ({r['fa_per_h']}/h); held-out real room sounds ({extra['heldout_real_negative_s']} s): "
              f"{r['heldout_real_false_n']} {r['heldout_real_false']}")
    print(f"threshold {chosen}; model {a.out} ({rep['model_bytes']} B); {rep['wall_s']} s")
    for nm, s in scan.items():
        print(f"  scan {nm}: {s}")


if __name__ == "__main__":
    main()
