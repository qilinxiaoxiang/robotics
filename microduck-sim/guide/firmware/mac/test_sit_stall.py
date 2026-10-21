"""2026-10-21 (A7Z log app1021-040436, robot-runs-20261021-a7z/README.md): a sit whose leg servos never move. The fake
link turns goals into present positions at once for the head only; the ten leg servos (IDs 1-10) start at the stand pose
and keep it whatever is written, as the robot's loaded legs did (knees 0.02 / -0.03 rad through 53 s of "seated").
The Brain must report the stall instead of declaring a seat by its timer alone.
"""
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
from test_walk_wired_battery import make_link as make_link_for  # noqa: E402
from test_teleop_modes import WALK0, write_cmd  # noqa: E402
from test_battery import World  # noqa: E402

LEG_IDS = set(range(1, 11))


def stuck_legs_link(world, clock, reads):
    base = make_link_for(world, clock, reads)

    class StuckLegs(base):
        def sync_write(self, addr, size, values):
            if addr != ww.ADDR_GOAL:
                return super().sync_write(addr, size, values)
            for i, v in values.items():
                if i in LEG_IDS:
                    world.write(i, addr, size, v)  # the goal is written; the present position does not follow
            super().sync_write(addr, size, {i: v for i, v in values.items() if i not in LEG_IDS})

    return StuckLegs


class SitStall(unittest.TestCase):
    run_wired = twb.WiredBattery.run_wired  # the fake-link harness of test_walk_wired_battery / test_teleop_modes

    def test_a_seat_the_legs_never_took_is_reported_as_a_stall(self):
        w = World(shutdown=52, hw_err=0, volts_dv=74)
        for i, name in zip(wb.IDS, wb.NAMES):  # legs at the stand pose (the fake world starts every servo at 2048)
            if i in LEG_IDS:
                struct.pack_into("<i", w.regs[i], 132, wb.to_tick(name, wb.STAND[name]))
        hooks = lambda d, p: [(1.0, write_cmd(p, {"mode": "sit"}))]  # noqa: E731
        with mock.patch.object(twb, "make_link", stuck_legs_link):
            text, marker, wants, reads, last_log = self.run_wired(w, lambda t: 74, WALK0, end=5.5, supply="bench",
                                                                  hooks=hooks)
        seated = [ln for ln in self.log_lines if ln.get("sit_phase") == "seated"]
        self.assertTrue(seated, "the timer still declares the seat")
        kl, kr = wb.NAMES.index("left_knee"), wb.NAMES.index("right_knee")
        knees = [abs(ln["q"][kl]) for ln in seated] + [abs(ln["q"][kr]) for ln in seated]
        self.assertLess(max(knees), 0.3, "the legs never moved in this world")
        self.assertIn("sit: STALLED", text)  # tonight's log had no such line: the stall went unreported
        self.assertTrue(all(ln.get("sit_stalled") is True for ln in seated))
        self.assertEqual(last_log["mode"], "sit")  # the policy keeps balancing; a stand/walk command stands it up
        self.assertTrue(last_log["torque"])


if __name__ == "__main__":
    unittest.main()
