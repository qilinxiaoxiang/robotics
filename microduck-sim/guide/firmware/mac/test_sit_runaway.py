"""2026-10-23 (A7Z log app1023-204119, robot-runs-20261023-a7z/sit-headbump/findings.md): a sitstand61 rise ran away
(neck action -0.3 -> -3.75 rad), the hard action limit sent two ticks clipped to -3.0 rad, and the trip held that goal
at full gain: the neck reached -2.5 rad and pressed the head into the floor. Policy goals must stay within the trained
joint ranges, and after a sit trip the head must hold where it is while the legs keep their goals.
"""
import os
import re
import sys
import unittest
from unittest import mock

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "pi"))
import walk_brain as wb  # noqa: E402
import walk_wired as ww  # noqa: E402
import struct  # noqa: E402
import test_walk_wired_battery as twb  # noqa: E402
from test_walk_wired_battery import make_link as make_link_for  # noqa: E402
from test_teleop_modes import write_cmd  # noqa: E402
from test_battery import World  # noqa: E402

MJCF = os.path.join(HERE, "..", "..", "..", "microduck-rl-contribution", "src", "mjlab_microduck", "robot", "microduck",
                    "robot_groundcontact.xml")
NECK = wb.OBSERVATION_DOF_ORDER.index("neck_pitch")
NECK_ID = wb.IDS[wb.NAMES.index("neck_pitch")]
LIMITS_ON = ("--max-action", "1e9", "--max-walk-action", "1e9")  # the hard action limit stays at its 3.0 rad default


class RunawayNeck:
    """sitstand61 stand-in: zero action except the neck, which asks for `neck` rad."""

    def __init__(self, real, neck):
        self.real, self.neck = real, neck

    def get_inputs(self):
        return self.real.get_inputs()

    def get_modelmeta(self):
        return self.real.get_modelmeta()

    def run(self, outputs, feeds):
        a = np.zeros(14, dtype=np.float32)
        a[NECK] = self.neck
        return [a[None]]


NECK_STEP = 40  # ticks per write (2.9 rad/s at 50 Hz): the fake neck lags its goal, as the robot's did


def slow_neck_link(world, clock, reads):
    base = make_link_for(world, clock, reads)

    class SlowNeck(base):
        def sync_write(self, addr, size, values):
            super().sync_write(addr, size, {i: v for i, v in values.items() if not (addr == ww.ADDR_GOAL and i == NECK_ID)})
            if addr == ww.ADDR_GOAL and NECK_ID in values:
                world.write(NECK_ID, addr, size, values[NECK_ID])
                pos = struct.unpack_from("<i", world.regs[NECK_ID], 132)[0]
                step = max(-NECK_STEP, min(NECK_STEP, int(values[NECK_ID]) - pos))
                struct.pack_into("<i", world.regs[NECK_ID], 132, pos + step)

    return SlowNeck


def brain_with_neck(neck):
    class NeckBrain(wb.Brain):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.sessions["sitstand"] = RunawayNeck(self.sessions["sitstand"], neck)

    return NeckBrain


class SitRunaway(unittest.TestCase):
    run_wired = twb.WiredBattery.run_wired

    def sit_run(self, neck, end):
        w = World(shutdown=52, hw_err=0, volts_dv=74)
        hooks = lambda d, p: [(1.0, write_cmd(p, {"mode": "sit"}))]  # noqa: E731
        with mock.patch.object(ww, "Brain", brain_with_neck(neck)), mock.patch.object(twb, "make_link", slow_neck_link):
            text, marker, wants, reads, last_log = self.run_wired(w, lambda t: 74, {"mode": "stand"}, end=end,
                                                                  supply="bench", hooks=hooks, extra_args=LIMITS_ON)
        return text, last_log

    def neck_goals(self):
        return [wb.to_model("neck_pitch", ln["goal_tick"][str(NECK_ID)]) for ln in self.log_lines if ln.get("goal_tick")]

    def test_joint_range_is_the_mjcf_hinge_range(self):
        with open(MJCF) as fh:
            xml = fh.read()
        for name, (lo, hi) in wb.JOINT_RANGE.items():
            m = re.search(r'<joint[^>]*name="%s"[^>]*range="([^"]+)"' % name, xml) or \
                re.search(r'<joint[^>]*range="([^"]+)"[^>]*name="%s"' % name, xml)
            self.assertIsNotNone(m, name)
            mlo, mhi = (float(v) for v in m.group(1).split())
            self.assertAlmostEqual(lo, mlo, places=3, msg=name)
            self.assertAlmostEqual(hi, mhi, places=3, msg=name)
        self.assertEqual(set(wb.JOINT_RANGE), set(wb.NAMES))
        for n in wb.NAMES:  # the stand pose and the policy default are inside the ranges
            self.assertTrue(wb.JOINT_RANGE[n][0] <= wb.STAND[n] <= wb.JOINT_RANGE[n][1], n)

    def test_a_goal_past_the_range_is_clamped_without_a_trip(self):
        text, last_log = self.sit_run(-2.5, end=3.0)  # under the 3.0 rad hard limit: 0.349 - 2.5 = -2.15 rad asked
        self.assertNotIn("STOP", text)
        self.assertEqual(last_log["mode"], "sit")
        lo = wb.JOINT_RANGE["neck_pitch"][0]
        goals = self.neck_goals()
        self.assertGreaterEqual(min(goals), lo - 0.003)  # one servo tick is 0.0015 rad
        self.assertLess(min(goals), lo + 0.003)

    def test_a_sit_trip_holds_the_head_where_it_is_and_the_legs_on_their_goals(self):
        text, last_log = self.sit_run(-3.75, end=4.0)  # the 10/23 runaway's last action
        self.assertIn("STOP -> hold the last goals: sit: policy action over 3.0 rad", text)
        self.assertEqual(last_log["mode"], "monitor")
        self.assertTrue(last_log["torque"])
        self.assertGreaterEqual(min(self.neck_goals()), wb.JOINT_RANGE["neck_pitch"][0] - 0.003)  # never -2.65 rad
        trip = next(k for k, ln in enumerate(self.log_lines) if ln["mode"] == "monitor" and k > 0
                    and self.log_lines[k - 1]["mode"] == "sit")
        held = self.log_lines[trip - 1]["goal_tick"]  # the goals sent on the tripping tick
        end = last_log["goal_tick"]
        for i, n in zip(wb.IDS, wb.NAMES):
            if n in wb.HEAD_JOINTS:  # the measured position at the trip (one tick old), not the runaway goal
                self.assertLessEqual(abs(end[str(i)] - self.log_lines[trip - 1]["pos_tick"][i - 1]), 70, n)
            else:
                self.assertEqual(end[str(i)], held[str(i)], n)
        self.assertNotEqual(end[str(NECK_ID)], held[str(NECK_ID)])  # the neck no longer drives to the runaway goal

if __name__ == "__main__":
    unittest.main()
