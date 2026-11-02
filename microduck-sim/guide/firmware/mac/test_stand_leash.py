"""2026-11-02 (A7Z log app1102-005438, stand-leash-20261102/fall_slice.json): the duck fell on its side, the tilt stop
ramped it to STAND on the floor, the right hip and knee pressed against each other at 1.8-2.0 A for a second and the
hip servo latched a hardware error. Lying in stand mode a joint must never get more position error than StandLeash
allows, while the normal side-lying stand ramp and every upright stand keep the goals they always had.
"""
import json
import os
import struct
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "pi"))
import walk_brain as wb  # noqa: E402
import walk_wired as ww  # noqa: E402
import test_walk_wired_battery as twb  # noqa: E402
from test_battery import World  # noqa: E402

HIP = 3  # right_hip_pitch
HIP_NAME = wb.NAMES[wb.IDS.index(HIP)]
with open(os.path.join(HERE, "stand-leash-20261102", "fall_slice.json")) as fh:
    SLICE = json.load(fh)["rows"]
# a real side-lying sample of that slice; its gravity z is checked in setUp
LYING_QUAT = tuple(next(r for r in SLICE if r["gb_z"] > 0.1)["quat"])


def goals(row):
    return {i: row["goal"][k] for k, i in enumerate(wb.IDS)}


class LeashReplay(unittest.TestCase):
    """The goals the brain really sent in the fall, against the positions the servos really reached."""

    def test_the_real_stall_is_cut_to_the_leash(self):
        leash = ww.StandLeash()
        sent_err = []
        for row in SLICE:
            lying = row["gb_z"] > ww.LEASH_LYING_Z
            out = leash.apply(goals(row), row["pos"], lying, True, row["t"])
            sent_err.append((row["t"], abs(out[HIP] - row["pos"][wb.IDS.index(HIP)])))
        raw = max(abs(r["goal"][wb.IDS.index(HIP)] - r["pos"][wb.IDS.index(HIP)]) for r in SLICE if r["t"] > -1.5)
        self.assertGreater(raw, 800, "the fixture holds the failure")
        self.assertLessEqual(max(e for t, e in sent_err if t > -2.3), ww.LEASH_TICKS)

    def test_a_joint_tracking_within_the_leash_is_untouched(self):
        # the power-up ramp on the side peaked at 220 ticks of error (head pitch) in the same log
        leash = ww.StandLeash()
        goal = {i: 2048 + 220 for i in wb.IDS}
        self.assertEqual(leash.apply(goal, [2048] * 14, True, True, 0.0), goal)
        self.assertEqual(leash.engaged(), [])

    def test_upright_never_engages_and_other_modes_never_apply(self):
        leash = ww.StandLeash()
        goal = {i: 2048 + 900 for i in wb.IDS}
        self.assertEqual(leash.apply(goal, [2048] * 14, False, True, 0.0), goal)
        self.assertEqual(leash.apply(goal, [2048] * 14, True, False, 0.0), goal)

    def test_righting_the_robot_keeps_the_leash_until_the_joint_catches_up(self):
        leash = ww.StandLeash()
        goal = {i: 2048 for i in wb.IDS}
        far = [2048 + 900] + [2048] * 13
        self.assertEqual(leash.apply(goal, far, True, True, 0.0)[1], 2048 + 900 - ww.LEASH_TICKS)
        # righted by hand: no snap of the full 900 ticks at KP 400
        self.assertEqual(leash.apply(goal, far, False, True, 2.0)[1], 2048 + 900 - ww.LEASH_TICKS)
        near = [2048 + ww.LEASH_TICKS - 1] + [2048] * 13
        self.assertEqual(leash.apply(goal, near, False, True, 2.1)[1], 2048)
        self.assertEqual(leash.engaged(), [])
        self.assertEqual(leash.apply(goal, far, False, True, 2.2)[1], 2048)  # upright again: nothing latched

    def test_a_blocked_joint_drops_to_the_low_limit_and_a_moving_one_returns(self):
        leash = ww.StandLeash()
        goal = {i: 2048 for i in wb.IDS}
        far = [2048 + 900] + [2048] * 13
        for t in (0.0, ww.LEASH_BLOCKED_S - 0.1):
            self.assertEqual(leash.apply(goal, far, True, True, t)[1], 2048 + 900 - ww.LEASH_TICKS)
        self.assertEqual(leash.apply(goal, far, True, True, ww.LEASH_BLOCKED_S + 0.1)[1], 2048 + 900 - ww.LEASH_BLOCKED_TICKS)
        moved = [2048 + 900 - 2 * ww.LEASH_BLOCKED_MOVE_TICKS] + [2048] * 13
        self.assertEqual(leash.apply(goal, moved, True, True, ww.LEASH_BLOCKED_S + 0.2)[1], moved[0] - ww.LEASH_TICKS)


def pinned_hip_link(world, clock, reads):
    """The hip keeps the pinned position of the real fall whatever is written; the other servos follow at once."""
    base = twb_real_make_link(world, clock, reads)

    class PinnedHip(base):
        def sync_write(self, addr, size, values):
            if addr != ww.ADDR_GOAL:
                return super().sync_write(addr, size, values)
            if HIP in values:
                world.write(HIP, addr, size, values[HIP])
            super().sync_write(addr, size, {i: v for i, v in values.items() if i != HIP})

    return PinnedHip


twb_real_make_link = twb.make_link


class WholeLoop(unittest.TestCase):
    """walk_wired.main with the real Brain on the fake link: a stand command given lying on the side."""
    run_wired = twb.WiredBattery.run_wired

    def setUp(self):
        self.assertGreater(wb.body_gravity(LYING_QUAT)[2], ww.LEASH_LYING_Z)

    def run_stand(self, quat, end=7.0, world=None):
        w = world or World(shutdown=52, hw_err=0, volts_dv=74)
        struct.pack_into("<i", w.regs[HIP], 132, 376)
        with mock.patch.object(twb, "make_link", pinned_hip_link), mock.patch.object(twb, "UPRIGHT_SENSOR_QUAT", quat):
            text, _, _, _, last = self.run_wired(w, lambda t: 74, {"mode": "stand"}, end=end, supply="bench")
        return text, last, w

    def test_lying_with_a_pinned_hip_the_goal_stays_on_the_leash(self):
        text, last, _ = self.run_stand(LYING_QUAT)
        k = wb.IDS.index(HIP)
        rows = [ln for ln in self.log_lines if ln["mode"] == "stand" and ln.get("goal_tick")]
        self.assertTrue(rows)
        worst = max(abs(ln["goal_tick"][str(HIP)] - ln["pos_tick"][k]) for ln in rows)
        self.assertLessEqual(worst, ww.LEASH_TICKS)
        self.assertEqual(abs(last["goal_tick"][str(HIP)] - last["pos_tick"][k]), ww.LEASH_BLOCKED_TICKS)
        self.assertEqual(last["leashed"], [HIP_NAME])
        self.assertTrue(last["torque"], "the leash limits the force; torque stays on")
        self.assertIn("leash on", text)
        # the free joints still reach the stand pose: a normal stand on the side, Shawn rights it
        for i, name in zip(wb.IDS, wb.NAMES):
            if i != HIP:
                self.assertEqual(last["goal_tick"][str(i)], wb.to_tick(name, wb.STAND[name]))

    def test_upright_the_goal_is_what_the_brain_asked(self):
        _, last, _ = self.run_stand(twb.UPRIGHT_SENSOR_QUAT)
        self.assertEqual(last["goal_tick"][str(HIP)], wb.to_tick(HIP_NAME, wb.STAND[HIP_NAME]))
        self.assertEqual(last["leashed"], [])

    def test_the_log_and_the_console_name_the_error_bit(self):
        w = World(shutdown=52, hw_err=0, volts_dv=74)
        w.regs[HIP][146] = 61  # Present Temperature
        hooks = lambda d, p: [(3.0, lambda: w.regs[HIP].__setitem__(70, 0x20))]  # noqa: E731
        with mock.patch.object(twb, "make_link", pinned_hip_link):
            text, _, _, _, last = self.run_wired(w, lambda t: 74, {"mode": "stand"}, end=6.0, supply="bench", hooks=hooks)
        self.assertEqual(last["hw_faults"], [HIP_NAME])
        self.assertEqual(last["hw_bits"], {HIP_NAME: 0x20})
        self.assertIn("overload", text)
        self.assertIn("61 C", text)
        self.assertIn("torque-off", text)


if __name__ == "__main__":
    unittest.main()
