"""Writes test_burst.wav: 12 s, three loud broadband bursts (0.4 s sweep 300-6000 Hz, 0.1 s gap, 0.3 s noise) at 1, 5
and 9 s. Played from a phone 1 m from the duck at head height, once per direction, it gives the head microphones a
source tens of dB over the floor, so the direction test checks the microphone geometry and channel order apart from
how loud a voice is."""
import wave

import numpy as np
from scipy import signal

FS = 48000
rng = np.random.default_rng(0)
t = np.arange(int(0.4 * FS)) / FS
sweep = signal.chirp(t, 300, t[-1], 6000, method="logarithmic")
noise = signal.sosfilt(signal.butter(4, [300, 6000], "bandpass", fs=FS, output="sos"), rng.standard_normal(int(0.3 * FS)))
noise /= np.abs(noise).max()
burst = np.concatenate([sweep, np.zeros(int(0.1 * FS)), noise])
ramp = np.minimum(1, np.minimum(np.arange(len(burst)), len(burst) - np.arange(len(burst))) / (0.005 * FS))
burst *= ramp
y = np.zeros(12 * FS)
for s in (1, 5, 9):
    y[s * FS: s * FS + len(burst)] = burst
y *= 0.5
with wave.open("test_burst.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(FS)
    w.writeframes((y * 32767).astype("<i2").tobytes())
