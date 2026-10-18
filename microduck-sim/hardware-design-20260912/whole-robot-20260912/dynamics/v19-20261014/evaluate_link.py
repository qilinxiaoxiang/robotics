"""Measured-link variant of delay-repair-20260912/evaluate_delay.py (that file is imported, never edited).

Same model loading (load(): BAM XL330 at 5 V, KP 200, 1.47 A, signed mass parts), same policies (walk61 = BEST_alpha_
walking.onnx, stand61 = BEST_alpha_stand.onnx, sha256 identical), same command schedule (stand 0-2 s, 0.3 m/s with
heading hold gain 2 / limit 0.8 rad/s from 2 s to duration-2), same fall test and output fields, so
dynamics/run_compact_suite.grade() applies unchanged.

Difference: the state the policy sees and the moment a goal reaches the servos come from the reconstructed real
link timeline (link_timeline.py), not from constant tick queues. A sensor history is recorded every physics substep
(2.5 ms) and read back by linear interpolation at the real sample times, joints and IMU separately.

link_mode 'event': exact replay. The policy runs at every Mac receive (about 45 Hz, not 50 Hz) on the joint state
  sampled at s_j and the IMU state sampled at s_i; its goal is written only if and when the Pi applied that command,
  otherwise the previous goal is held (gaps of up to ~0.5 s exist in the window).
link_mode 'tick': the per-tick approximation. Every 20 ms the policy runs on state whose joint/IMU age equals the
  age of the goal that was in force at that instant on the real link; the goal applies immediately (no extra queue).
Compensation ('constant_velocity') mirrors guide/firmware/mac/walk_brain.py: joint age = median of the last 50
applied ages reported back by the Pi, IMU age = that + imu_age of the packet; joints and heading compensated with the
joint age, gyro/gravity with the IMU age. walk_brain's MAX_AGE = 40 ms hold is NOT applied here (see summary).
"""
from pathlib import Path
import argparse, json, math, sys, time
import numpy as np
import mujoco

HERE = Path(__file__).resolve().parent
DELAY = HERE.parents[1] / 'delay-repair-20260912'
sys.path.insert(0, str(DELAY)); sys.path.insert(0, str(HERE))
import evaluate_delay as ev  # noqa: E402
from compensation import compensate  # noqa: E402
import link_timeline as lt  # noqa: E402
import onnxruntime as ort  # noqa: E402

WINDOW_OFFSET_S = {0: 1.0, 9: 19.0, 42: 37.0}  # log window start per seed (log spans 68 s, runs 30 s)


class History:
    def __init__(self):
        self.t, self.x = [], []

    def add(self, t, x):
        self.t.append(t); self.x.append(np.array(x, float))

    def at(self, t):
        T = self.t
        if t <= T[0]:
            return self.x[0].copy()
        j = int(np.searchsorted(T, t))
        if j >= len(T):
            return self.x[-1].copy()
        a = (t - T[j - 1]) / (T[j] - T[j - 1])
        return (1 - a) * self.x[j - 1] + a * self.x[j]


def run(config, out):
    started = time.perf_counter()
    m, d, c, names, bam = ev.load(config)
    rng = np.random.default_rng(config.get('seed', 0))
    ji = np.array([m.actuator(n).trnid[0] for n in names]); qa = m.jnt_qposadr[ji]; va = m.jnt_dofadr[ji]
    trunk = m.body('trunk_base').id; gyro = m.sensor('imu_ang_vel').adr[0]
    d.qpos[:7] = [0, 0, .12, 1, 0, 0, 0]
    d.qpos[qa] = ev.HOME + rng.normal(0, config.get('joint_noise', .0), 14)
    mujoco.mj_forward(m, d); c.q_target = d.qpos[qa].copy()
    so = ort.SessionOptions(); so.intra_op_num_threads = 1; so.inter_op_num_threads = 1
    sessions = {k: ort.InferenceSession(str(ev.POLICY_DIR / f), sess_options=so, providers=['CPUExecutionProvider'])
                for k, f in [('walk', 'BEST_alpha_walking.onnx'), ('stand', 'BEST_alpha_stand.onnx')]}
    duration = config['duration']; dt_sub = m.opt.timestep; substeps = round(.02 / dt_sub)
    comp_on = config.get('delay_compensation', 'none') != 'none'
    cfg = {'delay_compensation': 'constant_velocity' if comp_on else 'none', 'prediction_fraction': 1.0,
           'predict_heading': True}

    tl = lt.build(HERE / config.get('link_log', 'link-log-last3000.jsonl'), config.get('rx_lag_cap_s'))
    T0 = tl['pi_t'][0] + WINDOW_OFFSET_S[config.get('seed', 0)]
    tau = lambda T: T - T0
    # applications known to the Mac (Pi reports applied_age back): (application time, age)
    app_idx = np.where(tl['applied'])[0]; app_t = tl['applied_at'][app_idx]; o = np.argsort(app_t)
    app_idx, app_t = app_idx[o], app_t[o]

    def predicted_ages(T_now, i_packet):
        j = np.searchsorted(app_t, T_now, side='right') - 1
        past = tl['applied_age'][app_idx[max(0, j - 49):j + 1]] if j >= 0 else np.array([])
        h = float(np.median(past)) if len(past) else 0.0
        return h, h + float(tl['imu_age'][i_packet])

    joint_hist, imu_hist = History(), History()

    def record(t):
        R = d.xmat[trunk].reshape(3, 3)
        g = R.T @ np.array([0, 0, -1.])
        yaw = math.atan2(R[1, 0], R[0, 0])
        imu_hist.add(t, np.r_[d.sensordata[gyro:gyro + 3], g, yaw])
        joint_hist.add(t, np.r_[d.qpos[qa] - ev.HOME, d.qvel[va]])

    last = np.zeros(14)
    yaw_unwrap = {'prev': 0.0, 'turns': 0.0}

    def policy(t_now, t_joint, t_imu, age_j, age_i):
        nonlocal last
        im = imu_hist.at(t_imu); jo = joint_hist.at(t_joint)
        state = np.r_[im[:6], jo]
        yaw = math.atan2(math.sin(im[6]), math.cos(im[6]))
        js, yaw_c = compensate(state, yaw, age_j, cfg)
        ims, _ = compensate(state, yaw, age_i, cfg)
        state = np.r_[ims[:6], js[6:]]
        cmd = np.zeros(13)
        if 2 <= t_now < duration - 2:
            cmd[:3] = config['command']
            cmd[2] = np.clip(-config.get('heading_gain', 2) * yaw_c, -config.get('heading_rate_limit', .8),
                             config.get('heading_rate_limit', .8))
        sess = sessions['walk'] if np.linalg.norm(cmd[:3]) > .001 else sessions['stand']
        obs = np.r_[state, last, cmd].astype(np.float32)
        last = sess.run(None, {sess.get_inputs()[0].name: obs[None]})[0].reshape(-1)
        return ev.HOME + last, cmd

    rows = []; fell = False; fall_time = None; bad_contact = 0; peak_current = 0; max_torque = 0
    ages_used = []; held_ticks = 0; n_policy = 0; cmd_now = np.zeros(13)
    record(0.0)
    mode = config['link_mode']
    # event lists (sim time)
    rx = [(tau(tl['r'][i]), i) for i in range(tl['n']) if 0 <= tau(tl['r'][i]) < duration]
    targets = {}
    rx_ptr = 0
    apps = sorted((tau(tl['applied_at'][i]), i) for i in range(tl['n'])
                  if tl['applied'][i] and 0 <= tau(tl['applied_at'][i]) < duration)
    app_ptr = 0
    series = lt.goal_age_series(tl, T0, duration) if mode == 'tick' else None
    last_applied_src = None
    pending = ev.HOME.copy()
    for tick in range(round(duration / .02)):
        t = tick * .02
        if mode == 'tick':
            # Same structure as evaluate_delay: the action computed now is written at the next tick (20 ms action
            # queue), and it is computed from state aged (real goal age at that next tick - 20 ms).
            s = series[min(tick + 1, len(series) - 1)]
            if config.get('fixed_age_s') is not None:  # validation hook: constant age, compare with evaluate_delay
                fa = config['fixed_age_s']
                s = dict(joint_age=fa, imu_age=fa, predicted_joint_age=fa - .02, predicted_imu_age=fa - .02)
            aj, ai = max(s['joint_age'] - .02, 0.0), max(s['imu_age'] - .02, 0.0)
            pj, pi_ = (s['predicted_joint_age'], s['predicted_imu_age'])
            c.q_target = pending.copy()
            pending, cmd_now = policy(t, t - aj, t - ai, pj, pi_); n_policy += 1
            ages_used.append((s['joint_age'], s['imu_age']))
        current_samples = []
        for sub in range(substeps):
            ts = t + sub * dt_sub
            if mode == 'event':
                while rx_ptr < len(rx) and rx[rx_ptr][0] <= ts:
                    tr, i = rx[rx_ptr]; rx_ptr += 1
                    pj, pi_ = predicted_ages(tl['r'][i], i)
                    targets[i], cmd_now = policy(tr, tau(tl['s_j'][i]), tau(tl['s_i'][i]), pj, pi_); n_policy += 1
                while app_ptr < len(apps) and apps[app_ptr][0] <= ts:
                    ta, i = apps[app_ptr]; app_ptr += 1
                    if i in targets:
                        c.q_target = targets[i].copy(); last_applied_src = i
                        ages_used.append((ta - tau(tl['s_j'][i]), ta - tau(tl['s_i'][i])))
            c.update(); mujoco.mj_step(m, d)
            record(ts + dt_sub)
            current_samples.append(float(np.sum(np.abs(d.ctrl)) / bam.kt.value))
            max_torque = max(max_torque, float(np.max(np.abs(d.actuator_force))))
        peak_current = max(peak_current, max(current_samples))
        tilt = math.degrees(math.acos(float(np.clip(d.xmat[trunk].reshape(3, 3)[2, 2], -1, 1))))
        if not np.all(np.isfinite(d.qpos)) or tilt > 60 or d.xpos[trunk, 2] < .04:
            fell = True
            if fall_time is None: fall_time = round(t + .02, 3)
        contact_pairs = []
        for contact in d.contact:
            ids = (int(contact.geom1), int(contact.geom2)); n = [m.geom(i).name for i in ids]
            if 'floor' in n:
                other = ids[1] if n[0] == 'floor' else ids[0]
                body = m.body(m.geom_bodyid[other]).name
                if body not in ('ankle_left', 'ankle_right'): bad_contact += 1
                contact_pairs.append(body)
        R = d.xmat[trunk].reshape(3, 3)
        rows.append({'time': round(t + .02, 4), 'x': float(d.xpos[trunk, 0]), 'y': float(d.xpos[trunk, 1]),
                     'height': float(d.xpos[trunk, 2]), 'tilt_deg': tilt, 'command': cmd_now[:3].tolist(),
                     'yaw_rad': math.atan2(R[1, 0], R[0, 0]), 'ground_bodies': sorted(set(contact_pairs)),
                     'motor_current_sum_proxy_a': float(np.mean(current_samples))})
        if fell: break
    moving = [r for r in rows if 3 <= r['time'] <= duration - 2]
    vx = (moving[-1]['x'] - moving[0]['x']) / (moving[-1]['time'] - moving[0]['time']) if len(moving) > 1 else None
    heading = None
    if len(moving) > 1:
        heading = float(np.max(np.abs(np.degrees(np.unwrap([r['yaw_rad'] for r in moving])))))
    warnings = [{'index': i, 'number': int(w.number)} for i, w in enumerate(d.warning) if w.number]
    au = np.array(ages_used) if ages_used else np.zeros((1, 2))
    result = {'config': config, 'mass_kg': float(sum(m.body_mass)), 'duration_completed_s': rows[-1]['time'],
              'fell': fell, 'fall_time_s': fall_time, 'max_tilt_deg': max(r['tilt_deg'] for r in rows),
              'mean_forward_velocity_m_s': vx, 'max_abs_heading_deviation_deg': heading,
              'peak_summed_motor_current_proxy_a': peak_current, 'max_actuator_torque_nm': max_torque,
              'nonfoot_ground_contact_samples': bad_contact, 'warnings': warnings,
              'policy_calls': n_policy, 'window_start_pi_t': T0,
              'applied_joint_age_ms': lt.stats(au[:, 0]), 'applied_imu_age_ms': lt.stats(au[:, 1]),
              'wall_seconds': time.perf_counter() - started, 'engine': mujoco.mj_versionString(), 'rows': rows}
    out.write_text(json.dumps(result) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'config')}), flush=True)
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('config', type=Path); ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args(); run(json.loads(a.config.read_text()), a.output)
