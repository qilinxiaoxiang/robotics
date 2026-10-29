"""Live voice-band level of the three head microphones, one line every 0.2 s, for checking by ear whether a call is
heard above the robot's own noise. The robot does not move and nothing is written to the brain.

Run on the A7Z (stop namecall first; one reader on the card):
  arecord -q -D hw:<sndi2s0>,0 -c 4 -r 48000 -f S32_LE -t raw | python3 live_level.py
live_level.sh does both. Each line: seconds, voice-band (300-3000 Hz) level over the running floor for left / right /
back, and a bar for the loudest. A call worth localising should reach about +10 dB; a head touch shows as a short
spike on all three with a broadband (high 3-8 kHz) share, printed as "hf".
"""
import sys

import numpy as np

FS, CH, BLOCK = 48000, 4, 9600  # 0.2 s
f = np.fft.rfftfreq(BLOCK, 1 / FS)
VOICE = (f >= 300) & (f < 3000)
HIGH = (f >= 3000) & (f < 8000)
win = np.hanning(BLOCK)[:, None]
floor = None
hist = []
t = 0.0
stdin = sys.stdin.buffer
while True:
    raw = stdin.read(BLOCK * CH * 4)
    if len(raw) < BLOCK * CH * 4:
        break
    x = np.frombuffer(raw, "<i4").reshape(BLOCK, CH)[:, :3].astype(np.float64) / 2 ** 31
    x = x - x.mean(axis=0)
    P = np.abs(np.fft.rfft(x * win, axis=0)) ** 2
    v = 10 * np.log10(P[VOICE].sum(axis=0) + 1e-20)
    h = 10 * np.log10(P[HIGH].sum(axis=0) + 1e-20)
    hist.append(v)
    hist = hist[-150:]  # 30 s
    floor = np.percentile(np.array(hist), 20, axis=0)
    over = v - floor
    hf = float(np.mean(h - v))
    top = float(over.max())
    bar = "#" * int(max(0.0, min(top, 40.0)))
    print(f"{t:6.1f} s  L {over[0]:+5.1f}  R {over[1]:+5.1f}  B {over[2]:+5.1f} dB  hf {hf:+5.1f}  {bar}", flush=True)
    t += BLOCK / FS
