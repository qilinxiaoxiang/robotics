import math

import pytest

from pet.identity.whois import DEFAULT_CUES, STRANGER, CueModel, Whois, sigmoid


def test_single_face_observation_arithmetic():
    w = Whois()
    added = w.observe(0.0, "face", {1: 0.65, 2: 0.10})
    face = DEFAULT_CUES["face"]
    assert added[1] == pytest.approx(face.slope * (0.65 - face.match_cos))          # +3.0
    assert added[2] == pytest.approx(face.slope * (0.10 - face.match_cos))           # -3.6
    assert added[STRANGER] == pytest.approx(-face.max_llr)  # 12 * (0.25 - 0.65) = -4.8, clipped to -4
    d = w.decide(0.0, labeler=lambda pid: "owner" if pid == 1 else f"known:p{pid}")
    assert d.label == "owner" and d.person_id == 1
    assert d.confidence == pytest.approx(sigmoid(3.0))


def test_quality_scales_llr():
    w = Whois()
    a = w.observe(0.0, "face", {1: 0.65}, quality=0.5)
    assert a[1] == pytest.approx(1.5)


def test_decay_with_time_constant():
    w = Whois(tau_s=20.0)
    w.observe(0.0, "face", {1: 0.65})
    w.decide(20.0)
    assert w.L[1] == pytest.approx(3.0 / math.e)
    d = w.decide(60.0)
    assert d.label == "unsure"  # evidence faded


def test_face_and_voice_accumulate():
    w = Whois()
    w.observe(0.0, "face", {1: 0.50})    # +1.2: not enough alone
    assert w.decide(0.0).label == "unsure"
    w.observe(1.0, "voice", {1: 0.75})   # +1.8
    d = w.decide(1.0)
    expected = 1.2 * math.exp(-1 / 20) + 1.8
    assert w.L[1] == pytest.approx(expected)
    assert d.label == "known:p1" and d.confidence == pytest.approx(sigmoid(expected))


def test_stranger_accumulates_from_low_similarity():
    w = Whois()
    w.observe(0.0, "face", {1: 0.05, 2: 0.08})   # stranger +min(4, 12*0.17)=2.04
    w.observe(0.5, "face", {1: 0.02, 2: 0.10})
    d = w.decide(0.5)
    assert d.label == STRANGER and d.person_id is None
    assert d.confidence > 0.95


def test_no_known_persons_is_stranger_evidence():
    w = Whois()
    w.observe(0.0, "face", {})
    assert w.L[STRANGER] == pytest.approx(DEFAULT_CUES["face"].max_llr)  # best cos taken as -1, clipped


def test_margin_keeps_close_candidates_unsure():
    w = Whois()
    w.observe(0.0, "face", {1: 0.66, 2: 0.64})
    assert w.decide(0.0).label == "unsure"


def test_non_anchor_cue_only_reinforces():
    w = Whois()
    w.observe(0.0, "silhouette", {1: 0.95})
    assert 1 not in w.L and STRANGER not in w.L       # cannot name anyone alone
    w.observe(0.1, "face", {1: 0.55})                  # +1.8
    w.observe(0.2, "silhouette", {1: 0.95})            # +min(1.5, 6*0.35)=1.5
    assert w.L[1] == pytest.approx(1.8 * math.exp(-0.1 / 20) + 1.5)
    w.observe(0.3, "silhouette", {1: 0.10})            # negative silhouette ignored
    assert w.decide(0.3).label == "known:p1"


def test_register_custom_cue():
    w = Whois()
    w.register_cue(CueModel("gait", match_cos=0.5, slope=4, max_llr=1, stranger_cos=0.1, anchor=True))
    a = w.observe(0.0, "gait", {3: 0.9})
    assert a[3] == pytest.approx(1.0)


def test_log_odds_are_clamped_so_a_new_face_can_overturn():
    w = Whois(max_abs=6.0)
    for i in range(100):
        w.observe(i * 0.25, "face", {1: 0.9})
    assert w.L[1] == pytest.approx(6.0)
    t = 25.0
    for i in range(3):   # three clearly different faces, 0.25 s apart
        w.observe(t + i * 0.25, "face", {1: 0.02})
    assert w.decide(t + 0.5).label != "known:p1"
