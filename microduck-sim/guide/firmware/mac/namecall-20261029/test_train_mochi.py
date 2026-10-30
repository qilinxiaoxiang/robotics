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
