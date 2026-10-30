"""Input sensitivity of two walking policies on the robot's own logged states.

Rebuilds the 61 policy inputs walk_brain.py fed the policy on each logged walking tick (gyro, gravity, joint offsets
from the default, joint velocities, last action, [vx, vy, turn], head command, zero body slots), then evaluates each
policy's Jacobian d action / d input by central differences on the SAME states. A policy whose actions move more per
unit of sensor change turns the robot's sensor noise and servo deadband into larger action jumps; that is the quantity
a Lipschitz-constrained policy (Chen et al. 2024, arXiv 2410.11825) bounds.

    python3 sensitivity.py --models walk61=<dir>/walk61.onnx t1=<dir>/walk61.onnx --logs a.jsonl b.jsonl [--every 5]

Prints, per policy and per state set, the median and 90th-percentile Frobenius norm of the Jacobian and the norm per
input group. Joint order: log rows hold q and dq in walk_brain.NAMES order, the policy uses OBSERVATION_DOF_ORDER
(from the ONNX metadata, checked against the default pose there).
"""
import argparse
import json
import math

import numpy as np
import onnxruntime as ort

NAMES = ['right_ankle', 'right_knee', 'right_hip_pitch', 'right_hip_roll', 'right_hip_yaw', 'left_ankle', 'left_knee',
         'left_hip_pitch', 'left_hip_roll', 'left_hip_yaw', 'head_pitch', 'neck_pitch', 'head_yaw', 'head_roll']
GROUPS = [("gyro", 0, 3), ("gravity", 3, 6), ("joint pos", 6, 20), ("joint vel", 20, 34), ("last action", 34, 48),
          ("command", 48, 51), ("head", 51, 55), ("body", 55, 61)]
HEAD_JOINTS = ("neck_pitch", "head_pitch", "head_yaw", "head_roll")
HEAD_RANGE = (1.10, 1.10, 1.40, 0.31)
HEAD_ALPHA = 0.2


class Policy:
    def __init__(self, path):
        self.sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
        meta = self.sess.get_modelmeta().custom_metadata_map
        self.order = meta["joint_names"].split(",")
        self.default = dict(zip(self.order, [float(v) for v in meta["default_joint_pos"].split(",")]))
        self.name = self.sess.get_inputs()[0].name

    def run(self, obs):
        # the exported graph takes one row at a time
        return np.stack([self.sess.run(None, {self.name: o[None].astype(np.float32)})[0][0] for o in obs])


def rebuild(path, ref):
    """Inputs of every logged tick that ran the walk policy; ref supplies the joint order and default pose."""
    rows = []
    for line in open(path, errors="ignore"):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    out, last, head = [], None, np.zeros(4)
    for r in rows:
        if r.get("mode") != "walk" or not r.get("q") or not r.get("gb"):
            continue
        cmd = r.get("cmd") or {}
        want_head = cmd.get("head") or {}
        target = np.zeros(4)
        for k, n in enumerate(HEAD_JOINTS):
            if want_head.get(n) is not None:
                target[k] = float(np.clip(float(want_head[n]) - ref.default[n], -HEAD_RANGE[k], HEAD_RANGE[k]))
        head = head + HEAD_ALPHA * (target - head)
        if r.get("policy") == "walk" and r.get("action") and last is not None:
            q = dict(zip(NAMES, r["q"]))
            dq = dict(zip(NAMES, r["dq"]))
            obs = (list(r["gyro_body"]) + list(r["gb"]) + [q[n] - ref.default[n] for n in ref.order]
                   + [dq[n] for n in ref.order] + list(last)
                   + [float(cmd.get("vx") or 0), float(cmd.get("vy") or 0), float(r.get("turn") or 0)]
                   + list(head) + [0.0] * 6)
            out.append(obs)
        if r.get("action"):
            last = r["action"]
    return np.array(out, dtype=np.float32)


def jacobians(pol, X, eps=1e-3):
    n, d = X.shape
    J = np.zeros((n, 14, d), dtype=np.float64)
    for k in range(d):
        Xp, Xm = X.copy(), X.copy()
        Xp[:, k] += eps
        Xm[:, k] -= eps
        J[:, :, k] = (pol.run(Xp) - pol.run(Xm)) / (2 * eps)
    return J


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", required=True, help="name=path.onnx ...")
    ap.add_argument("--logs", nargs="+", required=True)
    ap.add_argument("--every", type=int, default=5, help="use every Nth walking tick")
    ap.add_argument("--json", default=None, help="write the numbers here")
    a = ap.parse_args()
    pols = {kv.split("=", 1)[0]: Policy(kv.split("=", 1)[1]) for kv in a.models}
    ref = next(iter(pols.values()))
    for p in pols.values():
        assert p.order == ref.order and p.default == ref.default, "policies disagree on joint order or default pose"
    result = {}
    for log in a.logs:
        X = rebuild(log, ref)[::a.every]
        if len(X) == 0:
            continue
        name = log.rsplit("/", 1)[-1]
        print(f"\n{name}: {len(X)} walking states")
        for pn, pol in pols.items():
            J = jacobians(pol, X)
            fro = np.sqrt((J ** 2).sum(axis=(1, 2)))
            groups = {g: round(float(np.median(np.sqrt((J[:, :, s:e] ** 2).sum(axis=(1, 2))))), 3) for g, s, e in GROUPS}
            row = dict(states=len(X), median=round(float(np.median(fro)), 3), p90=round(float(np.percentile(fro, 90)), 3),
                       groups=groups)
            result.setdefault(name, {})[pn] = row
            print(f"  {pn:8s} |J| median {row['median']:7.3f}  p90 {row['p90']:7.3f}  "
                  + "  ".join(f"{g} {v}" for g, v in groups.items()))
    if a.json:
        json.dump(result, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
