"""Self-collision check of head poses in the as-built MuJoCo model (collision hulls: trunk_base, hip, leg, feet, jaw_soft).

The robot is posed with the legs at STAND and the feet flat (static_gap.feet_flat_rot/setup), mj_forward is run and
every contact between two robot geoms (not the floor) is listed with its penetration depth. The neck bodies carry no
collision hull, so the head hull against the trunk hull is the check this model can make; a head pose whose hulls
overlap the trunk by more than --tol m is "collides". Kinematic only (no stepping), one process, under the laptop
guard.

  ~/.venvs/microduck-dyn/bin/python collide.py poses.json -> results/collide.json
poses.json: {"name": {"neck_pitch": .., "head_pitch": .., "head_yaw": .., "head_roll": ..}, ...}
"""
import argparse
import json
import os
import sys

SIM_PYTHON = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
if os.path.realpath(sys.prefix) != os.path.realpath(os.path.dirname(os.path.dirname(SIM_PYTHON))):
    os.execv(SIM_PYTHON, [SIM_PYTHON, os.path.abspath(__file__)] + sys.argv[1:])

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
sys.path.insert(0, MAC)
import sim_host_guard  # noqa: E402
sim_host_guard.one_sim_on_laptop("collide")
import brain_sim_check as bsc  # noqa: E402
import mujoco  # noqa: E402
import numpy as np  # noqa: E402
from walk_brain import STAND  # noqa: E402

MANIFEST = os.path.abspath(os.path.join(MAC, "..", "..", "..", "microduck_rl", "cmu", "model", "manifests", "plugged.json"))


def load():
    c0 = bsc.cfg(0.09, model="asbuilt", kp=400, voltage=7.0)
    c0["mass_manifest"] = MANIFEST
    m, d, c, names, bam = bsc.ev.load(c0)
    return m, d, names


def contacts(m, d, names, pose, tol):
    Rt = bsc.feet_flat_rot(m, d, names, pose)
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, Rt.ravel())
    bsc.setup(m, d, names, pose, q)
    d.qpos[2] = 0.3  # clear of the floor: only robot-robot contacts matter here
    mujoco.mj_forward(m, d)
    floor = m.geom("floor").id
    out = []
    for i in range(d.ncon):
        c = d.contact[i]
        if floor in (c.geom1, c.geom2) or c.dist > -tol:
            continue
        b1, b2 = m.body(m.geom_bodyid[c.geom1]).name, m.body(m.geom_bodyid[c.geom2]).name
        out.append(dict(bodies=[b1, b2], depth_mm=round(-float(c.dist) * 1000, 2)))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("poses")
    ap.add_argument("--tol", type=float, default=0.001, help="m; penetration deeper than this counts")
    ap.add_argument("--out", default=os.path.join(HERE, "results", "collide.json"))
    args = ap.parse_args()
    poses = json.load(open(args.poses))
    m, d, names = load()
    base = contacts(m, d, names, dict(STAND), args.tol)
    res = {"_stand_reference": base}
    for name, head in poses.items():
        pose = dict(STAND, **head)
        cs = contacts(m, d, names, pose, args.tol)
        res[name] = dict(head=head, contacts=cs, collides=bool(cs))
        print(f"{name:<40} {'COLLIDES ' + str(cs) if cs else 'clear'}")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(res, f, indent=1)
