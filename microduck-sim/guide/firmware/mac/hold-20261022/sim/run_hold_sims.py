"""Lifted by the head, then set down: brain_sim_check.py runs for the graded hold (hold.py), one at a time.

Writes <case>.json (brain_sim_check's full result) next to this file and prints a one-line summary per run.
Base condition as teleop_sim_batch.py: as-built model, plugged manifest, robot_state_check.py --print-sim-args
(servo rail volts, dropped servo reads), stand61 at zero command, walk_wired.py's guards on.

  ~/.venvs/microduck-dyn/bin/python run_hold_sims.py [case ...]
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.normpath(os.path.join(HERE, "..", ".."))
MANIFEST = os.path.normpath(os.path.join(MAC, "..", "..", "..", "microduck_rl", "cmu", "model", "manifests", "plugged.json"))
SIM_PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")

GRIP = ["--grip-at", "3.0", "--release-at", "7.2"]
LIFT = ["--lift-at", "3.4", "--lower-at", "6.0", "--lift-height", "0.04"]
COMMON = ["--walk-s", "0", "--until", "12", "--wired-guards"]
CASES = {
    "a_baseline_seed0": GRIP + LIFT + ["--seed", "0"],
    "a_baseline_seed1": GRIP + LIFT + ["--seed", "1"],
    "b_hold_seed0": GRIP + LIFT + ["--hold", "--seed", "0"],
    "b_hold_seed1": GRIP + LIFT + ["--hold", "--seed", "1"],
    "c_grip_only_hold_seed0": GRIP + ["--hold", "--seed", "0"],
    "d_lift_no_grip_hold_seed0": LIFT + ["--hold", "--seed", "0"],
}
# hand model sensitivity: the grip holds the head's orientation (5 N m/rad) instead of letting it pivot
RIGID = ["--hand-krot", "5", "--hand-crot", "0.1"]
for seed in ("0", "1"):
    CASES[f"a_baseline_rigidgrip_seed{seed}"] = GRIP + LIFT + RIGID + ["--seed", seed]
    CASES[f"b_hold_rigidgrip_seed{seed}"] = GRIP + LIFT + RIGID + ["--hold", "--seed", seed]
# a long hand-on-head rest without a lift (a pat or a steadying hand for 22 s)
CASES["c_grip_only_long_hold_seed0"] = ["--grip-at", "3.0", "--release-at", "25", "--until", "30", "--hold", "--seed", "0"]
# --hold before hold_session.py has calibrated the leg currents: no load share, the grip term alone
CASES["b_hold_uncal_seed0"] = GRIP + LIFT + ["--hold", "--hold-uncal", "--seed", "0"]
CASES["b_hold_uncal_rigidgrip_seed0"] = GRIP + LIFT + RIGID + ["--hold", "--hold-uncal", "--seed", "0"]
CASES["b_hold_uncal_seed1"] = GRIP + LIFT + ["--hold", "--hold-uncal", "--seed", "1"]
CASES["b_hold_uncal_rigidgrip_seed1"] = GRIP + LIFT + RIGID + ["--hold", "--hold-uncal", "--seed", "1"]
# hold.py constant sensitivity (the module constants overridden for one run; hold.py itself unchanged)
for tag, sets in (("atouch0", ["--hold-set", "A_TOUCH", "0"]), ("uprate2", ["--hold-set", "UP_RATE", "2"])):
    for seed in ("0", "1"):
        CASES[f"b_hold_{tag}_seed{seed}"] = GRIP + LIFT + ["--hold", "--seed", seed] + sets
        CASES[f"b_hold_{tag}_rigidgrip_seed{seed}"] = GRIP + LIFT + RIGID + ["--hold", "--seed", seed] + sets
# walking at 0.25 m/s (walk 4-14 s), gripped by the head at 6.0 s (2026-10-23, Shawn: a held head means stop):
# --wired-hold applies walk_wired.py's grip stop and hold gate; without --hold the walk goes on (today's robot)
WALK = ["--walk-at", "4", "--walk-s", "10", "--vx", "0.25", "--until", "16"]
GRIP_W = ["--grip-at", "6.0", "--release-at", "10.2"]
LIFT_W = ["--lift-at", "6.4", "--lower-at", "9.0", "--lift-height", "0.04"]
for seed in ("0", "1", "2", "3"):
    CASES[f"w_base_lift_seed{seed}"] = WALK + GRIP_W + LIFT_W + ["--seed", seed]
    CASES[f"w_hold_lift_seed{seed}"] = WALK + GRIP_W + LIFT_W + ["--hold", "--wired-hold", "--seed", seed]
    CASES[f"w_hold_lift_rigidgrip_seed{seed}"] = WALK + GRIP_W + LIFT_W + RIGID + ["--hold", "--wired-hold", "--seed", seed]
    CASES[f"w_hold_grip_only_seed{seed}"] = WALK + ["--grip-at", "6.0", "--release-at", "8.0", "--hold", "--wired-hold",
                                                    "--seed", seed]
    CASES[f"w_hold_lift_nosettle_seed{seed}"] = WALK + GRIP_W + LIFT_W + ["--hold", "--wired-hold", "--no-settle",
                                                                          "--seed", seed]
# the standing lift with the gate on: must match b_hold (stand61 at zero command is always allowed)
CASES["b_hold_wired_seed0"] = GRIP + LIFT + ["--hold", "--wired-hold", "--seed", "0"]


def main():
    real = subprocess.run([SIM_PY, os.path.join(MAC, "robot_state_check.py"), "--print-sim-args"],
                          capture_output=True, text=True, check=True).stdout.split()
    base = ["--model", "asbuilt", "--manifest", MANIFEST] + real + COMMON
    names = sys.argv[1:] or list(CASES)
    for name in names:
        extra = CASES[name] if name in CASES else json.load(open(os.path.join(HERE, name + ".args.json")))
        cmd = ["timeout", "600", SIM_PY, os.path.join(MAC, "brain_sim_check.py")] + base + extra
        r = subprocess.run(cmd, capture_output=True, text=True)
        line = [ln for ln in r.stdout.splitlines() if ln.startswith("{")]
        if r.returncode != 0 or not line:
            raise SystemExit(f"{name}: exit {r.returncode}\n{r.stderr[-3000:]}")
        res = json.loads(line[-1])
        res["command"] = " ".join(cmd[2:])
        json.dump(res, open(os.path.join(HERE, name + ".json"), "w"), indent=1)
        h = res["hold"]
        print(name, json.dumps({k: res[k] for k in ("fell_at", "max_tilt", "end_mode")} | {k: h.get(k) for k in (
            "guard_stop_at", "guard_why", "max_raw_action_lift", "max_applied_action_lift", "leg_range_air_rad",
            "stable_after_release_s", "max_action_jump_0p3s_after_release", "min_s", "grip_stop_at",
            "applied_s_below_0p5_after_grip_s", "min_applied_s")}), flush=True)


if __name__ == "__main__":
    main()
