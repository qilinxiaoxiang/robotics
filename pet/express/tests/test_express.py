import math
import os
import re

import numpy as np
import pytest

from pet.express import Affect, Expressor, Target, acknowledge, attend, content_idle, greet, startle
from pet.express.channels import CardError, load_card, map_trajectory, matrix, present_axes, validate
from pet.express.duck import HEAD_ALPHA, HEAD_JOINTS, HEAD_RANGE, ema, ema_preinverse, head_deltas
from pet.express.idle import Perlin1D
from pet.express.spring import overshoot_fraction, step_metrics, track, wn_zeta_from_effort
from pet.express.intents import effort_for
from pet.express.takes import SOCIAL_TAKES, Context, Habituation, choose_take, plan, selection_weights
from pet.express.voice import CallPicker, ola_stretch, render_call, resample

HERE = os.path.dirname(os.path.abspath(__file__))
CARDS = os.path.join(HERE, "..", "cards")
WALK_BRAIN = os.path.join(HERE, "..", "..", "..", "microduck-sim", "guide", "firmware", "mac", "walk_brain.py")
DT = 0.02


def card(name):
    return load_card(os.path.join(CARDS, name + ".json"))


# spring controller

@pytest.mark.parametrize("zeta", [0.3, 0.5, 0.7])
def test_underdamped_overshoot_matches_analytic(zeta):
    ref = np.r_[np.zeros(5), np.ones(300)]
    x = track(ref, DT, wn=8.0, zeta=zeta)
    over = x.max() - 1.0
    assert over == pytest.approx(overshoot_fraction(zeta), abs=0.02)


@pytest.mark.parametrize("zeta", [1.0, 1.2])
def test_overdamped_never_overshoots_and_settles(zeta):
    ref = np.r_[np.zeros(5), np.ones(400)]
    x = track(ref, DT, wn=5.0, zeta=zeta)
    assert x.max() <= 1.0 + 1e-6
    assert abs(x[-1] - 1.0) < 1e-3


def test_stiffer_spring_arrives_sooner():
    ref = np.r_[np.zeros(5), np.ones(200)]
    t = np.arange(len(ref)) * DT
    fast = step_metrics(t, track(ref, DT, 14.0, 0.7), 0.0, 1.0, 5 * DT)
    slow = step_metrics(t, track(ref, DT, 4.0, 0.7), 0.0, 1.0, 5 * DT)
    assert fast["arrival"] < slow["arrival"]


def test_rate_limit_is_respected():
    ref = np.r_[np.zeros(5), np.ones(200)]
    x = track(ref, DT, 20.0, 0.5, max_rate=2.0)
    assert np.abs(np.diff(x)).max() <= 2.0 * DT + 1e-9


def test_affect_sets_eager_vs_sleepy_dynamics():
    eager = acknowledge(Target(1, 0), warmth=0.9, energy=0.9, affect=Affect(0.8, 0.9))
    sleepy = acknowledge(Target(1, 0), warmth=0.5, energy=0.3, affect=Affect(0.1, 0.1))
    we, ze = wn_zeta_from_effort(effort_for(eager), 0.9)
    ws, zs = wn_zeta_from_effort(effort_for(sleepy), 0.1)
    assert we > ws and ze < 0.7 < zs
    assert overshoot_fraction(ze) > 0.05


# takes: selection, no repeat, jitter, anticipation, habituation

def test_no_immediate_repeat_over_many_choices():
    rng = np.random.default_rng(0)
    intent = acknowledge(Target(0.8, 0.2), 0.8, 0.7, Affect(0.6, 0.6))
    last, seen = None, set()
    for _ in range(500):
        take = choose_take(intent, Context(novelty=float(rng.uniform(0.1, 1.0))), rng, last)
        assert take != last
        seen.add(take)
        last = take
    assert seen == set(SOCIAL_TAKES)


def test_context_steers_selection():
    awake = acknowledge(Target(0.8, 0.2), 0.8, 0.7, Affect(0.6, 0.8))
    sleepy = acknowledge(Target(0.8, 0.2), 0.8, 0.4, Affect(0.2, 0.05))
    assert max(selection_weights(sleepy, Context()), key=selection_weights(sleepy, Context()).get) == "groggy"
    fresh, tired = selection_weights(awake, Context(novelty=1.0)), selection_weights(awake, Context(novelty=0.15))
    assert fresh["quick_snap"] > fresh["glance"] and tired["glance"] > tired["quick_snap"]
    assert selection_weights(awake, Context(distracted=True))["double_take"] > selection_weights(awake, Context())["double_take"]


def test_startle_always_startles():
    assert choose_take(startle(Target(1.0, 0)), Context(), np.random.default_rng(0), "startle") == "startle"


def test_same_take_twice_is_never_identical():
    rng = np.random.default_rng(3)
    intent = acknowledge(Target(0.9, 0.2), 0.8, 0.7, Affect(0.6, 0.6))
    for take in SOCIAL_TAKES:
        a1, _, p1, _ = plan(take, intent, Context(), rng)
        a2, _, p2, _ = plan(take, intent, Context(), rng)
        assert p1["latency"] != p2["latency"]
        assert np.abs(a1["ATTEND.yaw"][:min(len(a1["ATTEND.yaw"]), len(a2["ATTEND.yaw"]))]
                      - a2["ATTEND.yaw"][:min(len(a1["ATTEND.yaw"]), len(a2["ATTEND.yaw"]))]).max() > 1e-3


def test_anticipation_moves_away_first_and_eager_snap_overshoots():
    rng = np.random.default_rng(5)
    intent = acknowledge(Target(1.0, 0.2), 0.9, 0.9, Affect(0.8, 0.9))
    axes, events, p, arrival = plan("quick_snap", intent, Context(), rng)
    yaw = axes["ATTEND.yaw"]
    assert yaw.min() < -0.01                      # counter-move before the turn
    assert int(np.argmin(yaw)) * DT < arrival      # ... and it comes first
    assert yaw.max() > 1.0                         # eager spring overshoots the target
    assert abs(yaw[-1] - 1.0) < 0.05               # and settles on it
    assert events and abs(events[0]["t"] - arrival) < 0.2   # the call lands with the head


def test_groggy_is_late_slow_and_low():
    rng = np.random.default_rng(1)
    intent = acknowledge(Target(1.0, 0.2), 0.6, 0.4, Affect(0.2, 0.1))
    _, ev_g, pg, arr_g = plan("groggy", intent, Context(), rng)
    axes, _, _, arr_s = plan("quick_snap", intent, Context(), rng)
    assert arr_g > arr_s + 0.4
    if ev_g:
        assert ev_g[0]["pitch"] < 1.0 and ev_g[0]["stretch"] > 1.0


def test_double_take_looks_twice():
    rng = np.random.default_rng(2)
    axes, _, _, _ = plan("double_take", acknowledge(Target(1.0, 0.0), 0.8, 0.8, Affect(0.6, 0.7)), Context(), rng)
    yaw = axes["ATTEND.yaw"]
    peaks = np.flatnonzero((yaw[1:-1] > yaw[:-2]) & (yaw[1:-1] >= yaw[2:]) & (yaw[1:-1] > 0.15))
    assert len(peaks) >= 2


def test_habituation_drops_and_recovers():
    h = Habituation()
    first = h.on_call(0.0)
    vals = [h.on_call(t) for t in (2.0, 4.0, 6.0, 8.0)]
    assert first == 1.0 and all(b < a for a, b in zip([first] + vals, vals))
    later = h.on_call(300.0)
    assert later > 0.95


def test_repeated_calls_get_smaller_answers():
    ex = Expressor(card("duck"), seed=11)
    sched = [(0.5 + 2.0 * i, acknowledge(Target(0.9, 0.2), 0.8, 0.7, Affect(0.6, 0.6))) for i in range(8)]
    for i in range(8):
        sched.append((0.5 + 2.0 * i + 1.5, content_idle(affect=Affect(0.5, 0.4))))
    tl = ex.run(sched, 17.0)
    nov = [h["novelty"] for h in tl["takes"]]
    assert nov == sorted(nov, reverse=True) and nov[-1] < 0.3
    assert tl["takes"][-1]["params"]["energy"] < tl["takes"][0]["params"]["energy"]
    takes = [h["take"] for h in tl["takes"]]
    assert all(a != b for a, b in zip(takes, takes[1:]))


def test_attend_never_vocalises_and_greet_calls_twice():
    rng = np.random.default_rng(4)
    for take in ("quick_snap", "curious_turn"):
        assert plan(take, attend(Target(0.5, 0.0)), Context(), rng)[1] == []
    _, ev, _, _ = plan("quick_snap", greet(Target(0.5, 0.2)), Context(), rng)
    assert len(ev) == 2 and ev[1]["t"] > ev[0]["t"]


def test_idle_is_smooth_and_alive():
    p = Perlin1D(0)
    x = np.linspace(0, 20, 2001)
    y = p.fbm(x)
    assert np.abs(np.diff(y)).max() < 0.05 and y.std() > 0.05
    ex = Expressor(card("duck"), seed=0)
    tl = ex.run([(0.0, content_idle(affect=Affect(0.5, 0.4)))], 10.0)
    assert tl["outputs"]["head_yaw"].std() > 0.005


# channel mapping for the three cards

def test_three_cards_validate_and_declare_their_channels():
    duck, arm, vac = card("duck"), card("omx_arm"), card("vacuum")
    assert "ATTEND.pitch" in present_axes(duck) and "ATTEND.pitch" in present_axes(arm)
    assert "ATTEND.pitch" not in present_axes(vac)
    assert duck["channels"]["VOCALISE"]["render"] == "call"
    assert arm["channels"]["VOCALISE"]["render"] == "clack"
    assert vac["channels"]["VOCALISE"]["render"] == "beep"


def test_mapping_routes_axes_to_the_right_parts():
    def out(c, **ax):
        outs, M = matrix(c)
        from pet.express.takes import AXES
        x = np.array([ax.get(a.replace(".", "_"), 0.0) for a in AXES])
        return dict(zip(outs, M @ x))
    d = out(card("duck"), ATTEND_yaw=0.5)
    assert d["head_yaw"] == pytest.approx(0.5) and d["body_heading"] == 0
    d = out(card("duck"), ATTEND_yaw=0.5, ORIENT_yaw=0.5)
    assert d["head_yaw"] == pytest.approx(0.0) and d["body_heading"] == pytest.approx(0.5)  # gaze held while body turns
    a = out(card("omx_arm"), ATTEND_yaw=1.0, ORIENT_yaw=1.0)
    assert a["base"] == pytest.approx(1.0)        # glance + orient = full turn on the base
    assert out(card("omx_arm"), GESTURE_tilt=0.2)["wrist_roll"] != 0
    v = out(card("vacuum"), ATTEND_yaw=1.0, ORIENT_yaw=1.0, POSTURE_height=-0.5)
    assert v["heading"] == pytest.approx(1.0) and v["drive"] < 0   # the dip is a back-up


def test_limits_hold_and_vocal_renders_per_body():
    n = 150
    axes = {a: np.zeros(n) for a in ("ATTEND.yaw", "ATTEND.pitch", "ORIENT.yaw", "POSTURE.height", "GESTURE.tilt", "GESTURE.bob")}
    axes["ATTEND.yaw"][:] = 5.0
    axes["GESTURE.tilt"][:] = 2.0
    ev = [dict(t=1.0, kind="call", pitch=1.2, stretch=1.0, gain_db=0.0)]
    for name in ("duck", "omx_arm", "vacuum"):
        c = card(name)
        res, dev = map_trajectory(c, axes, DT, ev)
        for o, y in res.items():
            lo, hi = c["channels"]["outputs"][o]["limit"]
            assert y.min() >= lo - 1e-9 and y.max() <= hi + 1e-9
        assert len(dev) == 1
    _, dev = map_trajectory(card("vacuum"), axes, DT, ev)
    assert dev[0]["kind"] == "beep" and dev[0]["hz"] == round(1400 * 1.2)
    res, dev = map_trajectory(card("omx_arm"), {a: np.zeros(n) for a in axes}, DT, ev)
    assert dev[0]["kind"] == "clack" and res["gripper"].max() > 0.2


def test_validator_rejects_unknown_output():
    bad = card("vacuum")
    bad["channels"]["ATTEND"]["map"].append({"axis": "pitch", "to": "neck", "gain": 1.0})
    with pytest.raises(CardError):
        validate(bad)


def test_same_intent_on_three_bodies():
    intent = acknowledge(Target(0.9, 0.2), 0.8, 0.7, Affect(0.6, 0.6))
    for name, gaze in (("duck", "head_yaw"), ("omx_arm", "base"), ("vacuum", "heading")):
        tl = Expressor(card(name), seed=5).run([(0.3, intent, "quick_snap")], 3.0)
        assert tl["takes"][0]["take"] == "quick_snap"
        assert tl["outputs"][gaze][-1] > 0.5     # every body ends up facing the caller
        assert tl["events"]                       # and answers


# duck adapter: walk_brain's head path

def test_duck_constants_match_walk_brain():
    src = open(WALK_BRAIN).read()
    assert f"HEAD_JOINTS = {HEAD_JOINTS!r}" in src.replace('"', "'") or \
        'HEAD_JOINTS = ("neck_pitch", "head_pitch", "head_yaw", "head_roll")' in src
    assert re.search(r"^HEAD_RANGE = \(1\.10, 1\.10, 1\.40, 0\.31\)", src, re.M)
    assert re.search(rf"^HEAD_ALPHA = {HEAD_ALPHA}$", src, re.M)
    ch = card("duck")["channels"]["outputs"]
    for j, r in zip(HEAD_JOINTS, HEAD_RANGE):
        assert -r <= ch[j]["limit"][0] and ch[j]["limit"][1] <= r


def test_ema_preinverse_reproduces_the_wanted_trajectory():
    ex = Expressor(card("duck"), seed=2)
    tl = ex.run([(0.3, acknowledge(Target(1.0, 0.25), 0.9, 0.9, Affect(0.8, 0.9)), "quick_snap")], 3.0)
    y = head_deltas(tl["outputs"])
    r, c = ema_preinverse(y)
    assert np.abs(r).max(axis=0).tolist() <= list(HEAD_RANGE)
    err = np.abs(ema(r) - y).max(axis=1)
    assert np.median(err) < 1e-9 and err.max() < 0.05   # exact except a few ticks where a snap saturates HEAD_RANGE
    assert np.abs(ema(y) - y).max() > 0.05     # sending y itself would be smoothed away


# voice

def test_call_pitch_and_length_by_resampling():
    rate = 44100
    t = np.arange(int(0.3 * rate)) / rate
    x = np.sin(2 * math.pi * 700 * t) * np.hanning(len(t))
    for pitch, stretch in ((1.25, 1.0), (0.85, 1.4)):
        y = render_call(x, pitch, stretch)
        assert len(y) == pytest.approx(len(x) * stretch, rel=0.08)
        f = np.fft.rfftfreq(len(y), 1 / rate)[np.argmax(np.abs(np.fft.rfft(y)))]
        assert f == pytest.approx(700 * pitch, rel=0.04)
    assert len(resample(x, 2.0)) == pytest.approx(len(x) / 2, rel=0.01)
    assert len(ola_stretch(x, 1.5)) == pytest.approx(len(x) * 1.5, rel=0.08)


def test_call_picker_never_repeats():
    p = CallPicker(["a", "b", "c"], np.random.default_rng(0))
    picks = [p.pick() for _ in range(100)]
    assert all(a != b for a, b in zip(picks, picks[1:]))
