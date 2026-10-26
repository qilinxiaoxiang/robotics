"""walk_brain GETUP modes on synthetic samples: "off" keeps the 60 deg hold, "recover" runs LIMP -> POSE -> RISE ->
walk (or GAVE_UP), and the fall predictor ignores footfalls, static tilts and a robot held in the hand.

  ~/.venvs/microduck-walk/bin/python -m unittest test_getup.py
"""
import math
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
sys.path.insert(0, MAC)
sys.path.insert(0, os.path.join(MAC, "..", "pi"))
import walk_brain as wb  # noqa: E402

MODELS = os.path.join(MAC, "..", "..", "..", "hardware-design-20260912", "whole-robot-20260912", "runtime-overlay", "models")
WALK0 = {"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0}
DT = 0.02


def conj(q):
    return (q[0], -q[1], -q[2], -q[3])


def raw_imu(pitch, rate_y=0.0):
    """Raw BNO quaternion and gyro for a trunk pitched `pitch` rad forward, pitching at rate_y rad/s (body y), as
    brain_sim_check.py builds them (no IMU pitch trim in the plant)."""
    q_trunk = (math.cos(pitch / 2), 0.0, math.sin(pitch / 2), 0.0)
    trim = wb.IMU_PITCH_TRIM
    q_sensor = wb.qmul(wb.qmul(wb.qmul(q_trunk, trim), conj(wb.IMU_MOUNT_QUAT)), conj(wb.MOUNT_FIX))
    w = wb.apply_inverse(wb.IMU_PITCH_TRIM, [0.0, rate_y, 0.0])
    g = wb.apply_inverse(conj(wb.MOUNT_FIX), wb.apply_inverse(conj(wb.IMU_MOUNT_QUAT), w))
    return q_sensor, tuple(float(x) for x in g)


class Rig:
    def __init__(self, getup, pose=None):
        self.b = wb.Brain(MODELS, compensation=False, getup=getup)
        self.pose = dict(pose or self.b.default)
        self.t = 0.0

    def tick(self, want, pitch, rate=0.0, fresh=True):
        quat, gyro = raw_imu(pitch, rate)
        pos = [wb.to_tick(n, self.pose[n]) for n in wb.NAMES]
        out = self.b.tick(want, self.t, pos, [0] * 14, quat, gyro, fresh, 0.024, 0.024)
        self.t += DT
        return out


class TestGetup(unittest.TestCase):
    def test_gravity_of_the_helper(self):
        quat, _ = raw_imu(math.radians(30))
        self.assertAlmostEqual(wb.body_gravity(quat)[2], -math.cos(math.radians(30)), places=3)

    def test_off_holds_a_lying_robot(self):
        r = Rig("off")
        for _ in range(100):
            goal, kp, info = r.tick(WALK0, math.pi / 2)
            self.assertIsNone(info["action"])
            self.assertNotIn("getup", info)
        self.assertEqual(kp, wb.KP_RL)

    def test_nogate_runs_the_policy_lying(self):
        r = Rig("nogate")
        r.tick(WALK0, math.pi / 2)
        goal, kp, info = r.tick(WALK0, math.pi / 2)
        self.assertEqual(info["policy"], "stand")

    def test_recover_sequence(self):
        lying = dict(wb.STAND, left_knee=0.8, right_knee=-0.8)
        r = Rig("recover", lying)
        phases = []
        for _ in range(int(0.3 / DT)):  # lying, still
            goal, kp, info = r.tick(dict(WALK0, vx=0.3), math.pi / 2)
            phases.append(info.get("getup"))
        self.assertEqual(phases[-1], "limp")
        self.assertEqual(kp, wb.KP_LIMP)
        self.assertAlmostEqual(goal["left_knee"], 0.8, places=2)  # follows the joints
        for _ in range(int(0.3 / DT)):
            goal, kp, info = r.tick(dict(WALK0, vx=0.3), math.pi / 2)
        self.assertEqual(info["getup"], "pose")
        self.assertEqual(kp, wb.KP_POSE)
        for _ in range(int(wb.POSE_S / DT) + 2):
            goal, kp, info = r.tick(dict(WALK0, vx=0.3), math.pi / 2)
        for n in wb.NAMES:
            self.assertAlmostEqual(r.b.goal[n] if info.get("action") is None else r.b.default[n], r.b.default[n], places=6)
        goal, kp, info = r.tick(dict(WALK0, vx=0.3), math.pi / 2)
        self.assertEqual(info["getup"], "rise")
        self.assertEqual(info["policy"], "stand")  # zero command whatever the file says
        self.assertEqual(kp, wb.KP_RL)
        self.assertIsNotNone(info["action"])
        for _ in range(int(1.1 / DT)):  # upright for a second ends the rise
            goal, kp, info = r.tick(dict(WALK0, vx=0.3), 0.0)
        self.assertIsNone(r.b.getup)
        goal, kp, info = r.tick(dict(WALK0, vx=0.3), 0.0)
        self.assertEqual(info["policy"], "walk")  # the walk command in force takes over

    def test_gave_up_holds_soft_until_a_new_command(self):
        r = Rig("recover")
        r.tick(WALK0, math.pi / 2)  # enters walk mode (a mode switch clears any sequence)
        r.b.getup = {"phase": "rise", "t": r.t, "t0": r.t, "up": 0.0}
        for _ in range(int((wb.GIVEUP_S + 0.1) / DT)):
            goal, kp, info = r.tick(WALK0, math.pi / 2)
        self.assertEqual(info["getup"], "gave_up")
        self.assertEqual(kp, wb.KP_LIMP)
        held = dict(goal)
        for _ in range(50):
            goal, kp, info = r.tick(WALK0, math.pi / 2)
            self.assertEqual(goal, held)
            self.assertEqual(kp, wb.KP_LIMP)
            self.assertIsNone(info["action"])
        goal, kp, info = r.tick(dict(WALK0, vx=0.2), math.pi / 2)
        self.assertEqual(info["getup"], "rearmed")
        self.assertIsNone(r.b.getup)

    def test_predictor_false_positives(self):
        for pitch, rate in ((math.radians(8), 3.0), (math.radians(40), 0.0), (math.radians(26), 0.3),
                            (math.radians(50), -4.0)):
            r = Rig("recover")
            for _ in range(50):
                goal, kp, info = r.tick(WALK0, pitch, rate)
                self.assertIsNone(r.b.getup, (pitch, rate))

    def test_predictor_fires_on_a_fall_after_three_ticks(self):
        r = Rig("recover")
        r.tick(WALK0, 0.0)
        fired = []
        for k in range(5):
            r.tick(WALK0, 0.6, 3.0)
            fired.append(r.b.getup is not None)
        self.assertEqual(fired.index(True), 2)

    def test_held_in_hand_never_limps(self):
        r = Rig("recover")
        for _ in range(50):
            r.tick(dict(WALK0, hold={"s": 0.3, "kp": None}), 0.6, 3.0)
            self.assertIsNone(r.b.getup)

    def test_mode_switch_ends_the_sequence(self):
        r = Rig("recover")
        for _ in range(20):
            r.tick(WALK0, math.pi / 2)
        self.assertIsNotNone(r.b.getup)
        r.tick({"mode": "stand"}, math.pi / 2)
        self.assertIsNone(r.b.getup)


if __name__ == "__main__":
    unittest.main()
