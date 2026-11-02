"""Closed-loop replay of the scan session on the as-built sim with hidden angle offsets. Mac mini only.

walk_brain.Brain runs the deployed walk61/stand61/groundpick61 on the charger-pack mass model through the session's real
command sequence (shortened holds): stand, walk at zero with two nudges, groundpick phase 0.33, phase 1, walk with the
head commands. Each hold is compared with the robot's own log (real_windows.json) and the scan.

A hidden offset h on a joint: the joint's true angle is the encoder's plus h. The brain reads q_true - h and its goal
reaches the servo as goal + h. foot_play instead adds a free hinge below the ankle encoder, so the angle grows with load.
imu_bias rotates what the sensor reports about the true trunk (brain_sim_check.py --imu-pitch); the brain's 4 deg trim is
right at imu_bias 4 and leaves the brain reading 4 deg behind the true trunk at imu_bias 0.

    ~/.venvs/microduck-dyn/bin/python closed_loop.py --only chain --out /tmp/x.json
    ~/.venvs/microduck-dyn/bin/python closed_loop.py --jobs 8 --out closed_loop_results.json
    python3 closed_loop.py --report closed_loop_results.json

Read-drops: 0 in the holds (0.02 % in the log) and the walking figure from CURRENT-STATE.json while legs move.
"""
import argparse
import collections
import json
import math
import os
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

HERE = os.path.dirname(os.path.abspath(__file__))
SIM_PYTHON = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
REPORT_ONLY = "--report" in sys.argv
if not REPORT_ONLY and os.path.realpath(sys.prefix) != os.path.realpath(os.path.dirname(os.path.dirname(SIM_PYTHON))):
    os.execv(SIM_PYTHON, [SIM_PYTHON, os.path.abspath(__file__)] + sys.argv[1:])

import numpy as np  # noqa: E402

REAL = json.load(open(os.path.join(HERE, "real_windows.json")))
STATE = json.load(open(os.path.join(HERE, "..", "CURRENT-STATE.json")))["facts"]
VOLT = STATE["servo_rail_v"]["value"]        # the session's log reads 7.0 as well
MOVE_DROP = STATE["servo_read_drop_fraction"]["value"]
MANIFEST = os.path.join(HERE, "manifest-charger-20261101.json")
DT = 0.02
ID_NAMES = ["right_ankle", "right_knee", "right_hip_pitch", "right_hip_roll", "right_hip_yaw", "left_ankle", "left_knee",
            "left_hip_pitch", "left_hip_roll", "left_hip_yaw", "head_pitch", "neck_pitch", "head_yaw", "head_roll"]
ANKLE_FWD = {"left_ankle": -1.0, "right_ankle": 1.0}   # sim_static.probe_ankle_sign: this pattern leans the trunk forward
ANKLE_STAND, ANKLE_BEND = 0.44, 1.25                   # mean |ankle| of the two real holds, for the pose-dependent case

# Timeline, s. Holds are shorter than the robot's; the last 5 s of each are compared.
T_NUDGE1, T_NUDGE2, T_GP, T_RISE, T_WALK, T_HEAD, T_END = 8.0, 10.0, 18.0, 38.0, 40.4, 48.0, 62.0
WINDOWS = {"stand1": (13.0, 18.0), "bend": (33.0, 38.0), "stand2": (57.0, 62.0)}

PLANTS = {
    "chain": {},
    "neck-5": {"neck": -5.0},
    "neck-10.4": {"neck": -10.41},
    "ankles2.5": {"ankles": 2.5},
    "ankles5": {"ankles": 5.0},
    "ankles9.7": {"ankles": 9.69},
    "ankles5_neck-5": {"ankles": 5.0, "neck": -5.0},
    # the scan's per-pose fit, following the ankle angle between the two holds
    "scanbest": {"ankles": 2.5, "neck": -5.0, "bend_ankles": 9.0, "bend_neck": -1.0},
}
for _deg in (-2, -3, -4, -6, -7):
    PLANTS[f"neck{_deg}"] = {"neck": float(_deg)}
# a hard stop on the ankle at the angle the real ankle holds in the bend, with its goal 0.32 rad past it
for _stop in (1.20, 1.25, 1.30, 1.35, 1.40):
    PLANTS[f"stop{_stop}"] = {"ankle_stop": _stop}
    for _deg in (-3, -5):
        PLANTS[f"stop{_stop}_neck{_deg}"] = {"ankle_stop": _stop, "neck": float(_deg)}
    PLANTS[f"stop{_stop}_ankles2.5"] = {"ankle_stop": _stop, "ankles": 2.5}
    PLANTS[f"stop{_stop}_ankles2.5_neck-3"] = {"ankle_stop": _stop, "ankles": 2.5, "neck": -3.0}
# the head partly carried by the floor in the bend: an upward force on the jaw during the hold, N
for _f in (0.5, 1.0, 1.5, 2.0, 3.0):
    PLANTS[f"lift{_f}"] = {"head_lift": _f}
    PLANTS[f"stop1.25_lift{_f}"] = {"ankle_stop": 1.25, "head_lift": _f}
    PLANTS[f"stop1.25_neck-5_lift{_f}"] = {"ankle_stop": 1.25, "neck": -5.0, "head_lift": _f}
# floor and sole friction (evaluate_delay's friction key)
for _f in (1.5, 2.0, 3.0):
    PLANTS[f"fric{_f}"] = {"friction": _f}
    PLANTS[f"stop1.25_fric{_f}"] = {"ankle_stop": 1.25, "friction": _f}
# load sag the encoder does not see: it reads the joint a fraction alpha of the way back toward the goal (ankles excluded,
# they sit on the stop)
for _a in (0.3, 0.5, 0.65, 0.8):
    PLANTS[f"stop1.25_blind{_a}"] = {"ankle_stop": 1.25, "blind": _a}
    PLANTS[f"stop1.25_blind{_a}_neck-5"] = {"ankle_stop": 1.25, "blind": _a, "neck": -5.0}
for _deg in (1, 2, 3, 4, 5, 6, 7, 8, 9):
    PLANTS[f"footplay{_deg}"] = {"foot_play": float(_deg)}
for _deg in (3, 5, 7):
    PLANTS[f"footplay{_deg}_neck-5"] = {"foot_play": float(_deg), "neck": -5.0}
    PLANTS[f"footplay{_deg}_k0.2"] = {"foot_play": float(_deg), "fp_k": 0.2}
    PLANTS[f"footplay{_deg}_k1"] = {"foot_play": float(_deg), "fp_k": 1.0}
BIASES = (0.0, 2.0, 4.0)
SEEDS = (7, 8)


def want_at(t):
    """The session's commands, on the shortened clock. It enters walk directly: on the robot Shawn held it through the open
    loop stand, and the sim's free open-loop stand tips over at any forward ankle offset before the policy starts."""
    walk = {"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0}
    if T_NUDGE1 <= t < T_NUDGE1 + 0.6 or T_NUDGE2 <= t < T_NUDGE2 + 0.6:
        return dict(walk, vx=0.25)
    if t < T_GP:
        return walk
    if t < T_RISE:
        return {"mode": "groundpick", "phase": 0.33}
    if t < T_WALK:
        return {"mode": "groundpick", "phase": 1.0}
    if t < T_HEAD:
        return walk
    pitch = 0.25 if t < T_HEAD + 0.2 else 0.15 if t < T_HEAD + 1.2 else 0.05
    return dict(walk, head={"head_pitch": pitch, "head_roll": 0.0, "head_yaw": 0.0})


def moving(t):
    return (T_NUDGE1 <= t < T_NUDGE2 + 2.0) or (T_GP <= t < T_GP + 3.0) or (T_RISE <= t < T_WALK + 2.0)


def hidden(plant, names, q_enc=None):
    """Hidden offset per joint in rad. Pose-dependent cases read the encoder's own ankle angle."""
    f = 0.0
    if "bend_ankles" in plant and q_enc is not None:
        f = (abs(q_enc[names.index("left_ankle")]) + abs(q_enc[names.index("right_ankle")])) / 2
        f = min(1.0, max(0.0, (f - ANKLE_STAND) / (ANKLE_BEND - ANKLE_STAND)))
    ank = plant.get("ankles", 0.0) + f * (plant.get("bend_ankles", plant.get("ankles", 0.0)) - plant.get("ankles", 0.0))
    neck = plant.get("neck", 0.0) + f * (plant.get("bend_neck", plant.get("neck", 0.0)) - plant.get("neck", 0.0))
    h = np.zeros(len(names))
    h[names.index("left_ankle")] = math.radians(ank) * ANKLE_FWD["left_ankle"]
    h[names.index("right_ankle")] = math.radians(ank) * ANKLE_FWD["right_ankle"]
    h[names.index("neck_pitch")] = math.radians(neck)
    return h


def run_case(job):
    plant_name, bias, seed, stop_at = job
    MAC = os.path.abspath(os.path.join(HERE, "..", "guide", "firmware", "mac"))
    sys.path[:0] = [MAC, os.path.join(MAC, "getup-20261026")]
    import mujoco
    import getup_sim as gs
    from brain_sim_check import FOOT_PLAY_AXES

    plant = PLANTS[plant_name]
    rng = np.random.default_rng(seed)
    c0 = gs.cfg(0.09, model="asbuilt", kp=200, voltage=VOLT)
    c0["friction"] = plant.get("friction", 1.0)
    c0["mass_manifest"] = MANIFEST
    if plant.get("foot_play"):
        c0["foot_play"] = dict(deg=plant["foot_play"], stiffness=plant.get("fp_k", 0.05), damping=0.002, axis=FOOT_PLAY_AXES["pitch"])
    m, d, c, names, bam = gs.ev.load(c0)
    if plant.get("ankle_stop"):
        for n in ("left_ankle", "right_ankle"):
            jid = m.joint(n).id
            m.jnt_limited[jid] = 1
            m.jnt_range[jid] = (-plant["ankle_stop"], plant["ankle_stop"])
    brain = gs.Brain(gs.MODELS)
    home = {n: brain.default[n] for n in names}
    h0 = hidden(plant, names)
    gs.place(m, d, names, {n: home[n] + h0[i] for i, n in enumerate(names)}, np.array([1.0, 0, 0, 0]))
    c.q_target = np.array([home[n] for n in names]) + h0
    bam.actuator.kp = 400

    idx = {n: names.index(n) for n in gs.NAMES}
    ji = np.array([m.actuator(n).trnid[0] for n in names])
    qa, va = m.jnt_qposadr[ji], m.jnt_dofadr[ji]
    trunk = m.body("trunk_base").id
    gyro_adr = m.sensor("imu_ang_vel").adr[0]
    sub = round(DT / m.opt.timestep)
    Rimu = gs.rot_y(bias)
    qbias = np.zeros(4)
    mujoco.mju_mat2Quat(qbias, Rimu.ravel())
    aq = collections.deque([c.q_target.copy()] * 2, maxlen=2)
    sq = collections.deque(maxlen=2)
    cam = m.site("head_camera").id
    jaw = m.body("jaw_soft").id
    # every body from the neck up, for the head-on-floor check
    neck_body = m.jnt_bodyid[m.joint("neck_pitch").id]
    head_bodies = set()
    for b in range(m.nbody):
        p = b
        while p > 0:
            if p == neck_body:
                head_bodies.add(b)
                break
            p = m.body_parentid[p]
    floor = m.geom("floor").id
    force = np.zeros(6)

    rows = {k: collections.defaultdict(list) for k in WINDOWS}
    fell_at, peak_gz, trace = None, -1.0, []
    goal_now = None
    for k in range(int(round((stop_at or T_END) / DT))):
        t = k * DT
        want = want_at(t)
        q_true = tuple(d.qpos[3:7].copy())
        q_s = gs.qmul(tuple(q_true), tuple(qbias)) if bias else q_true
        q_sensor = gs.qmul(gs.qmul(q_s, gs.conj(gs.IMU_MOUNT_QUAT)), gs.conj(gs.MOUNT_FIX))
        w_body = Rimu.T @ d.sensordata[gyro_adr:gyro_adr + 3].copy()
        g_sensor = gs.apply(gs.MOUNT_FIX, gs.apply(gs.IMU_MOUNT_QUAT, w_body))
        sample = (q_sensor, tuple(float(x) for x in g_sensor), d.qpos[qa].copy(), d.qvel[va].copy())
        if not sq:
            sq.extend([sample] * sq.maxlen)
        sq.append(sample)
        qs_old, gs_old, qm, dqm = sq[0]
        h = hidden(plant, names, qm - h0) if "bend_ankles" in plant else h0
        qe = qm - h
        if plant.get("blind") and goal_now is not None:
            qe = qe + plant["blind"] * np.array([0.0 if "ankle" in n else goal_now[n] - qe[i] for i, n in enumerate(names)])
        pos_t = [gs.to_tick(n, float(qe[idx[n]])) for n in gs.NAMES]
        vel_t = [int(round(float(dqm[idx[n]]) / gs.VEL_UNIT / gs.SIGN[n])) for n in gs.NAMES]
        fresh = not (moving(t) and rng.random() < MOVE_DROP)
        goal, kp, info = brain.tick(want, t, pos_t, vel_t, tuple(qs_old), gs_old, fresh, 0.024, 0.024)
        if goal is not None:
            goal_now = goal
        target = np.array([goal[n] for n in names]) + h if goal is not None else aq[-1].copy()
        if goal is not None and kp:
            bam.actuator.kp = kp
        aq.append(target.copy())
        c.q_target = aq[0]
        if plant.get("head_lift"):
            d.xfrc_applied[jaw, 2] = plant["head_lift"] if T_GP + 2.0 <= t < T_RISE else 0.0
        for _ in range(sub):
            c.update()
            mujoco.mj_step(m, d)
        R = d.xmat[trunk].reshape(3, 3)
        gz = -float(R[2, 2])
        peak_gz = max(peak_gz, gz)
        if fell_at is None and gz > -0.35:
            fell_at = round(t, 2)
        if k % 25 == 0:
            trace.append((round(t, 2), brain.mode, round(math.degrees(math.asin(max(-1, min(1, -R[2, 0])))), 1),
                          round(float(info["q"][11]), 3), round(float(info["gb"][0]), 3)))
        for win, (a, b) in WINDOWS.items():
            if a <= t < b:
                rw = rows[win]
                rw["q"].append(info["q"])
                rw["gb"].append(info["gb"])
                if goal_now is not None:
                    rw["err"].append([info["q"][i] - goal_now[n] for i, n in enumerate(ID_NAMES)])
                rw["pitch"].append(math.degrees(math.asin(max(-1, min(1, -R[2, 0])))))
                rw["cam_z"].append(float(d.site_xpos[cam][2]))
                if k % 10 == 0:
                    fz = 0.0
                    for i in range(d.ncon):
                        con = d.contact[i]
                        g1, g2 = con.geom1, con.geom2
                        other = g2 if g1 == floor else g1 if g2 == floor else None
                        if other is not None and m.geom_bodyid[other] in head_bodies:
                            mujoco.mj_contactForce(m, d, i, force)
                            fz += force[0]
                    rw["head_floor_n"].append(fz)
    out = dict(plant=plant_name, imu_bias=bias, seed=seed, fell_at=fell_at, peak_gz=round(peak_gz, 3), windows={}, trace=trace)
    for win, rw in rows.items():
        if not rw["q"]:
            continue
        q, err = np.array(rw["q"], float), np.array(rw["err"], float)
        gb = np.array(rw["gb"], float).mean(0)
        out["windows"][win] = dict(q=dict(zip(ID_NAMES, np.round(q.mean(0), 4).tolist())), q_range=round(float(np.ptp(q, axis=0).max()), 4),
                                   err=dict(zip(ID_NAMES, np.round(np.median(err, axis=0), 4).tolist())),
                                   gb=np.round(gb, 4).tolist(), brain_deg=round(math.degrees(math.asin(gb[0])), 2),
                                   true_deg=round(float(np.mean(rw["pitch"])), 2), cam_z_mm=round(float(np.mean(rw["cam_z"])) * 1000, 1),
                                   head_floor_n=round(float(np.mean(rw["head_floor_n"])), 3))
    return out


def report(path):
    data = json.load(open(path))["rows"]
    legs = [n for n in ID_NAMES if "ankle" in n or "knee" in n or "hip_pitch" in n]
    upper = ["neck_pitch", "head_pitch"]
    detail = sys.argv[sys.argv.index("--detail") + 1].split(",") if "--detail" in sys.argv else []
    print("real:", {w: dict(brain_deg=REAL[w]["trunk_deg"], neck=REAL[w]["q"]["neck_pitch"], head=REAL[w]["q"]["head_pitch"],
                            ankles=round((abs(REAL[w]["q"]["left_ankle"]) + abs(REAL[w]["q"]["right_ankle"])) / 2, 3)) for w in REAL})
    groups = collections.defaultdict(list)
    for r in data:
        groups[(r["plant"], r["imu_bias"])].append(r)
    table = []
    for (plant, bias), rs in groups.items():
        fell = [r["fell_at"] for r in rs if r["fell_at"] is not None]
        line = dict(plant=plant, bias=bias, n=len(rs), fell=fell, w={})
        tot = []
        for w in WINDOWS:
            have = [r["windows"][w] for r in rs if w in r["windows"]]
            if not have:
                continue
            rw = REAL[w]
            mean = lambda f: float(np.mean([f(x) for x in have]))
            dq_leg = math.sqrt(mean(lambda x: np.mean([(x["q"][n] - rw["q"][n]) ** 2 for n in legs])))
            dq_up = math.sqrt(mean(lambda x: np.mean([(x["q"][n] - rw["q"][n]) ** 2 for n in upper])))
            derr = math.sqrt(mean(lambda x: np.mean([(x["err"][n] - rw["err"][n]) ** 2 for n in legs + upper])))
            line["w"][w] = dict(brain_deg=round(mean(lambda x: x["brain_deg"]), 1), d_brain=round(mean(lambda x: x["brain_deg"]) - rw["trunk_deg"], 1),
                                true_deg=round(mean(lambda x: x["true_deg"]), 1), leg_rms=round(dq_leg, 3), up_rms=round(dq_up, 3), err_rms=round(derr, 3),
                                neck=round(mean(lambda x: x["q"]["neck_pitch"]), 3), head=round(mean(lambda x: x["q"]["head_pitch"]), 3),
                                cam_z=round(mean(lambda x: x["cam_z_mm"]), 1), floor_n=round(mean(lambda x: x["head_floor_n"]), 2),
                                q_range=round(mean(lambda x: x["q_range"]), 3))
            tot += [dq_leg, dq_up]
        line["score"] = round(float(np.mean(tot)), 3) if len(tot) == 6 and not fell else None
        table.append(line)
    table.sort(key=lambda x: (x["score"] is None, x["score"] or 0))
    for ln in table:
        print(f"\n{ln['plant']} bias {ln['bias']:.0f} n{ln['n']} score {ln['score']} fell {ln['fell']}")
        for w, v in ln["w"].items():
            print(f"  {w:7s} brain {v['brain_deg']:6.1f} (d {v['d_brain']:+5.1f}) true {v['true_deg']:6.1f} | leg rms {v['leg_rms']:.3f} up rms {v['up_rms']:.3f} err rms {v['err_rms']:.3f}"
                  f" | neck {v['neck']:+.3f} head {v['head']:+.3f} | cam z {v['cam_z']:6.1f} floor {v['floor_n']:.2f} N jitter {v['q_range']:.3f}")
            if ln["plant"] in detail:
                rs = groups[(ln["plant"], ln["bias"])]
                for n in ID_NAMES:
                    sq_ = np.mean([r["windows"][w]["q"][n] for r in rs])
                    se = np.mean([r["windows"][w]["err"][n] for r in rs])
                    print(f"      {n:16s} q sim {sq_:+.3f} real {REAL[w]['q'][n]:+.3f} d {sq_ - REAL[w]['q'][n]:+.3f} | err sim {se:+.3f} real {REAL[w]['err'][n]:+.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=None)
    ap.add_argument("--detail", default=None, help="with --report: comma list of plants to print per joint")
    ap.add_argument("--only", default=None, help="comma list of plant names")
    ap.add_argument("--biases", default=None)
    ap.add_argument("--seeds", default=None)
    ap.add_argument("--stop-at", type=float, default=None)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--out", default=os.path.join(HERE, "closed_loop_results.json"))
    a = ap.parse_args()
    if a.report:
        report(a.report)
        return
    plants = a.only.split(",") if a.only else list(PLANTS)
    biases = [float(x) for x in a.biases.split(",")] if a.biases else BIASES
    seeds = [int(x) for x in a.seeds.split(",")] if a.seeds else SEEDS
    jobs = [(p, b, s, a.stop_at) for p in plants for b in biases for s in seeds]
    t0, rows = time.time(), []
    if a.jobs > 1:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(a.jobs) as pool:
            it = pool.imap_unordered(run_case, jobs)
            for r in it:
                rows.append(r)
                print(r["plant"], r["imu_bias"], r["seed"], "fell", r["fell_at"], round(time.time() - t0), "s", flush=True)
                json.dump(dict(rows=rows, jobs=len(jobs)), open(a.out, "w"), indent=1)
    else:
        for j in jobs:
            r = run_case(j)
            rows.append(r)
            print(r["plant"], r["imu_bias"], r["seed"], "fell", r["fell_at"], round(time.time() - t0), "s", flush=True)
            json.dump(dict(rows=rows, jobs=len(jobs)), open(a.out, "w"), indent=1)
    print("done", len(rows), "in", round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    main()
