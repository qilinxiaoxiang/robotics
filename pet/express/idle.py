"""Living stillness: 1-D Perlin gradient noise for idle gaze drift, head tilt and breathing posture."""
import math

import numpy as np


class Perlin1D:
    """Classic 1-D gradient noise: smooth, zero at integer lattice points, |value| <= 0.5 per octave."""

    def __init__(self, seed=0, size=256):
        rng = np.random.default_rng(seed)
        self.g = rng.uniform(-1.0, 1.0, size)
        self.p = rng.permutation(size)
        self.n = size

    def __call__(self, x):
        x = np.asarray(x, float)
        i0 = np.floor(x).astype(int)
        f = x - i0
        g0 = self.g[self.p[i0 % self.n]]
        g1 = self.g[self.p[(i0 + 1) % self.n]]
        u = f * f * f * (f * (f * 6 - 15) + 10)  # quintic fade
        return (1 - u) * g0 * f + u * g1 * (f - 1)

    def fbm(self, x, octaves=3, lacunarity=2.0, gain=0.5):
        out, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
        for k in range(octaves):
            out = out + amp * self(np.asarray(x) * freq + 17.3 * k)
            norm += amp
            amp *= gain
            freq *= lacunarity
        return out / norm * 2.0  # roughly within [-1, 1]


class Idle:
    """Idle offsets for the semantic axes. Arousal scales amplitude and speed; low arousal droops the posture."""

    def __init__(self, seed=0):
        self.n = {k: Perlin1D(seed * 31 + i) for i, k in enumerate(("yaw", "pitch", "tilt", "posture"))}

    def sample(self, t, arousal=0.4, scale=1.0):
        a = 0.3 + 0.7 * arousal
        speed = 0.12 + 0.35 * arousal  # lattice cells per second
        breathe = 0.5 * math.sin(2 * math.pi * t / (4.5 - 1.5 * arousal))
        return {
            "ATTEND.yaw": scale * 0.10 * a * float(self.n["yaw"].fbm(t * speed)),
            "ATTEND.pitch": scale * 0.05 * a * float(self.n["pitch"].fbm(t * speed * 0.8)),
            "GESTURE.tilt": scale * 0.06 * a * float(self.n["tilt"].fbm(t * speed * 0.6)),
            "POSTURE.height": scale * (0.06 * breathe + 0.08 * float(self.n["posture"].fbm(t * 0.1)))
            - 0.35 * max(0.0, 0.35 - arousal),
        }
