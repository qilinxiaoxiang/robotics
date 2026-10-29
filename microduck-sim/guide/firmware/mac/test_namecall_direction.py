"""namecall.py Localiser: GCC-PHAT + SRP on the head's real microphone geometry, synthetic 4-channel scenes with known
delays. Resolution numbers land in namecall-20261029/results/direction_synthetic.json when run with -s.

  pet/.venv/bin/python -m pytest microduck-sim/guide/firmware/mac/test_namecall_direction.py -q
"""
import json
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import namecall as nc  # noqa: E402

FS = nc.FS
RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "namecall-20261029", "results")


def window_at_onset(x, onset_s, loc):
    i0 = int(round((onset_s - 0.5 * nc.BLOCK / FS) * FS))
    return x[i0:i0 + loc.window]


def wrap(d):
    return (d + 180) % 360 - 180


def test_geometry_matches_the_head_cad():
    loc = nc.Localiser()
    assert abs(np.linalg.norm(loc.pos["left"] - loc.pos["right"]) - 0.077) < 1e-9     # ears 77 mm apart
    assert abs(np.linalg.norm(loc.pos["left"] - loc.pos["back"]) - 0.0948) < 5e-4     # back mic 80-95 mm from the ears
    assert 1.2 < loc.expected_resolution_deg(0.25) < 1.5      # 0.25 sample on the ear pair ahead
    assert 5.0 < loc.expected_resolution_deg(1.0) < 5.6


def test_gcc_phat_sign_positive_lag_means_a_later():
    rng = np.random.default_rng(0)
    s = rng.standard_normal(4096).astype(np.float32)
    a = np.concatenate([np.zeros(7, np.float32), s[:-7]])    # a is s delayed by 7 samples
    lags, r = nc.gcc_phat(a, s, FS, band=(100, 20000), max_lag=20)
    assert lags[int(np.argmax(r))] == 7
    assert abs(lags[0] + nc.parabolic_peak(r, int(np.argmax(r))) - 7) < 0.1


def test_fractional_delay_is_interpolated():
    rng = np.random.default_rng(1)
    s = rng.standard_normal(4096).astype(np.float32)
    S = np.fft.rfft(s)
    f = np.fft.rfftfreq(len(s), 1 / FS)
    a = np.fft.irfft(S * np.exp(-2j * math.pi * f * (3.4 / FS)), len(s)).astype(np.float32)
    lags, r = nc.gcc_phat(a, s, FS, band=(100, 20000), max_lag=20)
    assert abs(lags[0] + nc.parabolic_peak(r, int(np.argmax(r))) - 3.4) < 0.15


@pytest.mark.parametrize("snr_db", [30, 20, 10])
def test_azimuth_all_round_with_front_back(snr_db):
    loc = nc.Localiser()
    sig = nc.synth_call(seed=2)
    errs = []
    for az in range(-180, 180, 10):
        x, on = nc.render_scene(sig, math.radians(az), snr_db=snr_db, seed=az + 1000)
        est = loc.estimate(window_at_onset(x, on, loc))
        errs.append(abs(wrap(est["az_deg"] - az)))
    errs = np.array(errs)
    assert errs.max() < (4.0 if snr_db >= 20 else 8.0), errs
    assert np.mean(errs) < (1.5 if snr_db >= 20 else 3.0)
    assert (errs > 90).sum() == 0            # never the mirror image


def test_clap_and_voice_both_localise():
    loc = nc.Localiser()
    for kind in ("voice", "clap"):
        sig = nc.synth_call(seed=3, kind=kind)
        for az in (-120, -40, 0, 40, 120):
            x, on = nc.render_scene(sig, math.radians(az), snr_db=20, seed=az + 207)
            est = loc.estimate(window_at_onset(x, on, loc))
            assert abs(wrap(est["az_deg"] - az)) < 5, (kind, az, est)


def test_swapped_ears_flag_repairs_crossed_ear_wires():
    """A robot whose left ear landed on ch1: --swap-ears tells the localiser so, and the azimuth is right again."""
    sig = nc.synth_call(seed=4)
    crossed = dict(nc.CHANNELS)
    crossed["left"], crossed["right"] = crossed["right"], crossed["left"]
    x, on = nc.render_scene(sig, math.radians(50), channels=crossed, snr_db=20, seed=9)
    loc0 = nc.Localiser()
    wrong = loc0.estimate(window_at_onset(x, on, loc0))
    right = nc.Localiser(channels=crossed).estimate(window_at_onset(x, on, loc0))
    assert abs(right["az_deg"] - 50) < 4
    assert wrong["az_deg"] < -30            # without the flag the head would turn the wrong way


def test_two_ears_alone_cannot_tell_front_from_back_but_three_can():
    """The back mic's job: with ch2 silent (not fitted) the mirror is as good as the truth."""
    loc = nc.Localiser()
    sig = nc.synth_call(seed=5)
    x, on = nc.render_scene(sig, math.radians(140), snr_db=25, seed=11)
    w = window_at_onset(x, on, loc)
    assert abs(wrap(loc.estimate(w)["az_deg"] - 140)) < 4
    w2 = w.copy()
    w2[:, 2] = 0
    est = loc.estimate(w2)
    assert abs(wrap(est["az_deg"] - 140)) < 8 or abs(wrap(est["az_deg"] - 40)) < 8    # either image, ears only
    assert est["margin"] < 0.1                                                          # and it knows it cannot tell


def test_resolution_table(capsys):
    """Record the expected resolution from the real geometry: error statistics by SNR over the whole circle."""
    loc = nc.Localiser()
    sig = nc.synth_call(seed=6)
    table = {}
    for snr in (30, 20, 10, 5):
        errs, margins = [], []
        for az in range(-180, 180, 5):
            x, on = nc.render_scene(sig, math.radians(az), snr_db=snr, seed=az + 50 * snr)
            est = loc.estimate(window_at_onset(x, on, loc))
            errs.append(abs(wrap(est["az_deg"] - az)))
            margins.append(est["margin"])
        e = np.array(errs)
        table[f"snr_{snr}_db"] = dict(mean_deg=round(float(e.mean()), 2), p90_deg=round(float(np.percentile(e, 90)), 2),
                                      max_deg=round(float(e.max()), 2), mirror_errors=int((e > 90).sum()), n=len(e))
    out = dict(geometry_mm=nc.MICS_MM, channels=nc.CHANNELS, fs=FS, window_samples=loc.window, band_hz=nc.BAND,
               ear_pair_resolution_deg_per_0p25_sample=round(loc.expected_resolution_deg(0.25), 2),
               ear_pair_resolution_deg_per_sample=round(loc.expected_resolution_deg(1.0), 2),
               synthetic_far_field=table, note="free field, no head shadow, no echo; the robot adds both")
    os.makedirs(RESULTS, exist_ok=True)
    json.dump(out, open(os.path.join(RESULTS, "direction_synthetic.json"), "w"), indent=1)
    with capsys.disabled():
        print("\ndirection:", json.dumps(table))
    assert table["snr_20_db"]["max_deg"] < 4 and table["snr_20_db"]["mirror_errors"] == 0
