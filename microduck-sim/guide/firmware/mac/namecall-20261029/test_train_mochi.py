"""train_mochi: positives whose voice, speaker or room no negative shares are refused (the cue would be learned).

  pet/.venv/bin/python -m pytest microduck-sim/guide/firmware/mac/namecall-20261029/test_train_mochi.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import train_mochi as tm  # noqa: E402


def test_synthetic_voices_without_synthetic_speech_are_unmatched():
    pos = {"speaker:shawn": 42, "voice:Samantha": 8, "voice:Tingting": 8}
    neg = {"speaker:shawn": 3, "voice:Samantha": 2}               # near-miss words read by half the voices only
    assert tm.unmatched_cues(pos, neg) == ["voice:Tingting"]


def test_a_room_kept_around_the_calls_needs_that_room_as_a_negative():
    assert tm.unmatched_cues({"room:calls_221619": 4}, {"room:live_205910": 1}) == ["room:calls_221619"]
    assert tm.unmatched_cues({"room:calls_221619": 4}, {"room:calls_221619": 9}) == []


def test_exported_model_matches_torch_with_batch_norm_folded(tmp_path):
    """The .npz the A7Z runs (numpy, no batch norm) gives the trained network's probabilities."""
    import argparse

    import numpy as np
    import pytest
    torch = pytest.importorskip("torch")
    import ownkws as ok
    rng = np.random.default_rng(0)
    X = rng.standard_normal((300, ok.N_FRAMES, ok.N_MELS)).astype(np.float32)
    Y = rng.integers(0, 3, 300)
    d = tm.train_torch(X, Y, argparse.Namespace(threads=1, epochs=2), seed=0)
    d["threshold"] = np.float32(0.9)
    p = str(tmp_path / "m.npz")
    np.savez(p, **d)
    got = ok.OwnModel(p).probs(X[:20])
    assert got.shape == (20, 3) and np.allclose(got.sum(axis=1), 1, atol=1e-5)
    assert np.allclose(got, tm.LAST_TORCH_PROBS(X[:20]), atol=2e-4)
