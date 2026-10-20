"""Open-loop stand pose study in the as-built MuJoCo model (2026-10-20). Sim only; never touches the robot.

The exact walk_brain.Brain stand mode is run: torque on at the present pose, a 2.0 s smoothstep ramp from the present
joint positions to walk_brain.STAND, then hold at KP_DEFAULT with no IMU feedback. A candidate pose is tested by
replacing walk_brain.STAND (the dict pi/stand_pose.py exports) in this process only. Sensor plumbing (encoder ticks,
BNO085 frame, one tick of sensor and action delay, dropped reads) is copied from brain_sim_check.run.

Model: brain_sim_check's as-built config (cfg 'asbuilt', BAM xl330 m6 actuators) with this folder's manifest copy
(asbuilt-20261020-manifest.json, build_manifest_copy.py). Supply and read drops from robot_state_check.py
--print-sim-args (CURRENT-STATE.json): --volt 7.0 --drop 0.04.

  ~/.venvs/microduck-dyn/bin/python stand_sim.py --selftest
Library use: run_case(...) -> dict (see its docstring).
"""
import collections
import json
import math
import os
import sys

SIM_PYTHON = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
if os.path.realpath(sys.prefix) != os.path.realpath(os.path.dirname(os.path.dirname(SIM_PYTHON))):
    os.execv(SIM_PYTHON, [SIM_PYTHON, os.path.abspath(__file__)] + sys.argv[1:])

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
sys.path.insert(0, MAC)
import brain_sim_check as bsc  # noqa: E402  (puts evaluate_delay, static_gap, walk_brain on the path)
import mujoco  # noqa: E402
import numpy as np  # noqa: E402
import walk_brain as wb  # noqa: E402

MANIFEST = os.path.join(HERE, "asbuilt-20261020-manifest.json")
LID = json.load(open(os.path.join(HERE, "lid-entry.json")))
PI_POS = [0.013898458364897247, -7.9141346850318e-08, -0.050467040423555716]  # add-pi (sole_thickness_sim.PI_POS)
NEUTRAL = dict(wb.NEUTRAL)
STAND_OBJ = wb.STAND  # the dict walk_brain.Brain reads; mutated per run, restored after
REAL_VOLT, REAL_DROP = 7.0, 0.04  # robot_state_check.py --print-sim-args, 2026-10-20

# backward-lean directions per joint (stance_poses_small.json: ankle_back03, hip_back, knee_back)
BACK = {"ankle": {"right_ankle": -1, "left_ankle": +1},
        "hip": {"right_hip_pitch": -1, "left_hip_pitch": +1},
        "knee": {"right_knee": +1, "left_knee": -1}}


def pose_from(delta):
    p = dict(NEUTRAL)
    for k, v in delta.items():
        p[k] += v
    return p


def back_delta(ankle=0.0, hip=0.0, knee=0.0):
    d = {}
    for grp, amt in (("ankle", ankle), ("hip", hip), ("knee", knee)):
        for j, s in BACK[grp].items():
            d[j] = d.get(j, 0.0) + s * amt
    return {k: round(v, 4) for k, v in d.items() if v}


def _load(kp, volt, friction, head_g, lid, cal=None):
    c0 = bsc.cfg(0.09, model="asbuilt", kp=kp, voltage=volt)
    c0["mass_manifest"] = MANIFEST
    parts = []
    if head_g:
        parts.append(dict(body="jaw_soft", mass_kg=head_g / 1000, position_m=PI_POS))
    if lid:
        parts.append(dict(body=LID["body"], mass_kg=LID["mass_kg"], position_m=LID["position_m"]))
    c0["mass_parts"] = parts
    if friction is not None:
        c0["friction"] = friction
    return bsc.ev.load(c0)


def run_case(target, start=None, kp=400, volt=REAL_VOLT, drop=REAL_DROP, friction=None, head_g=0.0, lid=False,
             T=60.0, push=None, walk_at=None, walk_s=10.0, lift=None, seed=0, trace_every=0.5, ramp_s=None):
    """target: 14-joint pose that replaces walk_brain.STAND. start: joint pose the robot stands in at t=0 with feet
    flat on the floor (default NEUTRAL); torque holds it, then stand mode ramps to target. push: (t, dv m/s along the
    world x the robot faces, positive forward, 0.1 s force on the trunk). walk_at: switch to walk mode at zero command
    (stand61) at that time for walk_s. lift: (t_lift, height_m, pitch_deg, hold_s) holds the trunk kinematically in the
    air from t_lift (feet free), from walk mode. ramp_s replaces the stand-entry ramp duration (walk_brain: 2.0 s) for
    a what-if; None keeps the Brain's own. Returns tilt trace and summary numbers."""
    start = dict(start or NEUTRAL)
    saved_stand, saved_kp = dict(STAND_OBJ), wb.KP_DEFAULT
    STAND_OBJ.update(target)
    wb.KP_DEFAULT = kp
    try:
        return _run(target, start, kp, volt, drop, friction, head_g, lid, T, push, walk_at, walk_s, lift, seed, trace_every, ramp_s)
    finally:
        STAND_OBJ.clear(); STAND_OBJ.update(saved_stand)
        wb.KP_DEFAULT = saved_kp


def _run(target, start, kp, volt, drop, friction, head_g, lid, T, push, walk_at, walk_s, lift, seed, trace_every, ramp_s):
    m, d, c, names, bam = _load(kp, volt, friction, head_g, lid)
    idx = {n: names.index(n) for n in wb.NAMES}
    p0 = np.array([start[n] for n in names])
    Rt = bsc.feet_flat_rot(m, d, names, start)
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, Rt.ravel())
    ji = bsc.setup(m, d, names, start, q)
    zmin = np.vstack(bsc.sole_points(m, d))[:, 2].min()
    d.qpos[2] -= zmin - 0.0005
    mujoco.mj_forward(m, d)
    qa, va = m.jnt_qposadr[ji], m.jnt_dofadr[ji]
    trunk = m.body("trunk_base").id
    gyro_adr = m.sensor("imu_ang_vel").adr[0]
    total_mass = float(m.body_subtreemass[0])
    c.q_target = p0.copy()
    bam.actuator.kp = kp
    brain = wb.Brain(bsc.MODELS, compensation=False, walk_ramp=0.0)
    sub = round(0.02 / m.opt.timestep)
    aq = collections.deque([p0.copy()] * 2, maxlen=2)
    sq = collections.deque(maxlen=2)
    rng = np.random.default_rng(seed)

    def pitch_deg():
        R = d.xmat[trunk].reshape(3, 3)
        return math.degrees(math.atan2(-R[2, 0], R[2, 2]))

    def tilt_deg():
        return math.degrees(math.acos(float(np.clip(d.xmat[trunk][8], -1, 1))))

    pitch0 = pitch_deg()
    x0 = float(d.xpos[trunk, 0])
    feet = [m.geom(g).id for g in ("left_foot_collision", "right_foot_collision")]
    foot0 = [d.geom_xpos[g].copy() for g in feet]
    trace, fell, max_tilt_after, max_tilt = [], None, 0.0, 0.0
    walk_stats = dict(max_action=0.0, jumps=0, max_goal_step=0.0, first_goal_jump=None, max_tilt=0.0)
    lift_stats = None
    prev_action, prev_goal, last_mode = None, None, None
    held = None
    q_sum, q_n = None, 0
    for tick in range(int(T / 0.02)):
        t = tick * 0.02
        q_trunk = d.qpos[3:7].copy()
        q_sensor = bsc.qmul(bsc.qmul(tuple(q_trunk), bsc.conj(wb.IMU_MOUNT_QUAT)), bsc.conj(wb.MOUNT_FIX))
        w_body = d.sensordata[gyro_adr:gyro_adr + 3].copy()
        g_sensor = bsc.apply(wb.MOUNT_FIX, bsc.apply(wb.IMU_MOUNT_QUAT, w_body))
        sample = (q_sensor, tuple(float(x) for x in g_sensor), d.qpos[qa].copy(), d.qvel[va].copy())
        if not sq:
            sq.extend([sample] * sq.maxlen)
        sq.append(sample)
        q_s, g_s, qm, dqm = sq[0]
        pos_t = [wb.to_tick(n, float(qm[idx[n]])) for n in wb.NAMES]
        vel_t = [int(round(float(dqm[idx[n]]) / wb.VEL_UNIT / wb.SIGN[n])) for n in wb.NAMES]
        walking = walk_at is not None and walk_at <= t < walk_at + walk_s
        want = {"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0} if walking else {"mode": "stand"}
        fresh = rng.random() >= drop
        goal, gkp, info = brain.tick(want, t, pos_t, vel_t, tuple(q_s), g_s, fresh, 0.024, 0.024)
        if ramp_s is not None and brain.ramp is not None and brain.ramp[3] == 2.0 and brain.ramp[0] == t:
            # what-if: the entry ramp started this tick; shorten it and recompute this tick's goal from it
            t0, a0, a1, _ = brain.ramp
            brain.ramp = (t0, a0, a1, ramp_s)
            sf = min(1.0, 0.0 / ramp_s)
            goal = {n: a0[n] + (a1[n] - a0[n]) * sf for n in wb.NAMES}
        if goal is not None:
            tgt = np.array([goal[n] for n in names])
            if gkp:
                bam.actuator.kp = gkp
        else:
            tgt = aq[-1].copy()
        if walking:
            if last_mode != "walk":
                walk_t0 = t
            if info["action"] is not None:
                a = np.array(info["action"])
                walk_stats["max_action"] = max(walk_stats["max_action"], float(np.abs(a).max()))
                if prev_action is not None and float(np.abs(a - prev_action).max()) > 0.5:
                    walk_stats["jumps"] += 1
                prev_action = a
            if prev_goal is not None:
                step = float(np.abs(tgt - prev_goal).max())
                walk_stats["max_goal_step"] = max(walk_stats["max_goal_step"], step)
            if t - walk_t0 <= 0.5:  # transient at takeover: largest goal move away from the held pose
                dev = float(np.abs(tgt - p_hold).max()) if last_mode == "walk" else 0.0
                walk_stats["first_goal_jump"] = max(walk_stats["first_goal_jump"] or 0.0, dev)
        if not walking and walk_at is not None and t < walk_at:
            p_hold = tgt.copy()
        last_mode = "walk" if walking else "stand"
        prev_goal = tgt.copy()
        aq.append(tgt.copy())
        c.q_target = aq[0]
        in_window = lift is not None and lift[0] <= t < lift[0] + lift[3]
        lifting = in_window and lift[1] > 0  # height 0: the same statistics window on the floor (reference)
        if in_window and lift_stats is None:
            lift_stats = dict(actions=[], qs=[], dqs=[])
        if lifting and held is None:
            held = d.qpos[0:7].copy()
            held[2] += lift[1]
            Rl = bsc.rot_y(lift[2])
            Rcur = d.xmat[trunk].reshape(3, 3)
            yaw = math.atan2(Rcur[1, 0], Rcur[0, 0])
            Rz = np.array([[math.cos(yaw), -math.sin(yaw), 0], [math.sin(yaw), math.cos(yaw), 0], [0, 0, 1]])
            qq = np.zeros(4)
            mujoco.mju_mat2Quat(qq, (Rz @ Rl).ravel())
            held[3:7] = qq
        for k in range(sub):
            if push is not None and push[0] <= t < push[0] + 0.1:
                d.xfrc_applied[trunk, 0] = total_mass * push[1] / 0.1
            else:
                d.xfrc_applied[trunk, 0] = 0.0
            if lifting:
                d.qpos[0:7] = held
                d.qvel[0:6] = 0.0
            c.update()
            mujoco.mj_step(m, d)
        if in_window:
            if info["action"] is not None:
                lift_stats["actions"].append(list(info["action"]))
            lift_stats["qs"].append(d.qpos[qa].tolist())
            lift_stats["dqs"].append(d.qvel[va].tolist())
        tl = tilt_deg()
        if not lifting:
            max_tilt = max(max_tilt, tl)
            if t >= 5.0:
                max_tilt_after = max(max_tilt_after, tl)
        if walking:
            walk_stats["max_tilt"] = max(walk_stats["max_tilt"], tl)
            if t - walk_t0 >= 3.0 and not lifting:  # settled stand61 stance (q as the encoders report it)
                q_sum = q_sum + d.qpos[qa] if q_sum is not None else d.qpos[qa].copy()
                q_n += 1
        if trace_every and tick % round(trace_every / 0.02) == 0:
            trace.append((round(t, 2), round(tl, 2), round(pitch_deg(), 2), round(float(d.xpos[trunk, 0]) - x0, 4)))
        if not lifting and (tl > 45 or d.xpos[trunk, 2] < 0.04):
            fell = round(t, 2)
            break
    slip = [round(float(np.linalg.norm((d.geom_xpos[g] - f0)[:2])) * 1000, 1) for g, f0 in zip(feet, foot0)]
    out = dict(ramp_s=ramp_s, kp=kp, volt=volt, drop=drop, friction=friction, head_g=head_g, lid=lid, T=T, push=push,
               start_pitch_deg=round(pitch0, 2), fell_at=fell, max_tilt=round(max_tilt, 2),
               max_tilt_after_5s=round(max_tilt_after, 2), end_tilt=round(tilt_deg(), 2), end_pitch=round(pitch_deg(), 2),
               trunk_dx_mm=round((float(d.xpos[trunk, 0]) - x0) * 1000, 1), foot_slip_mm=slip,
               total_mass_kg=round(total_mass, 4), trace=trace)
    if walk_at is not None:
        out["walk"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in walk_stats.items()}
        if q_n:
            out["walk"]["mean_q_delta_from_target"] = {n: round(float(q_sum[i] / q_n - target[n]), 4) for i, n in enumerate(names)}
            out["walk"]["mean_q_ticks"] = q_n
    if lift_stats is not None:
        A = np.array(lift_stats["actions"]) if lift_stats["actions"] else np.zeros((1, 14))
        Q = np.array(lift_stats["qs"]); DQ = np.array(lift_stats["dqs"])
        legs = [names.index(n) for n in names if n.startswith(("left_", "right_"))]
        jumps = int((np.abs(np.diff(A, axis=0)).max(axis=1) > 0.5).sum()) if len(A) > 1 else 0
        out["lift"] = dict(ticks=len(A), max_abs_action=round(float(np.abs(A).max()), 3),
                           mean_abs_action=round(float(np.abs(A).mean()), 3),
                           action_jumps_gt_0p5=jumps,
                           leg_joint_range_rad=round(float((Q[:, legs].max(0) - Q[:, legs].min(0)).max()), 3),
                           leg_joint_range_per_joint={names[i]: round(float(Q[:, i].max() - Q[:, i].min()), 3) for i in legs},
                           max_leg_speed_rad_s=round(float(np.abs(DQ[:, legs]).max()), 2),
                           rms_leg_speed_rad_s=round(float(np.sqrt((DQ[:, legs] ** 2).mean())), 2))
    return out


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        r = run_case(dict(NEUTRAL), T=10.0)
        r.pop("trace")
        print(json.dumps(r))
