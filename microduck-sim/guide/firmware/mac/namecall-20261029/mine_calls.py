"""Find Mochi calls in duck recordings without anyone labelling them: template matching on log-mel against calls
already known from other recordings (how the eight calls of calls_201411 were found on 10/29), so new recordings
can feed the spotter's training without Shawn marking anything.

A template is the 0.6 s log-mel (ownkws.logmel, per-band mean removed) starting at a known call. A file is scanned
every 10 ms; the score at t is the best normalised correlation of any template from ANOTHER file with the 0.6 s
starting at t, then z-scored against that file's own scores. Peaks above --z, at least --gap s apart, are candidates.

  python3 mine_calls.py --mono16 DIR [--files a,b] [--z 4] [--check]

--check: for every file with known calls, scan it with templates from the other files only and report how many of
its known calls are found (within 0.5 s) and how many other peaks fire: the acceptance of the method itself.
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import ownkws as ok  # noqa: E402
import train_mochi as tm  # noqa: E402

FS = 16000
T_LEN = 0.6
HOP = ok.HOP / FS                              # 10 ms per log-mel frame


def known_calls(lab, mono):
    """file -> call start times (s) from the labels file."""
    out = {}
    for nm, (t0, t1) in lab.get("call_spans", {}).items():
        out[nm] = [s for s, _ in tm.events(mono[nm], t0, t1)]
    for key in ("calls_heldout", "word_starts", "calls_found"):
        for nm, ts in lab.get(key, {}).items():
            out.setdefault(nm, []).extend(ts)
    return {k: sorted(v) for k, v in out.items()}


def feats(y):
    lm = ok.logmel(y)
    return (lm - lm.mean(axis=0)) / (lm.std(axis=0) + 1e-6)


def templates(mono, calls, exclude=()):
    n = int(T_LEN / HOP)
    out = []
    for nm, ts in calls.items():
        if nm in exclude:
            continue
        f = feats(mono[nm])
        for t in ts:
            i = int(round(t / HOP))
            if 0 <= i and i + n <= len(f):
                w = f[i:i + n] - f[i:i + n].mean()
                out.append(w / (np.linalg.norm(w) + 1e-9))
    return np.stack(out)


def scan(y, tpl):
    f = feats(y)
    n = tpl.shape[1]
    idx = np.arange(n)[None, :] + np.arange(len(f) - n)[:, None]
    win = f[idx]                                               # (T, n, mels)
    win = win - win.mean(axis=(1, 2), keepdims=True)
    win = win / (np.linalg.norm(win.reshape(len(win), -1), axis=1)[:, None, None] + 1e-9)
    s = np.einsum("tnm,knm->tk", win, tpl, optimize=True).max(axis=1)
    z = (s - np.median(s)) / (1.4826 * np.median(np.abs(s - np.median(s))) + 1e-9)
    return np.arange(len(s)) * HOP, z


def peaks(ts, z, thr, gap):
    out = []
    for i in np.argsort(-z):
        if z[i] < thr:
            break
        if all(abs(ts[i] - p) >= gap for p, _ in out):
            out.append((float(ts[i]), float(z[i])))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mono16", required=True)
    ap.add_argument("--labels", default=os.path.join(HERE, "mochi_labels.json"))
    ap.add_argument("--files", default="")
    ap.add_argument("--z", type=float, default=4.0)
    ap.add_argument("--gap", type=float, default=1.5)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    lab = json.load(open(a.labels))
    mono = {os.path.basename(p)[:-4]: np.load(os.path.join(a.mono16, p)) for p in os.listdir(a.mono16)
            if p.endswith(".npy") and "@" not in p}
    calls = known_calls(lab, mono)
    if a.check:
        for nm, ts in calls.items():
            tt, z = scan(mono[nm], templates(mono, calls, exclude=(nm,)))
            for thr in (3.0, 4.0, 5.0, 6.0):
                pk = peaks(tt, z, thr, a.gap)
                found = sum(any(abs(p - t) <= 0.5 for p, _ in pk) for t in ts)
                other = sum(not any(abs(p - t) <= 0.5 for t in ts) for p, _ in pk)
                print(f"{nm}: z {thr}: {found}/{len(ts)} known calls found, {other} other peaks")
        return
    tpl = templates(mono, calls)
    for nm in (a.files.split(",") if a.files else sorted(mono)):
        tt, z = scan(mono[nm], tpl)
        pk = peaks(tt, z, a.z, a.gap)
        print(f"{nm}: {len(pk)} candidates at z >= {a.z}: {[(round(p, 2), round(v, 1)) for p, v in pk]}")


if __name__ == "__main__":
    main()
