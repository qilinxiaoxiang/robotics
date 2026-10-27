"""The seeing-pick guards from the 2026-10-27 sim rehearsal: jaw_ctl.holding needs a still jaw, and walk_wired refuses
the switch to seepick without the jaw marks or an object.

    python3 -m pytest -q test_seepick_guards.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jaw_ctl  # noqa: E402
import walk_wired as ww  # noqa: E402


def jaw():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "jaw_calibration.json")
    json.dump({"closed_tick": 2042, "open_tick": 2442}, open(path, "w"))
    j = jaw_ctl.JawCtl(path)
    j.goal_deg = "grip"
    return j


def tick_at(j, deg):
    return min(range(1800, 2700), key=lambda t: abs(j.opening_deg(t) - deg))


def test_a_still_jaw_on_an_object_is_holding():
    j = jaw()
    for _ in range(3):
        j.last_tick = tick_at(j, 10.0)
    assert j.holding()


def test_a_jaw_sweeping_shut_is_not_holding():
    j = jaw()
    for deg in (12.0, 9.0, 6.0):  # 3 deg per read: closing on nothing, still above GRIP_MIN_DEG
        j.last_tick = tick_at(j, deg)
    assert not j.holding()


def test_holding_needs_three_reads_and_a_grip():
    j = jaw()
    j.last_tick = tick_at(j, 10.0)
    j.last_tick = tick_at(j, 10.0)
    assert not j.holding()
    j.last_tick = tick_at(j, 10.0)
    j.goal_deg = 2.0
    assert not j.holding()


def test_closed_on_nothing_is_not_holding():
    j = jaw()
    for _ in range(3):
        j.last_tick = tick_at(j, 0.5)
    assert not j.holding()


def test_seepick_needs_the_jaw_marks_and_an_object():
    obj = {"mode": "seepick", "object": {"x": 0.09, "y": 0.0, "size": 0.013, "t": 1.0}}
    assert ww.seepick_block(obj, True) is None
    assert "not calibrated" in ww.seepick_block(obj, False)
    assert "object" in ww.seepick_block({"mode": "seepick"}, True)
    assert "object" in ww.seepick_block({"mode": "seepick", "object": {"x": 0.09}}, True)
