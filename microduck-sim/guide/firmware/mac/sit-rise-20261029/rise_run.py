"""Run brain_sim_check.py (or another harness in guide/firmware/mac) with one sit-rise condition changed, without
editing walk_brain.py. Study tool for sit-rise-20261029/README.md.

  python rise_run.py [options] -- brain_sim_check.py --model asbuilt --sit-at 4 --unsit-at 10 ...
    --unsit-s S        walk_brain.UNSIT_S, the rise timer of walk_brain.py up to e4a92b4 (2.0 s); the evidence hand-over
                       that replaced it has no such constant, so this option does nothing on the current file
    --rise-kp K        servo gain while the sitstand policy rises (robotd: standing gain 0.8 x 200 = 160)
    --sit-lowpass A    robotd's leg target low-pass t = A t + (1 - A) prev on every sit-mode tick (robotd default 0.7;
                       the head 0.5 rides along with --head-lowpass)
    --head-lowpass A
    --to-stand         after a sit, a walk command becomes {"mode": "stand"} (the open-loop ramp), the runner's
                       second stand-up route
    --stand-after S    after the rise hands over to stand61, the walk command becomes {"mode": "stand"} S s later
                       (the open-loop stand reached through stand61, as robotd reaches every pose through velstand)
    --stand-at T       every walk command from T s on becomes {"mode": "stand"}: the stand61 -> stand switch without a
                       sit (control for --stand-after)
    --neck V           stand_pose.STAND_POSE["neck_pitch"] (D-030 0.25, NEUTRAL 0.35)
    --attr MOD.NAME=V  any other module constant (json value), e.g. walk_brain.SIT_KNEE_MIN=0.6
"""
import argparse
import json
import os
import runpy
import sys

MAC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, MAC)
os.chdir(MAC)

argv = sys.argv[1:]
cut = argv.index("--") if "--" in argv else len(argv)
ap = argparse.ArgumentParser()
ap.add_argument("--unsit-s", type=float, default=None)
ap.add_argument("--rise-kp", type=int, default=None)
ap.add_argument("--sit-lowpass", type=float, default=None)
ap.add_argument("--head-lowpass", type=float, default=None)
ap.add_argument("--to-stand", action="store_true")
ap.add_argument("--stand-after", type=float, default=None,
                help="s; after the rise hands over to stand61, switch to {'mode': 'stand'} this long after")
ap.add_argument("--stand-at", type=float, default=None,
                help="s from the first tick; every walk command from then on becomes {'mode': 'stand'} (no sit needed)")
ap.add_argument("--neck", type=float, default=None)
ap.add_argument("--attr", action="append", default=[])
ap.add_argument("--stale-bvh", action="store_true",
                help="skip evaluate_delay.load's body-BVH refit (the plant before 2026-10-29, and fake_pi's evaluate.load)")
a = ap.parse_args(argv[:cut])
harness = argv[cut + 1:]

import walk_brain  # noqa: E402

if a.stale_bvh:
    sys.path.insert(0, os.path.join(MAC, "..", "..", "..", "hardware-design-20260912", "whole-robot-20260912",
                                    "delay-repair-20260912"))
    import evaluate_delay  # noqa: E402
    evaluate_delay.refit_body_bvh = lambda m: {}

sys.path.insert(0, os.path.join(MAC, "..", "pi"))
import stand_pose  # noqa: E402

if a.unsit_s is not None:
    walk_brain.UNSIT_S = a.unsit_s
if a.neck is not None:
    stand_pose.STAND_POSE["neck_pitch"] = a.neck
for spec in a.attr:
    key, val = spec.split("=", 1)
    mod, name = key.split(".", 1)
    setattr(sys.modules[mod], name, json.loads(val))

HEAD = {"neck_pitch", "head_pitch", "head_yaw", "head_roll"}
_tick = walk_brain.Brain.tick


def tick(self, want, now, *rest):
    if a.to_stand and getattr(self, "_rr_sat", False) and isinstance(want, dict) and want.get("mode") == "walk":
        want = {"mode": "stand"}
    t0 = getattr(self, "_rr_t0", None)
    if t0 is None:
        self._rr_t0 = t0 = now
    if a.stand_at is not None and now - t0 >= a.stand_at and isinstance(want, dict) and want.get("mode") == "walk":
        want = {"mode": "stand"}  # no sit: the stand61 -> open-loop stand switch on its own
    if a.stand_after is not None and getattr(self, "_rr_sat", False) and self.mode in ("walk", "stand"):
        t_up = getattr(self, "_rr_up", None)
        if t_up is None:
            self._rr_up = t_up = now
        if now - t_up >= a.stand_after and isinstance(want, dict) and want.get("mode") == "walk":
            want = {"mode": "stand"}  # latched: every later walk command stays a stand
    goal, kp, info = _tick(self, want, now, *rest)
    if self.mode == "sit":
        self._rr_sat = True
    in_sit = self.mode == "sit" and self.sit is not None and goal is not None
    if in_sit and a.rise_kp is not None and self.sit["phase"] == "rise":
        kp = a.rise_kp
    if in_sit and (a.sit_lowpass is not None or a.head_lowpass is not None):
        prev = getattr(self, "_rr_prev", None)
        if prev is not None:
            goal = dict(goal)
            for n, v in goal.items():
                alpha = a.head_lowpass if n in HEAD else a.sit_lowpass
                if alpha is not None and n in prev:
                    goal[n] = alpha * v + (1.0 - alpha) * prev[n]
            self.goal = dict(goal)
        self._rr_prev = dict(goal)
    elif not in_sit:
        self._rr_prev = None
    return goal, kp, info


walk_brain.Brain.tick = tick
sys.argv = harness
runpy.run_path(harness[0], run_name="__main__")
