"""Round 3 check: do the gate failures of the ts_start teacher arms depend on the position gain?

  python3 train/ts3_gain_split.py spec <dir under ckpt> [...]     -> train/eval/spec_gainsplit.json
  modal run train/flight_eval_modal.py --spec train/eval/spec_gainsplit.json
  python3 train/ts3_gain_split.py read <dir> [...]                -> table, train/out/gain_split.json

Runtime simulation (the gates' code path), walking, 10 seeds per cell, with the firmware position gain of walk mode
(--kp-rl; 200 is the robot's value, scale 1.0) at the training range's scales 0.8, 1.0, 1.25, 1.5, 1.75, 2.0, 2.2:
no pack and nominal pack (--stand-s 0 with the pack, as in gates G4 / G5). Per cell: falls of 10, median action
jumps per 10 s as reported by flight_eval (action_jumps_median).
"""
import json
import sys
from pathlib import Path

T = Path(__file__).resolve().parent
KPS = [160, 200, 250, 300, 350, 400, 440]
LOADS = {"none": ("manifests/flightpack-none.json", []), "pack": ("manifests/flightpack-nominal.json", ["--stand-s", "0"])}


def name(d, load, kp):
    return f"gainsplit_{d}_{load}_kp{kp}"


cmd, dirs = sys.argv[1], sys.argv[2:]
if cmd == "spec":
    evals = [dict(name=name(d, ld, kp), models=f"ckpt/{d}", manifest=man, case="walk", episodes=10, extra=ex + ["--kp-rl", str(kp)])
             for d in dirs for ld, (man, ex) in LOADS.items() for kp in KPS]
    (T / "eval/spec_gainsplit.json").write_text(json.dumps(dict(evals=evals), indent=1))
    print(len(evals), "evals,", 10 * len(evals), "episodes")
else:
    out = {}
    for d in dirs:
        for ld in LOADS:
            print(f"{d} {ld}: gain scale -> falls of 10, median jumps, fall times")
            for kp in KPS:
                s = json.loads((T / f"eval/{name(d, ld, kp)}.json").read_text())["summary"]
                out[name(d, ld, kp)] = dict(falls=s["falls"], episodes=s["episodes"], jumps=s["action_jumps_median"], fall_times=s["fall_times"])
                print(f"  {kp / 200:.2f} (kp {kp}): {s['falls']} of {s['episodes']}, jumps {s['action_jumps_median']}, {s['fall_times']}")
    (T / "out/gain_split.json").write_text(json.dumps(out, indent=1))
