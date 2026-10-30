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
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * FS / fs)), np.arange(len(x)), x).astype(np.float32)
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
    mono = {os.path.basename(p)[:-4]: np.load(p) for p in glob.glob(os.path.join(a.mono16, "*.npy"))}

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
        k = int(round(len(ev) * (1 - HOLDOUT_FRAC)))
        train_ev += [(nm, s, e) for s, e in ev[:k]]
        test_ev += [(nm, s, e) for s, e in ev[k:]]
    for nm, ts in lab.get("calls_heldout", {}).items():
        test_ev += [(nm, t, t + 0.6) for t in ts]

    X, Y = [], []

    def add(w, c):
        X.append(feat(fit_len(w)))
        Y.append(c)

    for nm, s, e in train_ev:
        y = mono[nm]
        for _ in range(a.pos_aug):
            st = s - rng.uniform(0.05, 0.45)                       # word anywhere a scoring window holds it
            seg = y[max(0, int((st - 0.3) * FS)): int((st + ok.WINDOW_S + 0.3) * FS)]
            f = rng.uniform(0.9, 1.1)
            seg = speed(seg, f)
            i0 = int(0.3 * FS / f)
            w = fit_len(seg[i0:i0 + WIN_N])
            if rng.random() < 0.7 and floor:
                w = mix(w, floor[rng.integers(len(floor))], rng.uniform(3, 20))
            add(w * 10 ** (rng.uniform(-10, 10) / 20), 0)
    n_pos = len(Y)

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
                x = read_wav16(os.path.join(a.set, r["file"]))[int(r["speech_start"] * FS) - 1600: int(r["speech_end"] * FS) + 1600]
                for _ in range(2):
                    w = fit_len(x, rng=rng)
                    if floor:
                        w = mix(w, floor[rng.integers(len(floor))], rng.uniform(5, 25))
                    add(w * 10 ** (rng.uniform(-30, -5) / 20), 1)
    n_speech = len(Y) - n_pos

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
    n_noise = len(Y) - n_pos - n_speech
    info = dict(train_events=len(train_ev), test_events=len(test_ev), rows=dict(mochi=n_pos, speech=n_speech, noise=n_noise),
                spans=spans_used, test=[(n, s) for n, s, _ in test_ev])
    return np.stack(X).astype(np.float32), np.array(Y), mono, train_ev, test_ev, lab, info


# ------------------------------------------------------------------------------------------------- model

def train_torch(X, Y, a, seed):
    import torch
    import torch.nn as nn
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
                layers += [nn.Conv1d(c_in, c, k, padding=k // 2), nn.ReLU()]
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
            tot += float(loss.detach()) * len(idx)
        if ep % 5 == 4 or ep == a.epochs - 1:
            print(f"  epoch {ep + 1}: loss {tot / n:.4f}", flush=True)
    net.eval()
    d = dict(mu=mu.astype(np.float32), sd=sd.astype(np.float32), classes=np.array(CLASSES))
    convs = [m for m in net.body if isinstance(m, nn.Conv1d)]
    for i, (c, p) in enumerate(zip(convs, pools)):
        d[f"conv{i}_w"] = c.weight.detach().numpy().transpose(2, 1, 0).astype(np.float32)   # (k, c_in, c_out)
        d[f"conv{i}_b"] = c.bias.detach().numpy().astype(np.float32)
        d[f"pool{i}"] = np.int32(p)
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
    return res, dict(speech_hours=round(sp_hours, 3)), scan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mono16", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--speech-commands", required=True)
    ap.add_argument("--set", default=None)
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
    chosen = next((float(t) for t, r in res.items() if r["fa_per_h"] is not None and r["fa_per_h"] <= a.fa_per_h), 0.98)
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
              f"{r['fa_speech']} ({r['fa_per_h']}/h)")
    print(f"threshold {chosen}; model {a.out} ({rep['model_bytes']} B); {rep['wall_s']} s")
    for nm, s in scan.items():
        print(f"  scan {nm}: {s}")


if __name__ == "__main__":
    main()
