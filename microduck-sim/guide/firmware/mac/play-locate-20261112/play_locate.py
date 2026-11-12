#!/usr/bin/env python3
"""Locate mechanical play (旷动) from walk_wired logs, without taking the robot apart.

Idea. With a foot flat on the floor, the trunk's rotation is fixed by the encoders of that leg: the as-built model's
forward kinematics turns the stance leg's measured angles into the trunk angular velocity the gyro should read
(omega_kin). Whatever the gyro reads beyond that (the residual) happened outside the encoders: play between a servo
horn and its link, a loose bracket or screw, the foot rocking or slipping, or the IMU mount shaking.
Play shows itself when the load on a joint reverses: the link crosses its free travel with the encoder still.
So for every leg joint the script finds the ticks where its load (goal minus position, the servo's P term) changes
sign while its foot carries the robot, and compares the residual's tick-to-tick change there with that foot's
stance median. The joint whose load reversals shake the trunk most, beyond what the same gait does in the sim
(which has no play), is where to look.

Outputs one JSON with:
  frame     the rotation and lag that best map omega_kin onto the gyro (low band); identity and 0-1 ticks expected
  side_axis residual and gyro rms per stance foot and trunk axis (walk ticks), and the share the kinematics explain
  joints    per leg joint: load reversals in stance, median |delta residual| at a reversal over the stance median
  per_log   the same joint ratios per log, so one loose joint shows up consistently or not at all

  python3 play_locate.py --out robot.json ~/duck-walks/raw/duck_wired_log_app1111-*.jsonl
  python3 play_locate.py --out sim.json --sim <brain_sim_check tick logs>
"""
import argparse
import collections
import glob
import gzip
import json
import math
import os
import sys

SIM_PYTHON = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
if os.path.realpath(sys.prefix) != os.path.realpath(os.path.dirname(os.path.dirname(SIM_PYTHON))):
    os.execv(SIM_PYTHON, [SIM_PYTHON, os.path.abspath(__file__)] + sys.argv[1:])

import mujoco  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
WHOLE = os.path.join(MAC, "..", "..", "..", "hardware-design-20260912", "whole-robot-20260912")
for p in (MAC, os.path.join(MAC, "..", "pi"), os.path.join(WHOLE, "dynamics", "realgap-20261014"),
          os.path.join(WHOLE, "delay-repair-20260912")):
    sys.path.insert(0, p)
import evaluate_delay as ev  # noqa: E402
from static_gap import cfg  # noqa: E402
import walk_brain as wb  # noqa: E402

LEG = ("hip_yaw", "hip_roll", "hip_pitch", "knee", "ankle")
STANCE_MM = 4.0      # a foot is the stance foot when it sits this much lower along gravity than the other
LOAD_TICKS = 2       # |goal - position| on both sides of a reversal, in encoder ticks (0.088 deg each)
AXES = ("roll_x", "pitch_y", "yaw_z")
ORDER = list(wb.NAMES)


def rows(path):
    op = gzip.open(path, "rt") if path.endswith(".gz") else open(path)
    for line in op:
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("mode") not in ("walk", "stand") or not r.get("torque", True) or not r.get("imu_valid", True):
            continue
        q, g, gy = r.get("q"), r.get("gb"), r.get("gyro_body")
        if not q or None in q or not g or not gy:
            continue
        yield dict(t=r["t"], mode=r["mode"], q=q, gb=g, gyro=gy, pos=r.get("pos_tick"), goal=r.get("goal_tick"),
                   cmd=r.get("cmd"), policy=r.get("policy"))


def vee_log(R):
    c = max(-1.0, min(1.0, (np.trace(R) - 1) / 2))
    th = math.acos(c)
    w = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    return w * (0.5 if th < 1e-6 else th / (2 * math.sin(th)))


class Kin:
    def __init__(self):
        m, d, c, names, bam = ev.load(cfg(0.09, model="asbuilt", kp=200, voltage=7.4))
        self.m, self.d = m, mujoco.MjData(m)
        self.qadr = {n: m.jnt_qposadr[m.actuator(n).trnid[0]] for n in names}
        self.foot = {s: m.geom_bodyid[m.geom(f"{s}_foot_collision").id] for s in ("left", "right")}
        self.sole = {}
        for s in ("left", "right"):
            gid = m.geom(f"{s}_foot_collision").id
            mid = m.geom_dataid[gid]
            self.sole[s] = (gid, m.mesh_vert[m.mesh_vertadr[mid]:m.mesh_vertadr[mid] + m.mesh_vertnum[mid]].copy())
        self.order = list(ORDER)  # the log's q order

    def feet(self, q):
        d = self.d
        d.qpos[:] = 0
        d.qpos[3] = 1.0
        for n, v in zip(self.order, q):
            d.qpos[self.qadr[n]] = v
        mujoco.mj_kinematics(self.m, d)
        out = {}
        for s, b in self.foot.items():
            gid, v = self.sole[s]
            pts = v @ d.geom_xmat[gid].reshape(3, 3).T + d.geom_xpos[gid]
            out[s] = (d.xmat[b].reshape(3, 3).copy(), pts)
        return out


def series(path, kin):
    """Per log: consecutive tick pairs with the stance foot, omega_kin through it, the gyro, and per-joint load."""
    R = list(rows(path))
    out = []
    names_ids = list(wb.NAMES)  # pos_tick / goal_tick order (servo IDs)
    prev = None
    for r in R:
        f = kin.feet(r["q"])
        g = np.array(r["gb"], float)
        g /= np.linalg.norm(g) or 1
        h = {s: float((f[s][1] @ g).max()) for s in f}  # the sole point lowest along gravity
        dh = (h["left"] - h["right"]) * 1000
        stance = "left" if dh > STANCE_MM else "right" if dh < -STANCE_MM else "double"
        load = None
        if r["pos"] and r["goal"]:  # pos_tick: a list in servo-ID order; goal_tick: {servo ID: tick}
            gl = r["goal"]
            load = {n: gl[str(i)] - r["pos"][k] for k, (i, n) in enumerate(zip(wb.IDS, names_ids))
                    if gl.get(str(i)) is not None and r["pos"][k] is not None}
        cur = dict(t=r["t"], mode=r["mode"], feet=f, stance=stance, gyro=np.array(r["gyro"], float), load=load,
                   walking=r["mode"] == "walk" and (
                       any(float(r["cmd"].get(k, 0) or 0) for k in ("vx", "vy", "vtheta")) if r["cmd"] is not None
                       else r["policy"] == "walk"))  # sim tick logs carry no cmd: the walk policy is running
        if prev is not None and 0.005 < cur["t"] - prev["t"] < 0.06:
            dt = cur["t"] - prev["t"]
            wk = {}
            for s in ("left", "right"):
                wk[s] = vee_log(prev["feet"][s][0] @ cur["feet"][s][0].T) / dt
            out.append(dict(t=cur["t"], mode=cur["mode"], walking=cur["walking"], stance=cur["stance"],
                            stance_prev=prev["stance"], wk=wk, gyro=cur["gyro"], gyro_prev=prev["gyro"],
                            load=cur["load"], load_prev=prev["load"]))
        elif prev is not None:
            out.append(None)  # a gap: no pair across it
        prev = cur
    return out


def lowpass(x, a=0.3):
    y = np.empty_like(x)
    acc = x[0]
    for i, v in enumerate(x):
        acc = a * v + (1 - a) * acc
        y[i] = acc
    return y


def fit_frame(segs):
    """Rotation Q and lag (ticks, gyro behind kinematics) that best map omega_kin onto the gyro on single-stance
    walking ticks, low band."""
    best = None
    for lag in range(0, 4):
        A, B = [], []
        for seg in segs:
            for i in range(len(seg) - lag):
                a, b = seg[i], seg[i + lag]
                if a["stance"] == "double" or a["stance"] != a["stance_prev"] or not a["walking"]:
                    continue
                A.append(a["wk"][a["stance"]])
                B.append(b["gyro"])
        if len(A) < 200:
            continue
        A, B = np.array(A), np.array(B)
        Al, Bl = np.apply_along_axis(lowpass, 0, A), np.apply_along_axis(lowpass, 0, B)
        U, _, Vt = np.linalg.svd(Bl.T @ Al)
        Q = U @ np.diag([1, 1, np.linalg.det(U @ Vt)]) @ Vt
        err = float(np.mean(np.sum((Bl - Al @ Q.T) ** 2, 1)))
        if best is None or err < best[2]:
            best = (lag, Q, err, len(A))
    return best


def split(seq):
    segs, cur = [], []
    for x in seq:
        if x is None:
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(x)
    if cur:
        segs.append(cur)
    return segs


def analyse(paths, kin, frame=None):
    per_log, allsegs = {}, []
    for p in paths:
        segs = split(series(p, kin))
        per_log[os.path.basename(p)] = segs
        allsegs += segs
    fr = fit_frame(allsegs) if frame is None else frame
    lag, Q = fr[0], fr[1]
    side_axis = collections.defaultdict(lambda: dict(res=[], gyro=[], kin=[]))
    joint = collections.defaultdict(lambda: dict(rev=[], base=[]))
    per = {}
    for name, segs in per_log.items():
        pj = collections.defaultdict(lambda: dict(rev=[], base=[]))
        for seg in segs:
            res = []
            for i in range(len(seg) - lag):
                a, b = seg[i], seg[i + lag]
                s = a["stance"]
                if s == "double" or s != a["stance_prev"]:
                    res.append(None)
                    continue
                wk = Q @ a["wk"][s]
                res.append((a, s, b["gyro"] - wk, b["gyro"], wk))
            for i in range(1, len(res)):
                if res[i] is None or res[i - 1] is None:
                    continue
                a, s, r, gy, wk = res[i]
                if a["walking"]:
                    side_axis[s]["res"].append(r)
                    side_axis[s]["gyro"].append(gy)
                    side_axis[s]["kin"].append(wk)
                jump = float(np.linalg.norm(r - res[i - 1][2]))
                if not a["walking"] or not a["load"] or not a["load_prev"]:
                    continue
                for jn in LEG:
                    n = f"{s}_{jn}"
                    l0, l1 = a["load_prev"].get(n), a["load"].get(n)
                    if l0 is None or l1 is None:
                        continue
                    key = n
                    if (l0 >= LOAD_TICKS and l1 <= -LOAD_TICKS) or (l0 <= -LOAD_TICKS and l1 >= LOAD_TICKS):
                        joint[key]["rev"].append(jump)
                        pj[key]["rev"].append(jump)
                    else:
                        joint[key]["base"].append(jump)
                        pj[key]["base"].append(jump)
        per[name] = {k: ratio(v) for k, v in sorted(pj.items())}
    sa = {}
    for s, v in side_axis.items():
        res, gy, kn = np.array(v["res"]), np.array(v["gyro"]), np.array(v["kin"])
        if len(res) < 50:
            continue
        sa[s] = dict(ticks=len(res), **{ax: dict(gyro_rms=round(float(np.sqrt(np.mean(gy[:, k] ** 2))), 3),
                                                kin_rms=round(float(np.sqrt(np.mean(kn[:, k] ** 2))), 3),
                                                residual_rms=round(float(np.sqrt(np.mean(res[:, k] ** 2))), 3),
                                                residual_jump_rms=round(float(np.sqrt(np.mean(np.diff(res[:, k]) ** 2))), 3))
                                        for k, ax in enumerate(AXES)})
    return dict(frame=dict(lag_ticks=lag, Q=np.round(Q, 3).tolist(), fit_ticks=fr[3]),
                side_axis=sa, joints={k: ratio(v) for k, v in sorted(joint.items())}, per_log=per), fr


def ratio(v):
    rev, base = v["rev"], v["base"]
    if len(rev) < 10 or len(base) < 50:
        return dict(reversals=len(rev))
    return dict(reversals=len(rev), rev_median=round(float(np.median(rev)), 3), base_median=round(float(np.median(base)), 3),
                ratio=round(float(np.median(rev) / max(np.median(base), 1e-6)), 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--order", choices=("obs", "names"), default="names", help="joint order of q in the log: servo-ID order (walk_brain.NAMES) in both robot and sim logs, checked 2026-11-12 against the stand pose")
    ap.add_argument("--frame-from", help="reuse the frame fit of an earlier output (for sim logs: the robot's)")
    a = ap.parse_args()
    global ORDER
    ORDER = list(wb.OBSERVATION_DOF_ORDER if a.order == "obs" else wb.NAMES)
    paths = sorted(set(p for g in a.logs for p in glob.glob(os.path.expanduser(g))))
    kin = Kin()
    frame = None
    if a.frame_from:
        f = json.load(open(a.frame_from))["frame"]
        frame = (f["lag_ticks"], np.array(f["Q"]), 0.0, f["fit_ticks"])
    res, _ = analyse(paths, kin, frame)
    res["logs"] = [os.path.basename(p) for p in paths]
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps(dict(frame=res["frame"], side_axis=res["side_axis"], joints=res["joints"]), indent=1))


if __name__ == "__main__":
    main()
