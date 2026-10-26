"""Duck adapter: Expressor outputs -> walk_brain.py's head command path, unchanged.

walk_brain.Brain.tick reads want["head"] = {joint: absolute model rad}, turns it into deltas from the policy default
pose clipped to HEAD_RANGE (head_target), and smooths them with head_cmd += HEAD_ALPHA * (target - head_cmd) before
the stand/walk policy sees them. A first-order filter cannot overshoot or anticipate, so the adapter pre-inverts it:
it sends r_k = c_{k-1} + (y_k - c_{k-1}) / HEAD_ALPHA, which makes head_cmd follow the wanted trajectory y exactly
whenever r_k stays inside HEAD_RANGE (else it saturates and head_cmd lags until it catches up).

The alternative, a two-line walk_brain change (a want key that sets head_cmd directly), is described in README.md;
nothing in microduck-sim is edited from here.
"""
import numpy as np

# walk_brain.py constants (tests/test_channels.py parses walk_brain.py and fails if these drift)
HEAD_JOINTS = ("neck_pitch", "head_pitch", "head_yaw", "head_roll")
HEAD_RANGE = (1.10, 1.10, 1.40, 0.31)
HEAD_ALPHA = 0.2


def head_deltas(outputs):
    """{output: array} -> (n, 4) wanted head-command deltas in HEAD_JOINTS order."""
    return np.stack([np.asarray(outputs[j], float) for j in HEAD_JOINTS], axis=1)


def ema_preinverse(y, alpha=HEAD_ALPHA, rng=HEAD_RANGE, c0=None):
    """Wanted head_cmd rows y (n, 4) -> (r, c): r the targets to send, c what walk_brain's EMA then produces."""
    y = np.asarray(y, float)
    lim = np.asarray(rng, float)
    r = np.empty_like(y)
    c = np.empty_like(y)
    prev = np.zeros(y.shape[1]) if c0 is None else np.asarray(c0, float)
    for k in range(len(y)):
        r[k] = np.clip(prev + (y[k] - prev) / alpha, -lim, lim)
        prev = prev + alpha * (r[k] - prev)
        c[k] = prev
    return r, c


def ema(r, alpha=HEAD_ALPHA, rng=HEAD_RANGE, c0=None):
    """walk_brain's head smoothing applied to targets r (n, 4)."""
    r = np.clip(np.asarray(r, float), -np.asarray(rng), np.asarray(rng))
    c = np.empty_like(r)
    prev = np.zeros(r.shape[1]) if c0 is None else np.asarray(c0, float)
    for k in range(len(r)):
        prev = prev + alpha * (r[k] - prev)
        c[k] = prev
    return c


def want_head(row, default):
    """One target row (4 deltas) -> want["head"] for walk_brain (absolute model rad)."""
    return {n: float(default[n] + row[k]) for k, n in enumerate(HEAD_JOINTS)}
