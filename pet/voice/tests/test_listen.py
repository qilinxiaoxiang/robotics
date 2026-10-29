"""listen.py: segmentation of a robot-format stream, resampling, whole-file fallback. No microphone, no model."""
from pathlib import Path

import numpy as np
import pytest

from pet.voice import listen
from pet.voice.synth import robot_format


def fake_speech(seconds=1.2, fs=16000, seed=1):
    """Voice-band noise with a syllable-like envelope: enough for the onset detector (300-4000 Hz, band_frac)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * fs)
    x = rng.standard_normal(n)
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / fs)
    spec[(f < 300) | (f > 3000)] = 0
    x = np.fft.irfft(spec, n)
    env = 0.55 + 0.45 * np.sin(2 * np.pi * 4 * np.arange(n) / fs) ** 2
    x *= env
    return (x / np.max(np.abs(x))).astype(np.float32)


@pytest.fixture
def robot_wav(tmp_path):
    p = tmp_path / "fake.robot.wav"
    robot_format(fake_speech(), p, pad_s=1.0)
    return p


def test_segments_one_utterance_from_robot_stream(robot_wav):
    utts = list(listen.utterances(listen.wav_blocks(robot_wav), listen.ROBOT_FS, source="test"))
    assert len(utts) == 1
    u = utts[0]
    assert u.fs == 16000
    assert listen.MIN_S <= u.seconds <= listen.MAX_S
    assert u.t_start < u.onset["t"] <= u.t_start + listen.PRE_S + 0.05   # pre-roll kept before the onset block
    assert 0.9 < u.onset["t"] < 1.3                                        # speech begins after 1.0 s of room noise
    assert u.t_end - u.onset["t"] >= 1.2                                   # the whole 1.2 s of speech is inside
    assert u.peak_dbfs > -30


def test_quiet_stream_gives_nothing(tmp_path):
    p = tmp_path / "quiet.robot.wav"
    robot_format(np.zeros(16000, np.float32), p, pad_s=1.0)
    assert list(listen.utterances(listen.wav_blocks(p), listen.ROBOT_FS)) == []


def test_max_length_bound(tmp_path):
    p = tmp_path / "long.robot.wav"
    robot_format(fake_speech(seconds=10.0), p, pad_s=1.0)
    utts = list(listen.utterances(listen.wav_blocks(p), listen.ROBOT_FS))
    assert utts and all(u.seconds <= listen.MAX_S + 0.05 for u in utts)


def test_to_16k_from_48k_keeps_length_and_tone():
    fs = 48000
    t = np.arange(fs) / fs
    x = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    y = listen.to_16k(x, fs)
    assert len(y) == 16000
    spec = np.abs(np.fft.rfft(y[2000:14000]))
    f = np.fft.rfftfreq(12000, 1 / 16000)
    assert abs(f[np.argmax(spec)] - 440) < 5
    assert np.array_equal(listen.to_16k(y, 16000), y)


def test_downmix_uses_the_ears_only():
    blk = np.zeros((960, 4), np.float32)
    blk[:, 0], blk[:, 1], blk[:, 2] = 0.2, 0.4, 9.0
    assert np.allclose(listen.downmix(blk), 0.3)
    assert np.allclose(listen.downmix(np.full((10, 2), 0.5, np.float32)), 0.5)


def test_utterance_wav_roundtrip(tmp_path):
    u = listen.Utterance(fake_speech(0.5), 0.0, 0.5, {}, "t")
    p = u.write_wav(tmp_path / "u.wav")
    blocks = list(listen.wav_blocks(p))
    assert blocks and blocks[0][1].shape == (320,)
    assert listen.wav_rate(p) == 16000
