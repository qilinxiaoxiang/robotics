"""Straight-walk heading hold in walk_brain.Brain: the yaw trim is learned from plain forward walks only, kept in its file
and read back by the next Brain, and every turn command stays within walk61's trained range. brain_sim_check.py
--yaw-torque checks the same logic in the as-built model.

  ~/.venvs/microduck-walk/bin/python -m unittest test_yaw_trim -v
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "pi"))
import walk_brain as wb  # noqa: E402

MODELS = os.path.join(wb.WHOLE, "runtime-overlay", "models")


class YawTrimTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "yaw_trim.json")

    def tearDown(self):
        self.dir.cleanup()

    def seg(self, mean, secs=2.0, manual=False):
        n = int(secs / 0.02)
        return {"t0": 0.0, "t": secs, "sum": mean * n, "n": n, "manual": manual}

    def test_learns_from_forward_walks_and_keeps_it(self):
        b = wb.Brain(MODELS, yaw_trim_file=self.path)
        self.assertEqual(b.yaw_trim, 0.0)
        b.learn_yaw_trim(self.seg(-0.8))
        self.assertAlmostEqual(b.yaw_trim, -0.4)
        with open(self.path) as f:
            self.assertAlmostEqual(json.load(f)["yaw_trim"], -0.4)
        self.assertAlmostEqual(wb.Brain(MODELS, yaw_trim_file=self.path).yaw_trim, -0.4)

    def test_ignores_manual_turns_and_short_walks(self):
        b = wb.Brain(MODELS, yaw_trim_file=self.path)
        b.learn_yaw_trim(self.seg(-0.8, manual=True))
        b.learn_yaw_trim(self.seg(-0.8, secs=0.5))
        self.assertEqual(b.yaw_trim, 0.0)
        self.assertFalse(os.path.exists(self.path))

    def test_trim_and_file_stay_in_trained_range(self):
        with open(self.path, "w") as f:
            json.dump({"yaw_trim": -3.0}, f)
        self.assertEqual(wb.load_yaw_trim(self.path), -wb.TURN_MAX)
        self.assertEqual(wb.load_yaw_trim(os.path.join(self.dir.name, "missing.json")), 0.0)
        self.assertEqual(wb.load_yaw_trim(None), 0.0)


if __name__ == "__main__":
    unittest.main()
