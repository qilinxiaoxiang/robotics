#!/usr/bin/env python
"""Tilted-floor wrapper around guide/firmware/mac/brain_sim_check.py (the repo file is not modified).

Tilting the world is done by rotating the gravity vector of the MuJoCo model and feeding the Brain the IMU
quaternion expressed in the gravity frame (what the real BNO085 reports). The scene floor is an infinite plane
through the origin, so rotating gravity is exactly tilting that plane: the robot still starts with its feet flat on
the floor (static_gap.setup / feet_flat_rot) and the floor-relative fall checks of brain_sim_check (trunk z < 0.04,
tilt vs floor normal > 45 deg) keep their meaning. What changes: the gravity the policy sees, the gravity the dynamics
feel, and the Brain's tilt guard (it uses the rotated quaternion, like the robot's IMU).

Reported per run, in addition to brain_sim_check's own row: max tilt of the trunk against gravity, the trunk
displacement in the floor plane (x = initial heading, y = left), the body gravity the policy saw at 1.2 s, and the
wall time. Run under ~/.venvs/microduck-dyn/bin/python (brain_sim_check re-execs otherwise).

  slope_sim.py --slope-deg 5 --direction down_ahead --case stand61 -- --model asbuilt --volt 7.0 --drop 0.04 ...
"""
import argparse
import contextlib
import io
import json
import math
import os
import sys
import time

MAC = "/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware/mac"
sys.path.insert(0, MAC)
import brain_sim_check as bsc  # noqa: E402  (imports mujoco, numpy, walk_brain under the sim venv)
import mujoco  # noqa: E402
import numpy as np  # noqa: E402
import walk_brain  # noqa: E402
from walk_brain import apply_inverse, qmul  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slope-results.jsonl")
G = 9.81


def conj(q):
    return (q[0], -q[1], -q[2], -q[3])


def gravity_dir(slope_deg, direction):
    """Unit gravity vector in the floor (world) frame. x = robot heading at start, y = robot's left, z = floor normal."""
    s, c = math.sin(math.radians(slope_deg)), math.cos(math.radians(slope_deg))
    return {"down_ahead": np.array([s, 0.0, -c]),    # floor descends ahead: gravity pulls forward
            "up_ahead": np.array([-s, 0.0, -c]),     # floor ascends ahead: gravity pulls backward
            "down_left": np.array([0.0, s, -c]),     # floor descends to the robot's left
            "down_right": np.array([0.0, -s, -c]),
            "flat": np.array([0.0, 0.0, -1.0])}[direction]


def rot_from_down(g_dir):
    """Rotation R_s with R_s @ [0,0,-1] = g_dir (axis in the floor plane)."""
    a, b = np.array([0.0, 0.0, -1.0]), np.asarray(g_dir, float)
    v = np.cross(a, b)
    s, c = np.linalg.norm(v), float(a @ b)
    if s < 1e-12:
        return np.eye(3)
    k = v / s
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + s * K + (1 - c) * K @ K


STATE = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slope-deg", type=float, default=0.0)
    ap.add_argument("--direction", default="flat",
                    choices=("flat", "down_ahead", "up_ahead", "down_left", "down_right"))
    ap.add_argument("--case", default="", help="label: stand61 | stand_kp400 | walk61_0.25")
    a, rest = ap.parse_known_args()
    if rest and rest[0] == "--":
        rest = rest[1:]
    g_dir = gravity_dir(a.slope_deg, a.direction)
    Rs = rot_from_down(g_dir)
    q_s = np.zeros(4)
    mujoco.mju_mat2Quat(q_s, Rs.ravel())
    q_s = tuple(float(x) for x in q_s)
    q_s_inv = conj(q_s)
    # self-check: a trunk upright relative to the floor must see gravity g_dir in its body frame
    seen = apply_inverse(qmul(q_s_inv, (1.0, 0.0, 0.0, 0.0)), [0.0, 0.0, -1.0])
    assert np.allclose(seen, g_dir, atol=1e-9), (seen, g_dir)

    # 1. gravity in the model + sanity on the floor geom
    orig_load = bsc.ev.load

    def load(config):
        m, d, c, names, bam = orig_load(config)
        assert np.allclose(m.opt.gravity, [0, 0, -G]), m.opt.gravity
        fl = m.geom("floor")
        assert fl.type[0] == mujoco.mjtGeom.mjGEOM_PLANE, fl.type
        assert np.allclose(m.geom_pos[fl.id], 0) and np.allclose(m.geom_quat[fl.id], [1, 0, 0, 0]), "floor not at origin"
        m.opt.gravity[:] = G * g_dir
        STATE.update(m=m, d=d, trunk=m.body("trunk_base").id, floor_friction=float(m.geom_friction[fl.id, 0]))
        return m, d, c, names, bam

    bsc.ev.load = load

    # 2. the Brain's IMU quaternion in the gravity frame; per-tick trace against gravity
    orig_tick = walk_brain.Brain.tick
    trace = []

    def tick(self, want, now, pos_t, vel_t, quat, gyro, *more):
        quat = qmul(q_s_inv, tuple(quat))
        out = orig_tick(self, want, now, pos_t, vel_t, quat, gyro, *more)
        d, trunk = STATE["d"], STATE["trunk"]
        R = d.xmat[trunk].reshape(3, 3)
        tilt_g = math.degrees(math.acos(float(np.clip(-(R[:, 2] @ g_dir), -1, 1))))
        info = out[2]
        trace.append((round(now, 2), self.mode, tilt_g, [float(x) for x in d.xpos[trunk]], info.get("gb"),
                      info.get("action") is not None))
        return out

    walk_brain.Brain.tick = tick
    bsc.Brain.tick = tick

    # 3. run brain_sim_check.main() with the pass-through flags
    sys.argv = ["brain_sim_check.py"] + rest
    buf, err = io.StringIO(), io.StringIO()
    t0 = time.time()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        bsc.main()
    wall = time.time() - t0
    row = json.loads(buf.getvalue().strip().splitlines()[-1])

    p0 = np.array(trace[0][3])
    # drift in the floor plane from the first tick to the last tick of the run (walk cases: from --walk-at, see dist_x)
    pe = np.array(trace[-1][3])
    gb_12 = next((tr[4] for tr in trace if tr[0] >= 1.2), None)
    policy_ticks = [tr for tr in trace if tr[5]]
    peak = max(tr[2] for tr in trace)
    peak_policy = max((tr[2] for tr in policy_ticks), default=None)
    end_tilt = trace[-1][2]
    tilt_floor_start = trace[0][2]
    # per-second tilt (vs gravity) summary for the appendix
    per_s = {}
    for tr in trace:
        per_s.setdefault(int(tr[0]), []).append(tr[2])
    tilt_by_s = {k: round(max(v), 1) for k, v in sorted(per_s.items())}
    modes = sorted({tr[1] for tr in trace})
    summary = dict(case=a.case, slope_deg=a.slope_deg, direction=a.direction, gravity_dir=[round(float(x), 4) for x in g_dir],
                   floor_friction=STATE.get("floor_friction"), wall_s=round(wall, 1), sim_s=round(trace[-1][0] + 0.02, 2),
                   fell_at=row["fell_at"], end_mode=row["end_mode"], modes_seen=modes,
                   max_tilt_vs_floor=row["max_tilt"], max_tilt_vs_gravity=round(peak, 1),
                   max_tilt_vs_gravity_policy=None if peak_policy is None else round(peak_policy, 1),
                   tilt_vs_gravity_at_t0=round(tilt_floor_start, 1), end_tilt_vs_gravity=round(end_tilt, 1),
                   drift_x_m=round(float(pe[0] - p0[0]), 3), drift_y_m=round(float(pe[1] - p0[1]), 3),
                   dist_x_from_walk_at=row["dist_x"], yaw_deg=row["yaw_deg"], max_action=row["max_action"],
                   action_jumps=row["action_jumps"], gb_at_1p2s=gb_12, tilt_by_s=tilt_by_s,
                   flags=rest, stderr_tail=err.getvalue().strip().splitlines()[-3:])
    print(json.dumps(summary))
    with open(OUT, "a") as f:
        f.write(json.dumps(dict(summary, bsc_row={k: v for k, v in row.items() if k != "trace"})) + "\n")


if __name__ == "__main__":
    main()
