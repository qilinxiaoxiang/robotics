"""Gate G1 of the t2 plan (fork cmu/finetune/modal/FINETUNE-DELTA.md, "Run t2 plan"): how far a fine-tuned policy's
actions are from walk61's on walk61's own robot walks.

Rebuilds the 61 inputs of every logged walking tick (sensitivity.rebuild: the robot's sensors, walk61's last action,
the logged command, head at default) and runs walk61 and each candidate on the same states. The distance is the
vector norm over the 14 joints of (candidate - walk61), averaged over ticks; T1 scored 0.71 rad, the gate is <= 0.25.

    python3 action_distance.py --walk61 <dir>/walk61.onnx --candidates t2a=<a>.onnx t2b=<b>.onnx \
        [--log walk61_see_walks.jsonl] [--gate 0.25] [--json out.json]

Exit status 1 when any candidate misses the gate.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

from sensitivity import Policy, rebuild

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--walk61", required=True)
    ap.add_argument("--candidates", nargs="+", required=True, help="name=path.onnx ...")
    ap.add_argument("--log", default=str(HERE / "walk61_see_walks.jsonl"))
    ap.add_argument("--gate", type=float, default=0.25)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    ref = Policy(a.walk61)
    X = rebuild(a.log, ref)
    base = ref.run(X)
    out, ok = dict(log=a.log, states=len(X), gate=a.gate, walk61_action_norm=round(float(np.linalg.norm(base, axis=1).mean()), 3)), True
    print(f"{len(X)} walking states from {Path(a.log).name}; walk61 mean action norm {out['walk61_action_norm']}")
    for kv in a.candidates:
        name, path = kv.split("=", 1)
        pol = Policy(path)
        assert pol.order == ref.order and pol.default == ref.default, f"{name}: joint order or default pose differs"
        d = pol.run(X) - base
        dist = float(np.linalg.norm(d, axis=1).mean())
        per_joint = {j: round(float(np.abs(d[:, k]).mean()), 3) for k, j in enumerate(ref.order)}
        passed = dist <= a.gate
        ok &= passed
        out[name] = dict(onnx=path, distance=round(dist, 3), passed=passed, per_joint=per_joint)
        print(f"  {name:10s} distance {dist:.3f} rad -> {'PASS' if passed else 'FAIL'} (gate {a.gate}); "
              + " ".join(f"{j} {v}" for j, v in per_joint.items()))
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
