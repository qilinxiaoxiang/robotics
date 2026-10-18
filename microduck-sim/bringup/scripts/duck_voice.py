#!/usr/bin/env python3
"""MicroDuck random voice: plays bursts of one to four duck calls with small random changes, like an animal.

Runs on the Pi (python3 + numpy). Calls come from build_duck_calls.py (default dir ~/duck_calls).
  duck_voice.py --once            one burst, then exit
  duck_voice.py                   keep going: a burst, then a random pause (mean --every seconds)
  duck_voice.py --voice mallard   only the real mallard; duck1..duck4 = one simulator voice; mix = any (default)
Each burst picks one voice, then per call: speed and pitch together x0.88..1.12 (a bigger or smaller duck),
level 0 to -5 dB, gaps 60-250 ms, and later calls in a burst slightly lower. Output goes through `aplay` on the
default ALSA device, so the softvol ceiling (D-012, -3 dB) always applies; nothing is ever louder than the file.
"""
import argparse
import glob
import os
import random
import subprocess
import sys
import time
import wave

import numpy as np

RATE = 44100


def load(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768


def voices(call_dir):
    groups = {}
    for p in sorted(glob.glob(os.path.join(call_dir, "*.wav"))):
        groups.setdefault(os.path.basename(p).split("_")[0], []).append(p)
    return groups


def perturb(x, speed, gain_db):
    n = int(len(x) / speed)
    y = np.interp(np.arange(n) * speed, np.arange(len(x)), x)
    return y * 10 ** (gain_db / 20)


def burst(groups, voice, rng):
    name = rng.choice(sorted(groups)) if voice == "mix" else voice
    calls = groups[name]
    n = rng.choices([1, 2, 3, 4], weights=[40, 30, 20, 10])[0]
    base = rng.uniform(0.88, 1.12)
    parts = []
    for i in range(n):
        speed = base * rng.uniform(0.97, 1.03) * (1 - 0.02 * i)
        parts.append(perturb(load(rng.choice(calls)), speed, -rng.uniform(0, 5)))
        if i < n - 1:
            parts.append(np.zeros(int(rng.uniform(0.06, 0.25) * RATE), np.float32))
    y = np.clip(np.concatenate(parts), -1, 1)
    return name, n, (y * 32767).astype("<i2").tobytes()


def play(pcm):
    subprocess.run(["aplay", "-q", "-t", "raw", "-f", "S16_LE", "-r", str(RATE), "-c", "1"], input=pcm, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.expanduser("~/duck_calls"))
    ap.add_argument("--voice", default="mix")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--every", type=float, default=20.0, help="mean pause between bursts, seconds")
    ap.add_argument("--seed", type=int)
    a = ap.parse_args()
    groups = voices(a.dir)
    if not groups or (a.voice != "mix" and a.voice not in groups):
        sys.exit(f"no calls for voice {a.voice!r} in {a.dir} (have {sorted(groups)})")
    rng = random.Random(a.seed)
    while True:
        name, n, pcm = burst(groups, a.voice, rng)
        print(f"{time.strftime('%H:%M:%S')} {name} x{n}", flush=True)
        play(pcm)
        if a.once:
            return
        time.sleep(max(3.0, rng.expovariate(1 / a.every)))


if __name__ == "__main__":
    main()
