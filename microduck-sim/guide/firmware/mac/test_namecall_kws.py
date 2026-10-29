"""namecall.py --name: the keyword gate. A call is answered only when the spotter hears the name; the direction is
taken at the word (the detector onset nearest its start), never at an earlier sound; the duck's own calls never wake
it. The gating tests use a scripted spotter; the last tests use the real sherpa-onnx model when it is installed
(~/rt/models/kws/ or $NAMECALL_KWS_MODEL) and skip otherwise.

  pet/.venv/bin/python -m pytest microduck-sim/guide/firmware/mac/test_namecall_kws.py -q
"""
import math
import os
import shutil
import subprocess
import sys
import wave

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import namecall as nc  # noqa: E402

FS, B = nc.FS, nc.BLOCK


def args(**kw):
    base = dict(threshold_db=12.0, rise_db=6.0, refractory=2.5, floor_tau=3.0, swap_ears=False, no_head=True, seed=3,
                smooth=False, idle=False, no_sound=True, bank_dir="/tmp/namecall_test_bank", sounds=None, mute=True,
                cmd="/tmp/namecall_test_kws_cmd.json", dry=True, no_gate=True, brain_logs="/nonexistent/*.jsonl",
                pitch=0.2, once=0, default_head_file=None, name="mochi", onset_gap=nc.ONSET_GAP_S,
                detector="energy", localiser="short")   # the name-mode mechanics as built; the 2 m components: test_namecall_call.py
    base.update(kw)
    return type("A", (), base)()


class ScriptedSpotter:
    """Stands in for KeywordGate: 'hears' the name at the given spot times; records what it was fed."""

    def __init__(self, spots, keyword="MOCHI"):
        self.spots = sorted(spots)
        self.keyword = keyword
        self.silent = []
        self.resets = []
        self.keywords_file, self.model_dir = "scripted", None

    def reset(self):
        self.resets.append(self.silent[-1][0] if self.silent else None)

    def feed(self, t, block, silent=False):
        self.silent.append((t, silent))
        t_end = t + len(block) / FS
        for s in self.spots:
            if t < s <= t_end + 1e-9:
                self.spots.remove(s)
                return dict(t_hit=round(t_end, 3), keyword=self.keyword, tokens=[], span_s=0.3)
        return None


def scene(events, dur, snr_db=20.0, seed=0):
    """events: (t, az_deg, kind) -> 4-channel scene with white noise."""
    x = np.zeros((int(dur * FS), 4), np.float32)
    rng = np.random.default_rng(seed)
    for k, (t, az, kind) in enumerate(events):
        sig = nc.synth_call(seed=seed + k, kind=kind) * (0.6 if kind == "clap" else 0.3)
        s, pre = nc.render_scene(sig, math.radians(az), pre_s=0.0, post_s=0.0, snr_db=200.0, seed=k)
        i = int(t * FS)
        x[i:i + len(s)] += s[: len(x) - i]
    noise = rng.standard_normal(x.shape).astype(np.float32) * 0.3 * 0.25 * 10 ** (-snr_db / 20)
    noise[:, 3] = 0
    return x + noise


def blocks(x):
    for i in range(0, len(x) - B + 1, B):
        yield i / FS, x[i:i + B]


def run(spots, events, dur, **kw):
    sp = ScriptedSpotter(spots)
    n = nc.NameCall(args(**kw), nc.Log(None, echo=False), now=lambda: 0.0, kws=sp)
    return n, sp, n.run_blocks(blocks(scene(events, dur)))


# --- the gate

def test_voices_without_the_name_get_no_response_but_any_voice_mode_still_answers_them():
    events = [(1.0, 50, "voice"), (4.0, -30, "voice")]
    n, _, dets = run([], events, 6.0)
    assert dets == [] and n.responses == 0
    plain = nc.NameCall(args(name=None, refractory=2.5), nc.Log(None, echo=False), now=lambda: 0.0)
    assert plain.kws is None
    got = plain.run_blocks(blocks(scene(events, 6.0)))
    assert [round(d["t"], 1) for d in got] == [1.0, 4.0]


def test_direction_is_taken_at_the_word_not_at_an_earlier_clap():
    # a clap from the left 0.7 s before the word (inside the candidate window), the name from the right
    n, _, dets = run([3.0 + nc.KW_BACK_S], [(2.3, 60, "clap"), (3.0, -40, "voice")], 5.0)
    assert any(abs(o["t"] - 2.3) < 0.03 for o in n.onsets)     # the detector did hear the clap
    assert len(dets) == 1
    d = dets[0]
    assert d["onset_from"] == "detector" and abs(d["t"] - 3.0) < 0.03
    assert abs(d["az_deg"] + 40) < 4
    assert d["keyword"] == "MOCHI" and d["decided_t"] - d["t_hit"] <= B / FS + 1e-6


def test_without_a_detector_onset_the_keyword_time_places_the_window():
    # detector made deaf to this level: the window starts KW_BACK_S before the spot, inside the word
    n, _, dets = run([2.0 + nc.KW_BACK_S + 0.1], [(2.0, 25, "voice")], 4.0, threshold_db=80.0)
    assert len(dets) == 1
    assert dets[0]["onset_from"] == "keyword" and abs(dets[0]["az_deg"] - 25) < 6


def test_a_second_name_within_the_refractory_period_is_one_call():
    n, _, dets = run([1.8, 2.8, 5.5], [(1.0, 10, "voice"), (2.1, 10, "voice"), (4.8, -70, "voice")], 7.0)
    assert len(dets) == 2
    assert abs(dets[1]["az_deg"] + 70) < 4


def test_the_spotter_hears_silence_while_the_own_quack_plays():
    class Bank:
        files = {}

        def __init__(self):
            self.on = False

        def playing(self):
            return self.on

        def play(self, e):
            return None

    sp = ScriptedSpotter([])
    n = nc.NameCall(args(), nc.Log(None, echo=False), now=lambda: 0.0, kws=sp)
    n.bank = Bank()
    x = scene([], 3.0)
    for t, b in blocks(x):
        n.bank.on = 1.0 <= t < 1.5
        n.hear(t, b)
    def at(tq):
        return min(sp.silent, key=lambda r: abs(r[0] - tq))[1]

    assert not at(0.8) and at(1.0) and at(1.48)
    assert at(1.5 + nc.QUACK_DEAF_S - 0.04)                  # still deaf right after the player ends
    assert not at(1.5 + nc.QUACK_DEAF_S + 0.1)               # listening again


def test_the_spotter_rests_during_the_take_and_starts_afresh_after_it():
    sp = ScriptedSpotter([1.0 + nc.KW_BACK_S])
    n = nc.NameCall(args(no_head=False, dry=True), nc.Log(None, echo=False), now=lambda: 0.0, kws=sp)
    n.head.default = dict(nc.DEFAULT_HEAD)
    dets = n.run_blocks(blocks(scene([(1.0, 45, "voice")], 8.0)))
    assert len(dets) == 1
    fed = [t for t, _ in sp.silent]
    gaps = [(a, b) for a, b in zip(fed, fed[1:]) if b - a > 0.05]
    assert len(gaps) == 1                                   # one pause: the take
    a, b = gaps[0]
    assert abs(a - (dets[0]["t_hit"] - B / FS)) < 0.03       # stopped right after the spot
    assert b - a > 0.5 and sp.resets == [a]                  # rested through the take, then a fresh stream


def test_cli_name_and_any_voice_are_exclusive_and_any_voice_is_the_default():
    assert nc.parse_args([]).name is None
    assert nc.parse_args(["--name", "mochi"]).name == "mochi"
    with pytest.raises(SystemExit):
        nc.parse_args(["--name", "mochi", "--any-voice"])
    with pytest.raises(SystemExit):
        nc.parse_args(["--name", "kiki"])
    assert os.path.isfile(nc.KEYWORDS["mochi"])


def test_decimate3_keeps_the_voice_band_and_removes_what_would_alias():
    d = nc.Decimate3()
    t = np.arange(FS) / FS
    x = (0.5 * np.sin(2 * math.pi * 1000 * t) + 0.5 * np.sin(2 * math.pi * 10000 * t)).astype(np.float32)
    y = np.concatenate([d(x[i:i + B]) for i in range(0, len(x), B)])
    assert len(y) == 16000
    Y = np.abs(np.fft.rfft(y[1600:] * np.hanning(len(y) - 1600)))
    f = np.fft.rfftfreq(len(y) - 1600, 1 / 16000)
    a1k = Y[np.argmin(np.abs(f - 1000))]
    a6k = Y[np.argmin(np.abs(f - 6000))]          # 10 kHz would fold to 6 kHz
    assert 20 * math.log10(a1k / a6k) > 50
    whole = nc.Decimate3()(x)
    assert np.allclose(whole, y, atol=1e-5)          # block-wise equals one pass


# --- the real spotter (skips without sherpa-onnx or the model)

def real_gate():
    pytest.importorskip("sherpa_onnx")
    model = nc.find_kws_model()
    if model is None:
        pytest.skip("keyword model not installed (~/rt/models/kws/)")
    return nc.KeywordGate(model, nc.KEYWORDS["mochi"])


def test_the_ducks_own_calls_never_wake_the_spotter():
    from pet.express.voice import find_calls, read_wav, render_call
    gate = real_gate()
    srcs = find_calls()
    if not srcs:
        pytest.skip("no duck recordings")
    clips = []
    for si, p in enumerate(srcs):
        x, rate = read_wav(p)
        clips.append((x, rate))
        if si < 4:                                     # the QuackBank variants the robot actually plays
            clips += [(render_call(x, pi, st, 0.0) * 0.9, rate) for pi in nc.QuackBank.PITCHES for st in nc.QuackBank.STRETCHES]
    rng = np.random.default_rng(0)
    t, hits = 0.0, []
    for x, rate in clips:
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * FS / rate)), np.arange(len(x)), x).astype(np.float32)
        s, _ = nc.render_scene(x * 0.3, rng.uniform(-3, 3), pre_s=0.5, post_s=0.8, snr_db=30.0, seed=len(hits))
        for i in range(0, len(s) - B + 1, B):
            h = gate.feed(t, s[i:i + B])
            if h:
                hits.append(h)
            t += B / FS
    assert len(clips) >= 48
    assert hits == []


@pytest.mark.skipif(shutil.which("say") is None, reason="needs macOS say")
def test_a_spoken_mochi_wakes_it_and_points_at_the_speaker(tmp_path):
    real_gate()
    p = str(tmp_path / "mochi.wav")
    # Karen's "Mochi" is one the spotter catches (the model writes it MARCHY); most voices are missed, NAMECALL.md 9
    subprocess.run(["say", "-v", "Karen", "--data-format=LEI16@48000", "-o", p, "Mochi"], check=True)
    with wave.open(p) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    x = np.concatenate([np.zeros(FS, np.float32), x, np.zeros(FS // 2, np.float32), x])
    s, _ = nc.render_scene(x * 0.5, math.radians(-55), pre_s=1.0, post_s=1.5, snr_db=25.0, seed=4)
    out = tmp_path / "scene.wav"
    with wave.open(str(out), "w") as w:
        w.setnchannels(4), w.setsampwidth(4), w.setframerate(FS)
        w.writeframes(((np.clip(s, -1, 1) * (2 ** 23 - 1)).astype("<i4") << 8).astype("<i4").tobytes())
    log = str(tmp_path / "log.jsonl")
    assert nc.main(["--wav", str(out), "--name", "mochi", "--no-head", "--no-sound", "--log", log, "--quiet"]) == 0
    import json
    rows = [json.loads(l) for l in open(log)]
    calls = [r for r in rows if r["kind"] == "call"]
    assert 1 <= len(calls) <= 2                       # the second "Mochi" is inside the refractory period
    assert calls[0]["keyword"] == "MOCHI" and abs(calls[0]["az_deg"] + 55) < 8
    rep = [r for r in rows if r["kind"] == "replay"][0]
    assert rep["trigger"] == "name" and rep["kw_hits"] >= 1
