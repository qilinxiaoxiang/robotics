"""life_log: segments open on voice, spotter score, events and the periodic sample, keep the pre-roll, stop when full.

  pet/.venv/bin/python -m pytest microduck-sim/guide/firmware/mac/test_life_log.py -q
"""
import json
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import life_log as ll  # noqa: E402
import namecall as nc  # noqa: E402

BLOCK = 960      # 20 ms at 48 kHz


def blocks(seconds, tone_from=None, tone_to=None, rng=np.random.default_rng(0)):
    t = 0.0
    for i in range(int(seconds / 0.02)):
        x = rng.standard_normal((BLOCK, 4)).astype(np.float32) * 1e-4
        if tone_from is not None and tone_from <= t < tone_to:
            n = np.arange(BLOCK) + i * BLOCK
            x[:, :3] += 0.1 * np.sin(2 * np.pi * 800 * n / 48000)[:, None]
        yield t, x
        t += 0.02


def index(d):
    p = os.path.join(d, "life_index.jsonl")
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def test_a_voice_opens_one_segment_with_its_pre_roll_and_post_roll(tmp_path):
    log = ll.LifeLog(str(tmp_path), nc.Decimate3, sample_every_s=1e9)
    for t, b in blocks(30, tone_from=10.0, tone_to=11.0):
        log.feed(t, b, score=0.0)
    log.close()
    segs = index(str(tmp_path))
    assert len(segs) == 1
    s = segs[0]
    assert s["triggers"][0][1] == "voice" and abs(s["t0"] - (10.0 - ll.PRE_S)) < 0.1
    assert abs(s["dur_s"] - (ll.PRE_S + 1.0 + ll.POST_S)) < 0.5
    with wave.open(os.path.join(str(tmp_path), s["file"])) as w:
        assert w.getnchannels() == 3 and w.getframerate() == 16000


def test_spotter_score_answers_and_the_periodic_sample_open_segments(tmp_path):
    log = ll.LifeLog(str(tmp_path), nc.Decimate3, sample_every_s=40.0, sample_s=5.0)
    for t, b in blocks(100):
        log.feed(t, b, score=0.5 if 20.0 <= t < 20.1 else 0.0)
        if abs(t - 60.0) < 1e-6:
            log.note(t, "call", keyword="MOCHI")
    log.close()
    why = [tr[1] for s in index(str(tmp_path)) for tr in s["triggers"]]
    assert "score" in why and "call" in why and why.count("sample") >= 2
    assert any(n["kind"] == "call" for s in index(str(tmp_path)) for n in s["notes"])


def test_writing_stops_when_the_cap_is_reached(tmp_path):
    stops = []
    log = ll.LifeLog(str(tmp_path), nc.Decimate3, sample_every_s=1e9, max_gb=1e-6, on_stop=stops.append)
    for t, b in blocks(40, tone_from=5.0, tone_to=6.0):
        log.feed(t, b)
    for t, b in blocks(40, tone_from=5.0, tone_to=6.0):
        log.feed(t + 40, b)
    log.close()
    assert len(index(str(tmp_path))) == 1 and stops and stops[0]["why"] == "life log full"
