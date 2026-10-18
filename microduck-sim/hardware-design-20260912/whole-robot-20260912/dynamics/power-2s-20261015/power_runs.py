"""Servo-rail supply current of the MicroDuck (15 x XL330-M288-T) on a 2S LiPo bus, from the as-built V1.9 sim.

Setup is realgap-20261014/policy_test.py and sitstand_volt.py (imported helpers, rollout loops copied so each 2.5 ms
sim step can be logged): V1.9 mass model with 90 g battery removal, BAM xl330 m6 actuators, KP 200 for the policies,
KP 400 for the static STAND hold, 50 Hz policy, one tick sensor and one tick action delay, nominal COM, seed 0.

Per sim step it logs the BAM motor torque (d.actuator_force, the electromagnetic torque kt*I before the separately
modelled gearbox friction) and the joint speed the BAM controller used for that step. analyse() turns them into bus
current with a DC motor model; see README.md.

  ~/.venvs/microduck-dyn/bin/python power_runs.py          # all cases, writes results.json (about 2 min, 4 workers)
"""
import collections, json, math, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np, mujoco, onnxruntime as ort

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'realgap-20261014'))
import policy_test as pt  # noqa: E402  (also puts delay-repair-20260912 on sys.path)
from static_gap import cfg, NAMES, HOME, STAND, feet_flat_rot, sole_points, setup  # noqa: E402
import evaluate_delay as ev  # noqa: E402

H = np.array([HOME[n] for n in NAMES])
DT_TICK = 0.02
ETA_DRIVER = 0.9            # H-bridge + PCB efficiency, assumed
STANDBY_A = 15 * 0.017      # 15 servos x 17 mA standby (ROBOTIS XL330-M288 e-manual)
GROUPS = {'left_leg': slice(0, 5), 'head_neck': slice(5, 9), 'right_leg': slice(9, 14)}  # NAMES order
LEG_CURRENT_JSON = (HERE.parents[3] / 'guide/content/interference-audit/open-issues/evidence/leg-current.json')


def build(volt, kp, current_limit, com_x_mm=0.0):
    c0 = cfg(0.09, kp=kp, voltage=volt, current_limit=current_limit)
    if com_x_mm:  # same 50 g trunk shift as policy_test.run
        c0['mass_parts'] = [dict(body='trunk_base', mass_kg=-0.05, position_m=[0, 0, 0.0]),
                            dict(body='trunk_base', mass_kg=0.05, position_m=[com_x_mm / 1000 * 0.76 / 0.05, 0, 0.0])]
    m, d, c, names, bam = ev.load(c0)
    assert names == NAMES, names
    return m, d, c, names, bam


def place_feet_flat(m, d, names, pose):
    Rt = feet_flat_rot(m, d, names, pose); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel())
    ji = setup(m, d, names, pose, q)
    zmin = np.vstack(sole_points(m, d))[:, 2].min(); d.qpos[2] -= zmin - 0.0005; mujoco.mj_forward(m, d)
    return ji


class Log:
    def __init__(self, c, m):
        self.act = np.array(c.act_indexes); self.dof = np.array(c.dof_indexes)
        self.feet = [m.body('ankle_left').id, m.body('ankle_right').id]
        self.t, self.tau, self.dq, self.fz = [], [], [], []; self.clip = 0.0

    def step(self, m, d, c):
        """One BAM update + one MuJoCo step, logged."""
        c.update()
        dq = d.qvel[self.dof].copy()       # speed the BAM model used for this step's voltage and current
        mujoco.mj_step(m, d)
        tau = d.actuator_force[self.act].copy()
        self.clip = max(self.clip, float(np.abs(d.ctrl[self.act] - tau).max()))  # forcerange clipping, expect 0
        self.t.append(d.time); self.tau.append(tau); self.dq.append(dq); self.fz.append(d.xpos[self.feet, 2].copy())

    def arrays(self):
        return np.array(self.t), np.array(self.tau), np.array(self.dq), np.array(self.fz)


def tilt_deg(d, trunk):
    return math.degrees(math.acos(np.clip(d.xmat[trunk].reshape(3, 3)[2, 2], -1, 1)))


def policy_rollout(volt, vx=None, wz=0.0, T=10.0, walk_at=3.0, walk_s=10.0, kp=200, current_limit=1.47, seed=0,
                   kick_s=0.0, kick_vx=0.3):
    """policy_test.run with no injected gaps: STAND feet flat, stand61 from t=0; walk61 at vx in [walk_at, walk_at+walk_s).
    kick_s > 0: walk61 runs at kick_vx for kick_s seconds before walk_at, then switches to vx (walk61 only starts
    stepping at vx >= 0.25 in this model, so this is how a lower or zero command is reached while stepping)."""
    m, d, c, names, bam = build(volt, kp, current_limit)
    p0 = np.array([STAND[n] for n in names])
    ji = place_feet_flat(m, d, names, dict(zip(names, p0)))
    qa, va = m.jnt_qposadr[ji], m.jnt_dofadr[ji]
    trunk = m.body('trunk_base').id; gyro = m.sensor('imu_ang_vel').adr[0]
    so = ort.SessionOptions(); so.intra_op_num_threads = 1
    sess = {k: ort.InferenceSession(str(pt.MODELS / f'{k}61.onnx'), sess_options=so) for k in ('walk', 'stand')}
    last = np.zeros(14); aq = collections.deque([p0.copy()] * 2, maxlen=2); sq = collections.deque(maxlen=2)
    c.q_target = p0.copy(); sub = round(DT_TICK / m.opt.timestep)
    log = Log(c, m); fell = None; maxtilt = 0.0; x0 = None
    for tick in range(int(round(T / DT_TICK))):
        t = tick * DT_TICK
        R = d.xmat[trunk].reshape(3, 3)
        s = np.r_[d.sensordata[gyro:gyro + 3], R.T @ np.array([0, 0, -1.]), d.qpos[qa] - H, d.qvel[va]]
        if not sq: sq.extend([s] * sq.maxlen)
        sq.append(s); s = sq[0]
        kicking = vx is not None and walk_at - kick_s <= t < walk_at
        walking = kicking or (vx is not None and walk_at <= t < walk_at + walk_s)
        cmd = np.zeros(13)
        if walking: cmd[0] = kick_vx if kicking else vx; cmd[2] = wz
        k = 'walk' if walking else 'stand'
        last = sess[k].run(None, {sess[k].get_inputs()[0].name: np.r_[s, last, cmd].astype(np.float32)[None]})[0].reshape(-1)
        aq.append(H + last); c.q_target = aq[0].copy()
        for _ in range(sub): log.step(m, d, c)
        tl = tilt_deg(d, trunk); maxtilt = max(maxtilt, tl)
        if vx is not None and t >= walk_at and x0 is None: x0 = float(d.xpos[trunk, 0])
        if tl > 45 or d.xpos[trunk, 2] < 0.04: fell = round(t, 2); break
    dist = None if x0 is None else round(float(d.xpos[trunk, 0]) - x0, 3)
    return dict(log=log, bam=bam, fell_at=fell, max_tilt=round(maxtilt, 1), dist_x=dist, sub=sub)


def static_rollout(volt, T=5.0, kp=400, current_limit=1.47, com_x_mm=0.0, zero=None):
    """ramp_test-style KP 400 hold of STAND_POSE (stand.py on the robot); zero = joint calibration error (deg)."""
    zero = zero or {}
    m, d, c, names, bam = build(volt, kp, current_limit, com_x_mm)
    z0 = np.array([math.radians(zero.get(n, 0)) for n in names])
    p0 = np.array([STAND[n] for n in names])
    place_feet_flat(m, d, names, dict(zip(names, p0 + z0)))
    trunk = m.body('trunk_base').id
    c.q_target = p0 + z0; log = Log(c, m); fell = None; maxtilt = 0.0; gx = None
    for _ in range(int(round(T / m.opt.timestep))):
        log.step(m, d, c)
        tl = tilt_deg(d, trunk); maxtilt = max(maxtilt, tl)
        if fell is None and tl > 45: fell = round(d.time, 2); break
    gx = float((d.xmat[trunk].reshape(3, 3).T @ np.array([0, 0, -1.]))[0])
    return dict(log=log, bam=bam, fell_at=fell, max_tilt=round(maxtilt, 1), gravity_x_end=round(gx, 3))


def sitstand_rollout(volt, T=8.0, kp=200, current_limit=1.47):
    """sitstand_volt.run: SIT keyframe, community BEST_alpha_sitstand, sit command 1 s then stand."""
    m, d, c, names, bam = build(volt, kp, current_limit)
    k = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_KEY, 'SIT'); mujoco.mj_resetDataKeyframe(m, d, k); mujoco.mj_forward(m, d)
    ji = np.array([m.actuator(n).trnid[0] for n in names]); qa, va = m.jnt_qposadr[ji], m.jnt_dofadr[ji]
    trunk = m.body('trunk_base').id; gy = m.sensor('imu_ang_vel').adr[0]
    s = ort.InferenceSession(str(ev.POLICY_DIR / 'BEST_alpha_sitstand.onnx')); last = np.zeros(14)
    c.q_target = d.qpos[qa].copy(); sub = round(DT_TICK / m.opt.timestep); log = Log(c, m); zs = []
    for tick in range(int(round(T / DT_TICK))):
        t = tick * DT_TICK; R = d.xmat[trunk].reshape(3, 3)
        cmd = np.zeros(13); cmd[0] = 1.0 if t < 1.0 else 0.0
        obs = np.r_[d.sensordata[gy:gy + 3], R.T @ [0, 0, -1.], d.qpos[qa] - H, d.qvel[va], last, cmd].astype(np.float32)
        last = s.run(None, {s.get_inputs()[0].name: obs[None]})[0].reshape(-1); c.q_target = H + last
        for _ in range(sub): log.step(m, d, c)
        if tick % 25 == 0: zs.append((round(t, 1), round(float(d.xpos[trunk, 2]), 3), round(tilt_deg(d, trunk), 1)))
    return dict(log=log, bam=bam, final_z=zs[-1][1], final_tilt=zs[-1][2], trace_z=zs[::2])


def rolling_max(x, n):
    if len(x) < n: return float('nan')
    c = np.cumsum(np.r_[0.0, x]); return float(((c[n:] - c[:-n]) / n).max())


def stats(x, step):
    n = lambda s: max(1, int(round(s / step)))
    return dict(mean=round(float(x.mean()), 4), max_1s=round(rolling_max(x, n(1.0)), 4),
                max_100ms=round(rolling_max(x, n(0.1)), 4), max_20ms=round(rolling_max(x, n(0.02)), 4),
                peak_step=round(float(x.max()), 4))


def analyse(t, tau, dq, fz, kt, R, vbus, window):
    """DC motor model per motor: I = tau/kt, V_m = I*R + ke*omega (ke = kt in SI), P = V_m*I.
    bus = sum(max(P, 0)) / V_bus / eta + standby. proxy = sum(|I|) (motor current, what Present Current reports)."""
    w = (t > window[0] + 1e-9) & (t <= window[1] + 1e-9)
    tau, dq, fz = tau[w], dq[w], fz[w]; step = float(np.median(np.diff(t)))
    I = tau / kt; Vm = I * R + kt * dq; P = Vm * I
    bus = np.clip(P, 0, None).sum(1) / vbus / ETA_DRIVER + STANDBY_A
    bus_shared = np.clip(P.sum(1), 0, None) / vbus / ETA_DRIVER + STANDBY_A   # regen of one motor feeds another
    proxy = np.abs(I).sum(1)
    out = dict(window_s=list(window), samples=int(w.sum()), sample_step_s=step,
               bus_current_a=stats(bus, step), proxy_sum_abs_motor_current_a=stats(proxy, step),
               bus_current_regen_shared_a=stats(bus_shared, step),
               mean_electrical_power_w=round(float(np.clip(P, 0, None).sum(1).mean()), 3),
               mean_copper_loss_w=round(float((I ** 2 * R).sum(1).mean()), 3),
               mean_mech_power_out_w=round(float((kt * dq * I).sum(1).mean()), 3),
               mean_regen_w=round(float(np.clip(P, None, 0).sum(1).mean()), 3),
               max_terminal_voltage_v=round(float(np.abs(Vm).max()), 3),
               max_motor_current_a=round(float(np.abs(I).max()), 3),
               groups={})
    for g, sl in GROUPS.items():
        out['groups'][g] = dict(
            bus_current_mean_a=round(float(np.clip(P[:, sl], 0, None).sum(1).mean() / vbus / ETA_DRIVER), 4),
            proxy_mean_a=round(float(np.abs(I[:, sl]).sum(1).mean()), 4),
            proxy_max_1s_a=round(rolling_max(np.abs(I[:, sl]).sum(1), int(round(1.0 / step))), 4))
    out['per_joint_mean_abs_current_a'] = {n: round(float(v), 4) for n, v in zip(NAMES, np.abs(I).mean(0))}
    out['per_joint_mean_signed_current_a'] = {n: round(float(v), 4) for n, v in zip(NAMES, I.mean(0))}
    lift = fz - np.percentile(fz, 5, axis=0)   # foot (ankle body) height above its stance level
    out['gait'] = dict(foot_lift_max_mm=[round(float(x) * 1000, 1) for x in lift.max(0)],
                       liftoffs_over_5mm=[int(np.sum((lift[1:, i] > 0.005) & (lift[:-1, i] <= 0.005))) for i in (0, 1)],
                       leg_joint_speed_rms_rad_s=round(float(np.sqrt((dq[:, list(range(5)) + list(range(9, 14))] ** 2).mean())), 3))
    return out


CASES = {}
for V in (7.4, 6.6, 8.2):
    CASES[f'{V}V-stand61'] = ('policy', dict(volt=V, vx=None, T=10.0), [(0, 10), (2, 10)])
    for vx in (0.0, 0.15, 0.3):   # margins.py convention: stand61 3 s from STAND, then walk61 10 s
        CASES[f'{V}V-walk61-vx{vx}'] = ('policy', dict(volt=V, vx=vx, T=13.0), [(3, 13)])
    for vx in (0.0, 0.1, 0.15):   # walk61 at 0.3 for 2 s to start stepping, then vx for 10 s
        CASES[f'{V}V-walk61-kick-vx{vx}'] = ('policy', dict(volt=V, vx=vx, T=15.0, walk_at=5.0, kick_s=2.0), [(5, 15)])
    CASES[f'{V}V-sitstand'] = ('sitstand', dict(volt=V, T=8.0), [(0, 8), (1, 4)])
for nm in ('walk61-vx0.3', 'sitstand'):  # firmware default Current Limit 1750 mA instead of the 1.47 A sim default
    kind, kw, win = CASES[f'7.4V-{nm}']
    CASES[f'7.4V-{nm}-limit1.75A'] = (kind, dict(kw, current_limit=1.75), win)
CASES['5.0V-stand61'] = ('policy', dict(volt=5.0, vx=None, T=10.0), [(0, 10), (2, 10)])
CASES['5.0V-walk61-vx0.3'] = ('policy', dict(volt=5.0, vx=0.3, T=13.0), [(3, 13)])
CASES['5.0V-static-STAND-kp400-nominal'] = ('static', dict(volt=5.0, T=5.0), [(0, 5), (2, 5)])
CASES['5.0V-static-STAND-kp400-com+10mm'] = ('static', dict(volt=5.0, T=5.0, com_x_mm=10), [(0, 5), (2, 5)])
CASES['5.0V-static-STAND-kp400-hip+8deg'] = ('static', dict(volt=5.0, T=5.0, zero={'left_hip_pitch': -8, 'right_hip_pitch': 8}), [(0, 5), (2, 5)])


def go(name):
    kind, kw, wins = CASES[name]; t0 = time.time()
    r = dict(policy=policy_rollout, static=static_rollout, sitstand=sitstand_rollout)[kind](**kw)
    log, bam = r.pop('log'), r.pop('bam'); r.pop('sub', None)
    t, tau, dq, fz = log.arrays()
    kt, R = float(bam.kt.value), float(bam.R.value)
    end = float(t[-1]) if len(t) else 0.0
    res = dict(kind=kind, args={k: v for k, v in kw.items()}, outcome=r, sim_end_s=round(end, 3),
               forcerange_clip_max_nm=round(log.clip, 6), wall_s=round(time.time() - t0, 1), windows={})
    for a, b in wins:
        if end >= b - 1e-6:
            res['windows'][f'{a}-{b}s'] = analyse(t, tau, dq, fz, kt, R, kw['volt'], (a, b))
    return name, res


HEADLINE = [  # (label, case, window)
    ('stand61 hold 10 s', 'stand61', '0-10s'), ('stand61 steady (2-10 s)', 'stand61', '2-10s'),
    ('walk61 vx 0 from STAND (does not step)', 'walk61-vx0.0', '3-13s'),
    ('walk61 vx 0.15 from STAND (does not step)', 'walk61-vx0.15', '3-13s'),
    ('walk61 vx 0.1 after 2 s at 0.3 (slowest stepping)', 'walk61-kick-vx0.1', '5-15s'),
    ('walk61 vx 0.15 after 2 s at 0.3 (steps)', 'walk61-kick-vx0.15', '5-15s'),
    ('walk61 vx 0.3 from STAND', 'walk61-vx0.3', '3-13s'),
    ('sit-to-stand 8 s', 'sitstand', '0-8s'), ('sit-to-stand rise (1-4 s)', 'sitstand', '1-4s')]


def summarize(cases):
    rows = []
    for V in (7.4, 6.6, 8.2):
        for label, case, win in HEADLINE:
            w = cases[f'{V}V-{case}']['windows'][win]; b = w['bus_current_a']
            o = cases[f'{V}V-{case}']['outcome']
            rows.append(dict(volt=V, case=label, bus_mean_a=b['mean'], bus_max_1s_a=b['max_1s'], bus_max_100ms_a=b['max_100ms'],
                             bus_max_20ms_a=b['max_20ms'], proxy_mean_a=w['proxy_sum_abs_motor_current_a']['mean'],
                             group_bus_mean_a={g: x['bus_current_mean_a'] for g, x in w['groups'].items()},
                             group_proxy_mean_a={g: x['proxy_mean_a'] for g, x in w['groups'].items()},
                             dist_x_m=o.get('dist_x'), liftoffs=w['gait']['liftoffs_over_5mm']))
    return rows


def main():
    t0 = time.time(); out = {}
    with ProcessPoolExecutor(4) as ex:
        for name, res in ex.map(go, CASES):
            out[name] = res
            w = next(iter(res['windows'].values()), None)
            print(name, res['outcome'], res['wall_s'], 's',
                  None if w is None else (w['bus_current_a'], w['proxy_sum_abs_motor_current_a']['mean']), flush=True)
    bam = ev.load_model(motor_name='xl330', model='m6') if hasattr(ev, 'load_model') else None
    meta = dict(
        date='2026-10-15', interpreter=sys.executable, wall_s=round(time.time() - t0, 1),
        model='as-built V1.9 (v19-mass-manifest.json, 90 g old battery removed), nominal COM, seed 0',
        actuator=dict(package='better_actuator_models 1.0.1 (bam), xl330 m6',
                      kt_nm_per_a=float(bam.kt.value) if bam else None, R_ohm=float(bam.R.value) if bam else None,
                      ke_v_s_per_rad='= kt (SI)', current_limit_a_default=1.47, kp_policy=200, kp_static=400),
        bus_model=dict(eta_driver=ETA_DRIVER, standby_a=STANDBY_A,
                       formula='I=tau/kt; V_m=I*R+kt*omega; P=V_m*I; I_bus=sum(max(P,0))/V_bus/eta + 15*0.017 A'),
        windows='rolling means over the 2.5 ms sim steps: 1 s = 400, 100 ms = 40, 20 ms = 8 samples; peak_step = one step',
        measured_reference=dict(stand_pose_hold_5v_sum_abs_present_current_a=0.165, date='2026-10-13',
                                source='guide/firmware/pi/stand.py hold, KP 400, jaw torque-off; sum |Present Current| of 14 servos'))
    real = None
    if Path('/tmp/duck_wired_log.jsonl').exists():
        import stand_log_check
        sys.argv = sys.argv[:1]; real = stand_log_check.main()
    json.dump(dict(meta=meta, summary=summarize(out), real_stand_log_check=real, cases=out),
              open(HERE / 'results.json', 'w'), indent=1)
    print('wall', round(time.time() - t0, 1), 's')


if __name__ == '__main__':
    main()
