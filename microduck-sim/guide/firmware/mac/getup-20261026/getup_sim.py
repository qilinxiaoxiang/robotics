"""Get-up drops for walk_brain.Brain in the as-built MuJoCo model (the brain_sim_check.py plant, sensor path and delays).

The robot is laid on the floor face-down, face-up or seated (Pollen's standup-env reset poses, mjlab_microduck
microduck_standup_env_cfg.py / mdp.set_random_ground_state), let settle with its servos at KP 50 holding that pose, and
then handed to the Brain with {"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0} (stand61 at zero command). --start push
starts standing on stand61 and shoves the trunk over instead, so the fall itself (and the recover sequence's fall
predictor) is exercised.

walk_wired.py's stop guards are emulated: an action over --hard-max-action is clipped, and HARD over it within 10 ticks
(OVER_LIMIT_TICKS) stops into open-loop STAND, which counts as a failure ("guard"). The tilt stop is assumed disabled
(--max-tilt 180 on the robot), because any get-up passes 30 deg by construction.

Success: the trunk's true gravity z < -0.85 (31.8 deg) continuously for the last --up-hold s of the run and the trunk
above 0.08 m. up_after_s: from the walk command (push: from the moment the trunk passed 60 deg) to the start of the first
1 s stretch standing (gravity z < -0.85 and trunk above 0.10 m; it stands at 0.115 m). Loads: per joint the peak |actuator torque|, and
the time spent at >= 95 % of the BAM torque limit (stall at the rail voltage), i.e. the servo pushing at its limit.

  ~/.venvs/microduck-dyn/bin/python getup_sim.py --start face_down --getup nogate --seed 0
"""
import argparse
import collections
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
sys.path.insert(0, MAC)
sys.path.insert(0, os.path.join(MAC, "..", "pi"))
WHOLE = os.path.join(MAC, "..", "..", "..", "hardware-design-20260912", "whole-robot-20260912")
sys.path.insert(0, os.path.join(WHOLE, "dynamics", "realgap-20261014"))
sys.path.insert(0, os.path.join(WHOLE, "delay-repair-20260912"))
import evaluate_delay as ev  # noqa: E402
from static_gap import cfg, setup  # noqa: E402
import walk_brain  # noqa: E402
from walk_brain import IMU_MOUNT_QUAT, MOUNT_FIX, NAMES, OBSERVATION_DOF_ORDER, SIGN, VEL_UNIT, Brain, qmul, to_tick  # noqa: E402
from brain_sim_check import apply, conj, rot_y  # noqa: E402
from walk_wired import HARD_WINDOW, OVER_LIMIT_TICKS  # noqa: E402

MODELS = os.path.join(WHOLE, "runtime-overlay", "models")
SADDLE = os.path.join(MAC, "..", "..", "print", "a7z-saddle", "balance", "manifest-saddle.json")
# Pollen standup env SITTING_JOINT_OVERRIDES (policy joint order index -> rad); neck/head stay at HOME
SIT = {1: 0.0, 2: -0.4079, 3: 1.35, 4: 0.0, 10: 0.0, 11: 0.4079, 12: -1.35, 13: 0.0}
S2 = 2 ** -0.5


def quat_mul(a, b):
    return np.array(qmul(tuple(a), tuple(b)))


def axis_quat(axis, ang):
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    return np.array([math.cos(ang / 2)] + list(a * math.sin(ang / 2)))


def start_state(args, rng, home):
    """(joint pose dict, trunk quaternion) for the start pose; noise as Pollen's resets (sit joints 0.12 rad std,
    sit tilt +-10 deg, face-up roll about the spine) but narrower: --joint-noise and --roll-max."""
    pose = dict(home)
    yaw = axis_quat([0, 0, 1], rng.uniform(-math.pi, math.pi))
    if args.start == "face_down":
        q = quat_mul(yaw, np.array([S2, 0, S2, 0]))  # +90 deg pitch: belly to the floor
    elif args.start == "face_up":
        q = quat_mul(yaw, np.array([S2, 0, -S2, 0]))  # -90 deg pitch: back to the floor
        q = quat_mul(q, axis_quat([0, 0, 1], rng.uniform(-args.roll_max, args.roll_max)))  # log-roll about the spine
    elif args.start == "side":
        q = quat_mul(yaw, axis_quat([1, 0, 0], math.pi / 2 * (1 if rng.random() < 0.5 else -1)))
    elif args.start == "sitting":
        for k, v in SIT.items():
            pose[OBSERVATION_DOF_ORDER[k]] = v
        t = math.radians(10)
        q = quat_mul(yaw, quat_mul(axis_quat([0, 1, 0], rng.uniform(-t, t)), axis_quat([1, 0, 0], rng.uniform(-t, t))))
    else:  # standing (push)
        q = yaw
    for n in pose:
        pose[n] += rng.normal(0, args.joint_noise if args.start != "sitting" else max(args.joint_noise, 0.0))
        lo, hi = walk_brain.JOINT_RANGE[n]
        pose[n] = min(hi, max(lo, pose[n]))
    return pose, q


def place(m, d, names, pose, quat):
    """Pose the robot and lower it until its lowest collision point is 5 mm above the floor."""
    setup(m, d, names, pose, tuple(quat))
    floor = m.geom("floor").id
    d.qpos[2] = 0.5
    mujoco.mj_forward(m, d)
    lo = 1e9
    for g in range(m.ngeom):
        if g == floor or not (m.geom_contype[g] or m.geom_conaffinity[g]):
            continue
        if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH:
            mid = m.geom_dataid[g]
            v = m.mesh_vert[m.mesh_vertadr[mid]:m.mesh_vertadr[mid] + m.mesh_vertnum[mid]]
            w = v @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g]
            lo = min(lo, float(w[:, 2].min()))
        else:
            lo = min(lo, float(d.geom_xpos[g, 2] - m.geom_rbound[g]))
    d.qpos[2] -= lo - 0.005
    d.qvel[:] = 0
    mujoco.mj_forward(m, d)


def run(args):
    rng = np.random.default_rng(args.seed)
    if args.getup:
        walk_brain.GETUP = args.getup
    for k, v in (args.set or []):
        setattr(walk_brain, k, type(getattr(walk_brain, k))(v))
    c0 = cfg(0.09, model="asbuilt", kp=200, voltage=args.volt)
    c0["friction"] = args.floor_mu
    if args.manifest != "asbuilt":
        c0["mass_manifest"] = os.path.abspath(SADDLE if args.manifest == "saddle" else args.manifest)
    m, d, c, names, bam = ev.load(c0)
    idx = {n: names.index(n) for n in NAMES}
    brain = Brain(args.models, compensation=args.compensation, getup=args.getup)
    home = {n: brain.default[n] for n in names}
    pose, quat = start_state(args, rng, home)
    place(m, d, names, pose, quat)
    ji = np.array([m.actuator(n).trnid[0] for n in names])
    qa, va = m.jnt_qposadr[ji], m.jnt_dofadr[ji]
    trunk = m.body("trunk_base").id
    gyro_adr = m.sensor("imu_ang_vel").adr[0]
    act_id = [m.actuator(n).id for n in names]
    limit = float(m.actuator_forcerange[act_id[0], 1])
    Rimu = rot_y(args.imu_pitch)
    p_hold = np.array([pose[n] for n in names])
    c.q_target = p_hold.copy()
    bam.actuator.kp = args.settle_kp
    sub = round(0.02 / m.opt.timestep)
    aq = collections.deque([p_hold.copy()] * (args.action_delay + 1), maxlen=args.action_delay + 1)
    sq = collections.deque(maxlen=args.sensor_delay + 1)
    hard_hits = collections.deque(maxlen=HARD_WINDOW)
    guard_at, phases, rows = None, [], []
    peak_tau = np.zeros(14)
    sat_s = np.zeros(14)
    max_action, clipped = 0.0, 0
    up_run, up_at, fall_t = 0.0, None, None
    gz_hist = []
    T = args.settle_s + args.run_s
    cmd_at = args.settle_s
    push_done = False
    for tick in range(int(round(T / 0.02))):
        t = tick * 0.02
        q_trunk = d.qpos[3:7].copy()
        Rt = d.xmat[trunk].reshape(3, 3)
        gz_true = -float(Rt[2, 2])  # body-frame gravity z of the true trunk (upright -> -1)
        if args.imu_pitch:
            qp = np.zeros(4)
            mujoco.mju_mat2Quat(qp, Rimu.ravel())
            q_trunk = np.array(qmul(tuple(q_trunk), tuple(qp)))
        q_sensor = qmul(qmul(tuple(q_trunk), conj(IMU_MOUNT_QUAT)), conj(MOUNT_FIX))
        w_body = Rimu.T @ d.sensordata[gyro_adr:gyro_adr + 3]
        g_sensor = apply(MOUNT_FIX, apply(IMU_MOUNT_QUAT, w_body))
        sample = (q_sensor, tuple(float(x) for x in g_sensor), d.qpos[qa].copy(), d.qvel[va].copy())
        if not sq:
            sq.extend([sample] * sq.maxlen)
        sq.append(sample)
        q_sensor, g_sensor, qm, dqm = sq[0]
        pos_t = [to_tick(n, float(qm[idx[n]])) for n in NAMES]
        vel_t = [int(round(float(dqm[idx[n]]) / VEL_UNIT / SIGN[n])) for n in NAMES]
        if args.start == "push":
            want = {"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0}  # stand61 from the start
        else:
            want = {"mode": "monitor"} if t < cmd_at else {"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0}
        if guard_at is not None:
            want = {"mode": "stand"}
        fresh = rng.random() >= args.drop
        age = args.sensor_delay * 0.02 + 0.004
        goal, kp, info = brain.tick(want, t, pos_t, vel_t, tuple(q_sensor), g_sensor, fresh, age, age)
        act = info.get("action")
        if act is not None and brain.mode in Brain.POLICY_MODES and guard_at is None:
            amax = max(abs(a) for a in act)
            max_action = max(max_action, amax)
            hard_hits.append(amax > args.hard_max_action)
            if sum(hard_hits) >= OVER_LIMIT_TICKS:
                guard_at = round(t, 2)
            elif amax > args.hard_max_action:
                h = args.hard_max_action
                goal = walk_brain.clamp_goal({n: brain.default[n] + max(-h, min(h, float(act[k])))
                                              for k, n in enumerate(OBSERVATION_DOF_ORDER)})
                brain.goal = dict(goal)
                clipped += 1
        ph = info.get("getup")
        if ph and (not phases or phases[-1][1] != ph):
            phases.append((round(t, 2), ph))
        if goal is not None:
            target = np.array([goal[n] for n in names])
            if kp:
                bam.actuator.kp = kp
        else:
            target = aq[-1].copy()
        aq.append(target.copy())
        c.q_target = aq[0]
        if args.start == "push" and not push_done and t >= args.push_at:
            d.xfrc_applied[trunk, :3] = [args.push_n * math.cos(args.push_dir), args.push_n * math.sin(args.push_dir), 0]
        for _ in range(sub):
            c.update()
            mujoco.mj_step(m, d)
        if args.start == "push" and not push_done and t >= args.push_at + args.push_s:
            d.xfrc_applied[trunk, :3] = 0
            push_done = True
        tau = np.abs(d.actuator_force[act_id])
        live = t >= cmd_at - 1e-9 or args.start == "push"
        if live:
            peak_tau = np.maximum(peak_tau, tau)
            sat_s += (tau >= 0.95 * limit) * 0.02
        if fall_t is None and gz_true > -0.5 and (args.start == "push" or t >= cmd_at):
            fall_t = round(t, 2)  # push: the moment the trunk passed 60 deg (lying)
        ref = cmd_at if args.start != "push" else fall_t  # up time counts from the command, or from the fall
        upright = gz_true < -0.85 and float(d.xpos[trunk, 2]) > 0.10  # standing: trunk up and above a seat's 0.06 m
        up_run = up_run + 0.02 if upright else 0.0
        if up_at is None and ref is not None and up_run >= 1.0 - 1e-9 and t - 1.0 >= ref - 1e-9:
            up_at = round(t - 1.0 - ref, 2)
        gz_hist.append((t, gz_true, float(d.xpos[trunk, 2])))
        if args.trace and tick % 5 == 0:
            rows.append(dict(t=round(t, 2), gz=round(gz_true, 3), z=round(float(d.xpos[trunk, 2]), 3), mode=brain.mode,
                             getup=ph, kp=kp if not isinstance(kp, dict) else "hold",
                             action_max=None if act is None else round(max(abs(a) for a in act), 2),
                             tau_max=round(float(tau.max()), 3)))
    tail = [r for r in gz_hist if r[0] >= T - args.up_hold]
    ok = guard_at is None and all(r[1] < -0.85 for r in tail) and min(r[2] for r in tail) > 0.08 and \
        (args.start != "push" or fall_t is not None)  # a push that did not topple the robot proves nothing
    fell_after_up = None
    if up_at is not None:
        t_up = up_at + (cmd_at if args.start != "push" else fall_t) + 1.0
        fell_after_up = any(r[1] > -0.5 for r in gz_hist if r[0] > t_up)
    out = dict(start=args.start, getup=walk_brain.GETUP if args.getup is None else args.getup, seed=args.seed,
               models=os.path.relpath(args.models, HERE), manifest=args.manifest, volt=args.volt, drop=args.drop,
               imu_pitch=args.imu_pitch, push=[args.push_n, round(args.push_dir, 3)] if args.start == "push" else None,
               fell=fall_t is not None if args.start == "push" else None, fall_t=fall_t, success=bool(ok), up_after_s=up_at, fell_after_up=fell_after_up,
               guard_stop_at=guard_at, clipped_ticks=clipped, max_action=round(max_action, 2),
               final_gz=round(gz_hist[-1][1], 3), final_trunk_z=round(gz_hist[-1][2], 3),
               start_gz=round(gz_hist[0][1], 3), torque_limit_nm=round(limit, 3),
               peak_tau_nm={n: round(float(peak_tau[i]), 3) for i, n in enumerate(names)},
               sat_s={n: round(float(sat_s[i]), 2) for i, n in enumerate(names) if sat_s[i] > 0},
               sat_s_total=round(float(sat_s.sum()), 2), sat_s_max_joint=round(float(sat_s.max()), 2),
               phases=phases, end_mode=brain.mode, end_getup=None if brain.getup is None else brain.getup["phase"],
               set=dict(args.set or []))
    if args.trace:
        out["trace"] = rows
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", choices=("face_down", "face_up", "side", "sitting", "push"), required=True)
    ap.add_argument("--getup", choices=walk_brain.GETUP_MODES, default=None, help="Brain getup mode (default: DUCK_GETUP)")
    ap.add_argument("--models", default=MODELS)
    ap.add_argument("--manifest", default="saddle", help="saddle (A7Z roof saddle, D-022 balance manifest), asbuilt, or a path")
    ap.add_argument("--volt", type=float, default=None, help="default: servo_rail_v in microduck-sim/CURRENT-STATE.json")
    ap.add_argument("--drop", type=float, default=None, help="default: servo_read_drop_fraction in CURRENT-STATE.json")
    ap.add_argument("--imu-pitch", type=float, default=0.0)
    ap.add_argument("--compensation", action="store_true")
    ap.add_argument("--sensor-delay", type=int, default=1)
    ap.add_argument("--action-delay", type=int, default=1)
    ap.add_argument("--floor-mu", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--joint-noise", type=float, default=0.05, help="rad std on every joint of the start pose")
    ap.add_argument("--roll-max", type=float, default=math.radians(30), help="face-up roll about the spine, +- rad")
    ap.add_argument("--settle-s", type=float, default=1.5, help="s lying at KP --settle-kp before the walk command")
    ap.add_argument("--settle-kp", type=int, default=50)
    ap.add_argument("--run-s", type=float, default=12.0, help="s simulated after the walk command")
    ap.add_argument("--up-hold", type=float, default=2.0, help="s at the end that must all be upright")
    ap.add_argument("--hard-max-action", type=float, default=3.0, help="walk_wired --hard-max-action")
    ap.add_argument("--push-at", type=float, default=2.0)
    ap.add_argument("--push-s", type=float, default=0.15)
    ap.add_argument("--push-n", type=float, default=8.0, help="N on the trunk")
    ap.add_argument("--push-dir", type=float, default=0.0, help="rad in the world xy plane (0 = +x)")
    ap.add_argument("--set", nargs=2, action="append", metavar=("CONST", "VALUE"), help="override a walk_brain constant")
    ap.add_argument("--trace", action="store_true")
    args = ap.parse_args()
    state = json.load(open(os.path.join(MAC, "..", "..", "..", "CURRENT-STATE.json")))["facts"]
    if args.volt is None:
        args.volt = float(state["servo_rail_v"]["value"])
    if args.drop is None:
        args.drop = float(state["servo_read_drop_fraction"]["value"])
    print(json.dumps(run(args)))


if __name__ == "__main__":
    main()
