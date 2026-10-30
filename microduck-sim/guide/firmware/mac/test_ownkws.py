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


def scripted(scores, **kw):
    """Feed OwnSpotter silent 20 ms blocks while its model returns these P(mochi), one per 100 ms score; -> hit times."""
    import namecall as nc
    s = ok.OwnSpotter(**kw)
    it = iter(scores)
    s.model.score = lambda feats: next(it)
    hits, block = [], np.zeros((nc.BLOCK, 4), np.float32)
    for i in range(len(scores) * ok.SCORE_EVERY):
        h = s.feed(i * nc.BLOCK / nc.FS, block)
        if h is not None:
            hits.append((round(h["t_hit"], 1), h["repeat"]))
    return hits


def test_a_repeated_near_miss_is_answered_on_the_repeat():
    """2026-10-30 18:53: two calls at 0.78-0.83 under the 0.9 threshold. The second run >= 0.7 starting 1-5 s after
    the first answers; one near miss alone, or two runs too close or too far apart, do not."""
    quiet = [0.1] * 10
    near = [0.75, 0.82, 0.6]
    assert scripted(quiet + near + quiet + [0.2] * 5 + near + quiet) == [(2.9, True)]   # second run 1.8 s after the first
    assert scripted(quiet + near + quiet * 4) == []                                        # once is not enough
    assert scripted(quiet + near + [0.1] * 3 + near + quiet) == []                         # 0.6 s apart: one call
    assert scripted(quiet + near + [0.1] * 60 + near + quiet) == []                        # 6.3 s apart: separate events
    assert scripted(quiet + [0.95] + quiet) == [(1.1, False)]                              # the main threshold still fires
    assert scripted(quiet + near + quiet + [0.2] * 5 + near + quiet, repeat_threshold=None) == []   # rule off
