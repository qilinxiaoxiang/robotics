"""The measured bow height correction in duck_kin (u20cam_mount.json bow_height_correction) against the ruler ticks of
2026-10-30: with it, every bow tick projects to the floor within 5 mm; standing poses are untouched.

    python3 -m pytest -q test_bow_correction.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "camera-calib-20261030", "bend-20261030"))
import cam_calib  # noqa: E402
import duck_kin  # noqa: E402
import empirical_pose as ep  # noqa: E402
from test_approach import STAND  # noqa: E402

KIN = duck_kin.DuckKin()
mount_plain = dict(duck_kin.load_mount())
mount_plain.pop("bow_height_correction", None)
PLAIN = duck_kin.DuckKin(mount=mount_plain)
TICKS = [o for o in json.load(open(os.path.join(HERE, "camera-calib-20261030", "bend-20261030", "bend_ticks.json")))["obs"]
         if o.get("cm") is not None]


def floor_x_error_mm(kin, o):
    x_true = cam_calib.toe_x(kin, o["q"], o["gb"]) + o["cm"] / 100.0
    g = kin.pixel_to_ground(o["u"], o["v"], o["q"], o["gb"], 640, 360, z=ep.Z_TICK)
    return None if g is None else (g[0] - x_true) * 1000


def test_mount_carries_the_correction():
    assert KIN.bow and KIN.bow["dz_m"] < -0.008 and KIN.bow["neck_full"] <= -1.2


def test_bow_ticks_project_within_5_mm():
    bow = [o for o in TICKS if o["q"]["neck_pitch"] > -1.5]
    errs = [floor_x_error_mm(KIN, o) for o in bow]
    assert all(e is not None for e in errs)
    assert max(abs(e) for e in errs) <= 5.0, sorted(round(e, 1) for e in errs)
    plain = [abs(floor_x_error_mm(PLAIN, o)) for o in bow]
    assert max(plain) > 9.0 and np.mean(plain) > np.mean(np.abs(errs))   # the uncorrected chain was worse


def test_rise_ticks_improve():
    rise = [o for o in TICKS if o["q"]["neck_pitch"] <= -1.5]
    errs = [abs(floor_x_error_mm(KIN, o)) for o in rise]
    plain = [abs(floor_x_error_mm(PLAIN, o)) for o in rise]
    assert max(errs) <= 8.0 and max(plain) > 15.0, (max(errs), max(plain))


def test_standing_is_untouched():
    q = dict(STAND, head_pitch=0.9)
    assert KIN.bow_dz(q) == 0.0
    a = KIN.pixel_to_ground(320, 300, q, (0, 0, -1), 640, 360)
    b = PLAIN.pixel_to_ground(320, 300, q, (0, 0, -1), 640, 360)
    assert np.allclose(a, b)


def test_between_is_linear():
    q = dict(STAND, neck_pitch=-0.6)
    assert abs(KIN.bow_dz(q) - 0.5 * KIN.bow["dz_m"]) < 1e-9
