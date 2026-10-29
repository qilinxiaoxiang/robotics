"""namecall.py's 2 m components: CallDetector (per-bin SNR over a tracked noise spectrum, voicing check), CallLocaliser
(masked SRP-PHAT over the whole call with an elevation prior) and the replay tool.

  pet/.venv/bin/python -m pytest microduck-sim/guide/firmware/mac/test_namecall_call.py -q
"""
import json
import math
import os
import sys
import time
import wave

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "namecall-20261029"))
import namecall as nc  # noqa: E402
import replay_calls  # noqa: E402

FS, B = nc.FS, nc.BLOCK


def wrap(d):
    return (d + 180) % 360 - 180


def noise_floor(n, seed, level=1e-3):
    """Pink-ish room noise: white noise low-passed, plus a 120 Hz line, on the three live channels."""
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((n, 4)).astype(np.float32)
    k = np.ones(8, np.float32) / 8
    for c in range(3):
        w[:, c] = np.convolve(w[:, c], k, mode="same")
    t = np.arange(n) / FS
    w[:, :3] += (0.5 * np.sin(2 * math.pi * 120 * t))[:, None].astype(np.float32)
    w[:, 3] = 0
    return w * level


def scene(calls, dur=8.0, seed=0, call_db=10.0, el=35.0, kind="voice"):
    """Calls at the given (t, az) rendered on the head geometry at elevation el, call_db over the floor in 300-4000 Hz
    band power at the loudest block. The 2 m calls were 1-9 dB over with three or four harmonics 10-20 dB over their
    bins; the synthetic call spreads its energy over 17 harmonics, so it needs about 10 dB here to lift as many bins.
    Returns the 4-channel scene."""
    x = noise_floor(int(dur * FS), seed)
    sig = nc.synth_call(seed=seed, kind=kind)
    det = nc.OnsetDetector()
    fl = float(np.median([det.level(x[i:i + B, :3].mean(axis=1))[0] for i in range(0, 50 * B, B)]))
    sl = max(det.level(sig[i:i + B])[0] for i in range(0, len(sig) - B, B))     # the call's loudest block
    gain = 10 ** ((fl + call_db - sl) / 20)
    for t, az in calls:
        y, _ = nc.render_scene(sig * gain, math.radians(az), pre_s=0.0, post_s=0.0, snr_db=200, seed=seed,
                               el_rad=math.radians(el))
        i = int(t * FS)
        x[i:i + len(y)] += y[: len(x) - i]
    return x


def run_det(det, x):
    hits = []
    for i in range(0, len(x) - B + 1, B):
        ev = det.update(i / FS, x[i:i + B])
        if ev:
            hits.append(ev)
    return hits


# --- detector

def test_quiet_calls_are_caught_where_the_energy_detector_misses_them():
    x = scene([(2.0, 30), (5.0, -60)], call_db=10.0)
    bins = run_det(nc.CallDetector(), x)
    assert [round(h["t"], 1) for h in bins] == [2.0, 5.0]
    assert all(h["bins"] >= nc.DET_MIN_BINS and h["voicing"] >= nc.DET_VOICING for h in bins)
    assert run_det(nc.OnsetDetector(), x) == []                 # 10 dB over the floor is under its 12 dB threshold


def test_the_noise_itself_never_triggers():
    x = noise_floor(int(60 * FS), seed=7)
    assert run_det(nc.CallDetector(), x) == []


def test_a_footstep_is_not_voiced_but_a_call_is():
    """A broadband thump (footstep, touch) lifts many bins but has no pitch; the voicing check turns it down."""
    x = noise_floor(int(6 * FS), seed=3)
    rng = np.random.default_rng(3)
    i = int(2.0 * FS)
    thump = rng.standard_normal(int(0.12 * FS)).astype(np.float32) * np.exp(-np.arange(int(0.12 * FS)) / (0.04 * FS))
    x[i:i + len(thump), :3] += (thump * 0.02)[:, None]
    assert run_det(nc.CallDetector(voicing=0.0), x) != []       # loud enough to be an onset
    assert run_det(nc.CallDetector(), x) == []                   # not periodic: refused
    y = scene([(2.0, 0)], dur=6.0)
    assert len(run_det(nc.CallDetector(), y)) == 1


def test_a_click_is_not_a_call_and_the_refractory_holds():
    x = noise_floor(int(6 * FS), seed=5)
    x[int(2.0 * FS):int(2.0 * FS) + 48, :3] += 0.5
    assert run_det(nc.CallDetector(voicing=0.0), x) == []
    y = scene([(1.5, 0), (2.5, 30), (5.5, -30)], dur=8.0)
    assert [round(h["t"], 1) for h in run_det(nc.CallDetector(refractory_s=2.5), y)] == [1.5, 5.5]


def test_noise_spectrum_follows_the_room_and_a_reset_restarts_it():
    x = noise_floor(int(14 * FS), seed=6)
    x[int(5 * FS):] *= 8          # 18 dB more room noise from 5 s on
    det = nc.CallDetector()
    hits = run_det(det, x)
    assert all(h["t"] < 5.5 for h in hits)       # at most the step itself
    f1 = det.floor
    det.reset_floor()
    assert det.floor is None
    run_det(det, x[int(6 * FS):int(7 * FS)])
    assert abs(det.floor - f1) < 3


# --- localiser

@pytest.mark.parametrize("snr_db", [20, 10])
def test_call_localiser_all_round_at_the_prior_elevation(snr_db):
    loc = nc.CallLocaliser()
    sig = nc.synth_call(seed=2)
    errs, margins = [], []
    for az in range(-180, 180, 15):
        x, on = nc.render_scene(sig, math.radians(az), pre_s=2.6, post_s=1.0, snr_db=snr_db, seed=az + 300,
                                el_rad=math.radians(35))
        est = loc.estimate(x[: int((on + 0.85) * FS) + loc.after], int(on * FS))
        assert est is not None and est["bins"] > 100 and est["el_deg"] == 35.0
        errs.append(abs(wrap(est["az_deg"] - az)))
        margins.append(est["margin"])
    errs = np.array(errs)
    assert errs.max() < (4.0 if snr_db >= 20 else 8.0), errs
    assert (errs > 90).sum() == 0
    assert min(m for m, az in zip(margins, range(-180, 180, 15)) if abs(az) != 90) > 0.02   # the back mic told front from back


def test_elevation_search_finds_the_caller_height_and_a_fixed_prior_compresses_it():
    sig = nc.synth_call(seed=4)
    x, on = nc.render_scene(sig, math.radians(40), pre_s=2.6, post_s=1.0, snr_db=25, seed=11, el_rad=math.radians(0))
    search = nc.CallLocaliser(elev_deg=(0, 20, 35, 50)).estimate(x, int(on * FS))
    assert search["el_deg"] == 0.0 and abs(search["az_deg"] - 40) < 3
    prior = nc.CallLocaliser(elev_deg=(35,)).estimate(x, int(on * FS))
    assert prior["el_deg"] == 35.0 and abs(prior["az_deg"] - 40) < 15    # the prior bends a flat source's reading by a few degrees


def test_call_localiser_masks_the_noise_and_declines_silence():
    loc = nc.CallLocaliser()
    x = noise_floor(int(4 * FS), seed=9)
    est = loc.estimate(x, int(3.0 * FS))
    assert est is None or (est["bins"] < 200 and est["srp"] < 0.5)   # a few chance bins, no coherent peak
    assert loc.estimate(x[: int(1.5 * FS)], int(1.9 * FS)) is None    # the window after the onset was never heard


def test_call_localiser_uses_the_swapped_ears():
    sig = nc.synth_call(seed=5)
    crossed = dict(nc.CHANNELS)
    crossed["left"], crossed["right"] = crossed["right"], crossed["left"]
    x, on = nc.render_scene(sig, math.radians(50), channels=crossed, snr_db=20, seed=9, pre_s=2.6, post_s=1.0,
                            el_rad=math.radians(35))
    assert abs(nc.CallLocaliser(channels=crossed).estimate(x, int(on * FS))["az_deg"] - 50) < 4
    assert nc.CallLocaliser().estimate(x, int(on * FS))["az_deg"] < -30


def test_localiser_cost_fits_the_a7z_budget():
    """One estimate on a 3.1 s buffer: well under the 0.8 s it waits for, so the 50 Hz loop keeps up on the A7Z
    (an A76 at 2 GHz runs about a quarter of an M1 Pro core; 416 MHz throttled a fifth of that)."""
    loc = nc.CallLocaliser()
    sig = nc.synth_call(seed=1)
    x, on = nc.render_scene(sig, 0.5, pre_s=2.6, post_s=1.0, snr_db=20, seed=1, el_rad=math.radians(35))
    loc.estimate(x, int(on * FS))
    t0 = time.perf_counter()
    for _ in range(5):
        loc.estimate(x, int(on * FS))
    ms = (time.perf_counter() - t0) / 5 * 1000
    assert ms * 4 * 2000 / 416 < 800, ms


# --- the chain and the replay tool on a recording-shaped wav

def write_wav(path, x):
    with wave.open(path, "w") as w:
        w.setnchannels(4), w.setsampwidth(4), w.setframerate(FS)
        w.writeframes((np.clip(x, -1, 1) * (2 ** 23 - 1)).astype("<i4").__lshift__(8).astype("<i4").tobytes())


def test_replay_tool_scores_a_recording(tmp_path):
    x = scene([(3.0, 60), (7.0, -120), (11.0, 0)], dur=16.0)
    p = str(tmp_path / "calls.wav")
    write_wav(p, x)
    out = str(tmp_path / "replay.json")
    rec = replay_calls.main([p, "--calls", "2.6:60,6.8:-120,10.7:0", "--out", out, "--quiet"])
    s = rec["summary"]
    assert s["detected"] == 3 and s["within"] == 3 and s["side_ok"] == 2 and s["front_back_ok"] == 3
    assert s["false_triggers"] == 0 and s["false_per_min"] == 0.0
    assert all(0.7 < r["decision_after_onset_s"] < 0.95 for r in rec["calls"])
    assert all(0.15 <= r["onset_after_ear_s"] <= 0.6 for r in rec["calls"])   # the onsets were 0.2-0.4 s after the "ear" times
    saved = json.load(open(out))
    assert saved["summary"]["settings"]["localiser"] == "CallLocaliser" and saved["summary"]["settings"]["detector"] == "CallDetector"
    neg = replay_calls.main([p, "--calls", "3.0,7.0", "--exclude", "10.5-12.5", "--quiet"])["summary"]
    assert neg["detected"] == 2 and neg["false_triggers"] == 0 and neg["false_on_excluded"] == 1
