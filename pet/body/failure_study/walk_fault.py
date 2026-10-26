"""One walk61 run in the as-built MuJoCo duck with one joint failed, on the unchanged brain_sim_check.py plant.

brain_sim_check.run() is used as it is (walk_brain.Brain, BAM XL330 actuators, sensor and action delay one tick,
dropped servo reads, walk_wired.py's walk-mode guards). Two things are patched in from outside:

- frozen: the joint is locked at its stand angle (walk_brain.STAND) by a MuJoCo joint limit 2 mrad wide, as a jammed
  gearbox or a servo that holds its last goal; its goal is pinned there too so the servo does not fight the lock. The
  policy keeps reading the joint's true (stuck) position.
- weak: the joint's P gain is halved in every mode (stand KP 400 -> 200, walk KP_RL 200 -> 100).

  ~/.venvs/microduck-dyn/bin/python walk_fault.py --joint neck_pitch --mode frozen --seed 0 -- --vx 0.25 ...
Everything after `--` goes to brain_sim_check.py's own argument parser. Prints one JSON line.
"""
import argparse
import contextlib
import io
import json
import os
import sys

SIM_PYTHON = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
if os.path.realpath(sys.prefix) != os.path.realpath(os.path.dirname(os.path.dirname(SIM_PYTHON))):
    os.execv(SIM_PYTHON, [SIM_PYTHON, os.path.abspath(__file__)] + sys.argv[1:])

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
MAC = os.path.join(REPO, "microduck-sim", "guide", "firmware", "mac")
sys.path.insert(0, MAC)
import brain_sim_check as bsc  # noqa: E402
import walk_brain  # noqa: E402

LOCK_HALF_WIDTH = 0.001  # rad


def install(joint, mode):
    home = walk_brain.STAND[joint]
    load0 = bsc.ev.load

    def load(c0):
        m, d, c, names, bam = load0(c0)
        if mode == "frozen":
            jid = m.actuator(joint).trnid[0]
            m.jnt_limited[jid] = 1
            m.jnt_range[jid] = [home - LOCK_HALF_WIDTH, home + LOCK_HALF_WIDTH]
        return m, d, c, names, bam

    class FaultBrain(bsc.Brain):
        def tick(self, *a, **k):
            goal, kp, info = super().tick(*a, **k)
            if mode == "frozen" and goal is not None:
                goal = dict(goal)
                goal[joint] = home
            if mode == "weak" and kp:
                kp = {n: float(kp[n] if isinstance(kp, dict) else kp) for n in walk_brain.NAMES}
                kp[joint] *= 0.5
            return goal, kp, info

    bsc.ev.load = load
    bsc.Brain = FaultBrain


def main():
    argv = sys.argv[1:]
    rest = argv[argv.index("--") + 1:] if "--" in argv else []
    own = argv[:argv.index("--")] if "--" in argv else argv
    ap = argparse.ArgumentParser()
    ap.add_argument("--joint", default=None)
    ap.add_argument("--mode", choices=("none", "frozen", "weak"), default="none")
    args = ap.parse_args(own)
    if args.mode != "none":
        install(args.joint, args.mode)
    sys.argv = ["brain_sim_check.py"] + rest
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        bsc.main()
    out = json.loads(buf.getvalue().strip().splitlines()[-1])
    trace = out.pop("trace", None) or []
    modes = [r[1] for r in trace]
    out.update(fault_joint=args.joint, fault_mode=args.mode, cmd=" ".join(sys.argv[1:]),
               guard_stop=out.get("end_mode") == "stand" and "walk" in modes)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
