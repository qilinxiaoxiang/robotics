"""Second-order (spring-damper) tracking: x'' = wn^2 (r - x) - 2 zeta wn x', with rate and acceleration limits.

zeta < 1 overshoots (eager), zeta >= 1 settles without overshoot (sleepy, slow settle). Integrated semi-implicitly
with sub-steps, so it is stable for the stiffnesses used here at 50 Hz output.
"""
import math

import numpy as np


def overshoot_fraction(zeta):
    """Analytic peak overshoot of a step response, as a fraction of the step (0 when zeta >= 1)."""
    if zeta >= 1.0:
        return 0.0
    return math.exp(-math.pi * zeta / math.sqrt(1.0 - zeta * zeta))


def wn_zeta_from_effort(effort, arousal):
    """Stiffness and damping of the gaze spring from Laban Effort and arousal.
    Sudden + free -> stiff and underdamped (snaps, overshoots); sustained + bound or sleepy -> soft, overdamped."""
    wn = 3.0 + 13.0 * effort.time * (0.5 + 0.5 * arousal)
    zeta = 0.32 + 0.55 * effort.flow + 0.35 * (1.0 - arousal) ** 2 + 0.15 * effort.weight
    return wn, min(zeta, 1.3)


class Spring:
    def __init__(self, x0=0.0, wn=8.0, zeta=0.7, max_rate=None, max_accel=None, substeps=8):
        self.x, self.v = float(x0), 0.0
        self.wn, self.zeta = float(wn), float(zeta)
        self.max_rate, self.max_accel = max_rate, max_accel
        self.substeps = substeps

    def step(self, r, dt):
        h = dt / self.substeps
        for _ in range(self.substeps):
            a = self.wn * self.wn * (r - self.x) - 2.0 * self.zeta * self.wn * self.v
            if self.max_accel is not None:
                a = max(-self.max_accel, min(self.max_accel, a))
            self.v += a * h
            if self.max_rate is not None:
                self.v = max(-self.max_rate, min(self.max_rate, self.v))
            self.x += self.v * h
        return self.x


def track(ref, dt, wn, zeta, x0=None, max_rate=None, max_accel=None):
    """Run a spring over a reference array (one sample per dt). wn and zeta may be arrays (per-sample gains)."""
    ref = np.asarray(ref, float)
    wn = np.broadcast_to(np.asarray(wn, float), ref.shape)
    zeta = np.broadcast_to(np.asarray(zeta, float), ref.shape)
    s = Spring(ref[0] if x0 is None else x0, wn[0], zeta[0], max_rate, max_accel)
    out = np.empty_like(ref)
    for k, r in enumerate(ref):
        s.wn, s.zeta = wn[k], zeta[k]
        out[k] = s.step(r, dt)
    return out


def step_metrics(t, x, x0, target, t_start, band=0.05):
    """Latency (first 10 % of the move), arrival (first within `band` of the move), peak overshoot fraction and
    settle time (last exit from the band), all measured from t_start."""
    move = target - x0
    if abs(move) < 1e-9:
        return dict(latency=None, arrival=None, overshoot=0.0, settle=None)
    prog = (np.asarray(x) - x0) / move
    t = np.asarray(t)
    after = t >= t_start
    lat = _first(t, after & (prog >= 0.10))
    arr = _first(t, after & (prog >= 1.0 - band))
    over = float(max(0.0, prog[after].max() - 1.0))
    outside = after & (np.abs(prog - 1.0) > band)
    settle = float(t[outside][-1] - t_start) if outside.any() else 0.0
    return dict(latency=None if lat is None else lat - t_start, arrival=None if arr is None else arr - t_start,
                overshoot=over, settle=settle)


def _first(t, mask):
    i = np.flatnonzero(mask)
    return float(t[i[0]]) if i.size else None
