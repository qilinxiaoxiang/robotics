"""ownkws: an ensemble .npz averages its members' probabilities and carries its own threshold.

  pet/.venv/bin/python -m pytest microduck-sim/guide/firmware/mac/test_ownkws.py -q
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ownkws as ok  # noqa: E402


def tiny(path, seed, threshold=0.5):
    r = np.random.default_rng(seed)
    d = dict(conv0_w=r.standard_normal((3, ok.N_MELS, 4)).astype(np.float32), conv0_b=np.zeros(4, np.float32),
             pool0=np.int32(2), dense_w=r.standard_normal((4, 3)).astype(np.float32), dense_b=np.zeros(3, np.float32),
             mu=np.zeros(ok.N_MELS, np.float32), sd=np.ones(ok.N_MELS, np.float32), threshold=np.float32(threshold),
             classes=np.array(["mochi", "speech", "noise"]))
    np.savez(path, **d)
    return str(path)


def test_ensemble_is_the_mean_of_its_members_and_has_its_own_threshold(tmp_path):
    a, b = tiny(tmp_path / "a.npz", 1), tiny(tmp_path / "b.npz", 2)
    e = ok.OwnModel(ok.pack_ensemble([a, b], str(tmp_path / "e.npz"), 0.7))
    x = np.random.default_rng(0).standard_normal((5, ok.N_FRAMES * ok.N_MELS)).astype(np.float32)
    want = (ok.OwnModel(a).probs(x) + ok.OwnModel(b).probs(x)) / 2
    assert np.allclose(e.probs(x), want, atol=1e-6)
    assert np.allclose(e.score(x), want[:, 0], atol=1e-6)
    assert abs(e.threshold - 0.7) < 1e-6 and e.classes == ["mochi", "speech", "noise"]


def test_a_single_model_file_still_loads():
    m = ok.OwnModel()
    assert m.members is not None or m.convs
    assert 0.0 < m.threshold < 1.0
