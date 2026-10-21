"""Train and test the stroke / relaxed-pat / angry-pat classifier from labelled recordings (draft, 2026-10-21).

    python3 train_touch.py touch_<session>.jsonl [...] [--brain-log duck_wired_log_<suffix>.jsonl] [--holdout 0.33]
                           [--model touch_lr.json]

Episodes come from the label rows in the recordings (record_touch.py); features from features.py. Multinomial
logistic regression (numpy, L2) on standardised features; the hold-out is the LAST third of every class (later
repetitions, so the test is not a shuffle of the same minute). Prints held-out accuracy, the confusion matrix and the
pat-vs-angry confusion; writes the model (weights, mean, std, class names) as JSON for the runtime.
Acceptance (findings-touch.md): held-out accuracy >= 0.85 over the three touch classes, pat_relaxed <-> pat_angry
confusion <= 0.15 each way, and zero touch events in the no-touch recording. Trains in seconds on the Mac.
"""
import argparse
import json
import sys
import numpy as np
from features import FEATURE_NAMES, episode_features

CLASSES = ['stroke', 'pat_relaxed', 'pat_angry']


def load(paths, brain_log=None):
    rows, labels = [], []
    for p in paths:
        for ln in open(p):
            r = json.loads(ln)
            (labels if 'label' in r else rows).append(r)
    rows.sort(key=lambda r: r['t'])
    imu = []
    if brain_log:
        imu = [json.loads(ln) for ln in open(brain_log)]
    eps = []
    starts = {}
    for lb in sorted(labels, key=lambda r: r['t']):
        if lb['event'] == 'start':
            starts[lb['label']] = lb['t']
        elif lb['label'] in starts:
            t0, t1 = starts.pop(lb['label']), lb['t']
            pad = [r for r in rows if t0 <= r['t'] <= t1]
            rest = [r for r in rows if t0 - 2.0 <= r['t'] < t0]
            im = [r for r in imu if t0 - 0.1 <= r['t'] <= t1 + 0.3]
            if len(pad) >= 5 and len(rest) >= 20:
                eps.append((lb['label'], episode_features(pad, rest, im)))
    return eps


def fit(X, y, n_cls, l2=1e-2, steps=3000, lr=0.1):
    W = np.zeros((X.shape[1] + 1, n_cls))
    Xb = np.hstack([X, np.ones((len(X), 1))])
    Y = np.eye(n_cls)[y]
    for _ in range(steps):
        P = np.exp(Xb @ W - (Xb @ W).max(1, keepdims=True))
        P /= P.sum(1, keepdims=True)
        W -= lr * (Xb.T @ (P - Y) / len(X) + l2 * np.vstack([W[:-1], np.zeros((1, n_cls))]))
    return W


def predict(W, X):
    return (np.hstack([X, np.ones((len(X), 1))]) @ W).argmax(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('recordings', nargs='+')
    ap.add_argument('--brain-log')
    ap.add_argument('--holdout', type=float, default=0.33)
    ap.add_argument('--model', default='touch_lr.json')
    a = ap.parse_args()
    eps = load(a.recordings, a.brain_log)
    none_eps = [f for lb, f in eps if lb == 'none']
    eps = [(lb, f) for lb, f in eps if lb in CLASSES]
    if not eps:
        sys.exit('no labelled episodes of ' + ', '.join(CLASSES))
    tr, te = [], []
    for c in CLASSES:
        cs = [(lb, f) for lb, f in eps if lb == c]
        k = int(round(len(cs) * (1 - a.holdout)))
        tr += cs[:k]; te += cs[k:]
    X = np.array([[f[n] for n in FEATURE_NAMES] for _, f in tr]); y = np.array([CLASSES.index(lb) for lb, _ in tr])
    mu, sd = X.mean(0), X.std(0) + 1e-6
    W = fit((X - mu) / sd, y, len(CLASSES))
    Xt = np.array([[f[n] for n in FEATURE_NAMES] for _, f in te]); yt = np.array([CLASSES.index(lb) for lb, _ in te])
    pr = predict(W, (Xt - mu) / sd)
    conf = np.zeros((len(CLASSES), len(CLASSES)), int)
    for t, p in zip(yt, pr):
        conf[t, p] += 1
    acc = (pr == yt).mean() if len(yt) else float('nan')
    print(f'train {len(tr)} held-out {len(te)}: accuracy {acc:.3f}')
    for i, c in enumerate(CLASSES):
        print(f'  true {c:12s} -> ' + ' '.join(f'{CLASSES[j]}={conf[i, j]}' for j in range(len(CLASSES))))
    pr_, pa_ = CLASSES.index('pat_relaxed'), CLASSES.index('pat_angry')
    n_r, n_a = conf[pr_].sum(), conf[pa_].sum()
    print(f'pat confusion: relaxed->angry {conf[pr_, pa_] / max(1, n_r):.2f}, angry->relaxed {conf[pa_, pr_] / max(1, n_a):.2f}')
    print(f'no-touch episodes: {len(none_eps)} (the runtime gate is the pad threshold, not this model)')
    json.dump({'classes': CLASSES, 'features': FEATURE_NAMES, 'W': W.tolist(), 'mean': mu.tolist(), 'std': sd.tolist(),
               'holdout_accuracy': acc, 'confusion': conf.tolist()}, open(a.model, 'w'), indent=1)
    print('model ->', a.model)


if __name__ == '__main__':
    main()
