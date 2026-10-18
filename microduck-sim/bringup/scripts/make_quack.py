#!/usr/bin/env python3
"""MicroDuck: synthesize a short "quack quack quack" WAV (stdlib only, runs on the Mac or the Pi).

Usage: make_quack.py [out.wav] [count]   (default quack.wav 3)
Play it on the Pi with plain `aplay quack.wav` (default device, so the -6 dB softvol ceiling applies).

Source-filter model of a mallard quack: a jittered pulse train (pitch rises 380 -> 450 Hz, then falls to 330 Hz)
plus breath noise, through nasal formant resonators at 1.1, 2.0 and 3.0 kHz, where duck quacks carry their energy.
A 650 Hz high-pass removes content below the speaker's resonance (CMS-30204-18SP Fo 560-840 Hz), which the
speaker cannot reproduce and which only adds cone excursion and buzz. No clipping; peak -1 dBFS before the ceiling.
"""
import math
import random
import struct
import sys
import wave

RATE = 44100


def biquad(x, b, a):
    y = [0.0] * len(x)
    x1 = x2 = y1 = y2 = 0.0
    for i, v in enumerate(x):
        o = b[0] * v + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        x2, x1, y2, y1 = x1, v, y1, o
        y[i] = o
    return y


def bandpass(f, q):
    w = 2 * math.pi * f / RATE
    al = math.sin(w) / (2 * q)
    a0 = 1 + al
    return [al / a0, 0.0, -al / a0], [1.0, -2 * math.cos(w) / a0, (1 - al) / a0]


def highpass(f, q=0.707):
    w = 2 * math.pi * f / RATE
    al = math.sin(w) / (2 * q)
    c = math.cos(w)
    a0 = 1 + al
    return [(1 + c) / 2 / a0, -(1 + c) / a0, (1 + c) / 2 / a0], [1.0, -2 * c / a0, (1 - al) / a0]


def quack(dur, rng):
    n = int(dur * RATE)
    src = [0.0] * n
    next_pulse = 0.0
    for i in range(n):
        t = i / n
        f0 = 380 + 70 * t / 0.3 if t < 0.3 else 450 - 120 * (t - 0.3) / 0.7
        if i >= next_pulse:
            src[i] += 1.0
            next_pulse = i + RATE / f0 * (1 + rng.uniform(-0.04, 0.04))
        src[i] += 0.08 * rng.uniform(-1, 1)
    sig = [0.0] * n
    for f, q, g in ((1100, 5, 1.0), (2000, 6, 1.0), (3000, 7, 0.6)):
        for i, v in enumerate(biquad(src, *bandpass(f, q))):
            sig[i] += g * v
    sig = biquad(biquad(sig, *highpass(650)), *highpass(650))
    att, rel = int(0.008 * RATE), int(0.05 * RATE)
    for i in range(n):
        sig[i] *= min(1.0, i / att, (n - i) / rel)
    return sig


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "quack.wav"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    rng = random.Random(7)
    sig = []
    for j in range(count):
        sig += quack(0.24 if j == count - 1 else 0.17, rng)
        sig += [0.0] * int(0.12 * RATE)
    peak = max(abs(x) for x in sig)
    scale = 10 ** (-1 / 20) * 32767 / peak
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(x * scale)) for x in sig))
    print(f"{path}: {count} quacks, {len(sig) / RATE:.2f} s")


if __name__ == "__main__":
    main()
