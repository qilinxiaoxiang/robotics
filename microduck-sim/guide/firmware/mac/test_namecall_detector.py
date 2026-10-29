"""namecall.py OnsetDetector: what counts as a call and what does not.

  pet/.venv/bin/python -m pytest microduck-sim/guide/firmware/mac/test_namecall_detector.py -q
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import namecall as nc  # noqa: E402

FS, B = nc.FS, nc.BLOCK


def run(det, x):
    """All onsets of a (n, ch) signal through 20 ms blocks."""
    hits = []
    for i in range(0, len(x) - B + 1, B):
        ev = det.update(i / FS, x[i:i + B])
        if ev:
            hits.append(ev)
    return hits


def scene(calls, dur=6.0, snr_db=20.0, seed=0, kind="voice"):
    """Noise floor with calls (t, az_deg) rendered from the front; returns (x, true onsets)."""
    rng = np.random.default_rng(seed)
    n = int(dur * FS)
    sig = nc.synth_call(seed=seed, kind=kind)
    rms = float(np.sqrt(np.mean(sig ** 2)))
    x = rng.standard_normal((n, 4)).astype(np.float32) * rms * 10 ** (-snr_db / 20)
    x[:, 3] = 0
    for t, az in calls:
        y, pre = nc.render_scene(sig, math.radians(az), pre_s=0.0, post_s=0.0, snr_db=200, seed=seed)
        i = int(t * FS)
        x[i:i + len(y)] += y[: n - i]
    return x


def test_one_call_one_onset_at_its_start():
    x = scene([(2.0, 0)])
    hits = run(nc.OnsetDetector(), x)
    assert len(hits) == 1
    assert abs(hits[0]["t"] - 2.0) <= 0.03          # the onset block (20 ms blocks)
    assert hits[0]["over_db"] >= 12 and hits[0]["rise_db"] >= 6


def test_refractory_merges_a_quick_second_call_and_accepts_a_later_one():
    x = scene([(1.5, 0), (2.5, 30), (5.0, -30)], dur=7.0)
    hits = run(nc.OnsetDetector(refractory_s=2.0), x)
    assert [round(h["t"], 1) for h in hits] == [1.5, 5.0]


def test_a_slow_swell_is_not_a_call():
    rng = np.random.default_rng(3)
    n = int(6 * FS)
    x = rng.standard_normal((n, 4)).astype(np.float32) * 1e-3
    t = np.arange(n) / FS
    frac = np.clip((t - 2.0) / 3.0, 0, 1)
    tone = np.sin(2 * math.pi * 800 * t) * 1e-3 * 10 ** (30 * frac / 20) * (t >= 2.0)   # 10 dB/s swell to +30 dB
    x[:, :3] += tone[:, None].astype(np.float32)
    assert run(nc.OnsetDetector(), x) == []


def test_low_frequency_rumble_is_not_a_call():
    rng = np.random.default_rng(4)
    n = int(5 * FS)
    x = rng.standard_normal((n, 4)).astype(np.float32) * 1e-3
    t = np.arange(n) / FS
    hum = (np.sin(2 * math.pi * 60 * t) + 0.5 * np.sin(2 * math.pi * 120 * t)) * 0.4 * (t > 2.0)   # a sudden motor hum
    x[:, :3] += hum[:, None].astype(np.float32)
    assert run(nc.OnsetDetector(), x) == []


def test_a_single_click_is_not_a_call_but_a_clap_is():
    rng = np.random.default_rng(5)
    n = int(4 * FS)
    x = rng.standard_normal((n, 4)).astype(np.float32) * 1e-3
    i = int(2.0 * FS)
    x[i:i + 48, :3] += 0.8      # 1 ms click: loud in one block only
    assert run(nc.OnsetDetector(), x) == []
    y = scene([(2.0, 0)], kind="clap")
    assert len(run(nc.OnsetDetector(), y)) == 1


def test_deaf_window_hides_the_own_quack():
    x = scene([(2.0, 0), (4.5, 0)], dur=7.0)
    det = nc.OnsetDetector(refractory_s=1.0)
    det.deaf_until = 2.6
    hits = run(det, x)
    assert [round(h["t"], 1) for h in hits] == [4.5]


def test_floor_follows_a_change_of_room_noise():
    rng = np.random.default_rng(6)
    n = int(12 * FS)
    x = rng.standard_normal((n, 4)).astype(np.float32) * 1e-3
    x[int(4 * FS):] *= 10          # 20 dB more room noise from 4 s on (a fan)
    det = nc.OnsetDetector(floor_tau_s=2.0)
    hits = run(det, x)
    assert hits == [] or all(h["t"] < 4.2 for h in hits)   # at most the step itself, never afterwards
    assert det.floor is not None and det.floor > -60     # the floor rose with the room


def test_levels_use_24_bit_left_justified_samples():
    raw = (np.array([(1 << 31) - 1, -(1 << 31)], dtype="<i4").tobytes() * 2)
    x = nc.i2s_to_float(raw, 4)
    assert x.shape == (1, 4)
    assert abs(x[0, 0] - 1.0) < 1e-6 and abs(x[0, 1] + 1.0) < 1e-6
