"""Flight simulation of the MicroDuck with the four-EDF pack: hover, floor -> table, table -> floor, throttle cut.

Robot: the as-built MuJoCo model (official scene + battery-20261104 manifest) with the flight-pack parts of
sim/out/manifest_pack_<variant>.json, loaded through cmu/whole/delay-repair-20260912/evaluate_delay.load, so the 14
servos are the project's BAM XL330 model (here holding the stand pose at KP 400, servo rail 7.6 V from CURRENT-STATE).
Nacelle collision boxes and a 0.75 m table are added. Thrust, rotor torques and battery are modelled here; the
controller is a stand-in with the structure of ArduPilot Copter (position -> velocity -> lean angle, altitude ->
climb rate -> collective, angle -> rate PID at 400 Hz, a mixer for the real fan geometry). It is NOT ArduPilot.

  $PY sim/flight.py --scenario hover|table_up|table_down|cut [--case-flags ...] --out row.json [--log log.npz] [--video f.mp4]
"""
import argparse
import json
import math
import os
import sys
from pathlib import Path

import mujoco
import numpy as np

H = Path(__file__).resolve().parent
FL = H.parent
SIMROOT = FL.parents[1]
RL = SIMROOT / "microduck_rl"
CMU = RL / "cmu"
sys.path.insert(0, str(CMU / "whole" / "delay-repair-20260912"))
sys.path.insert(0, str(CMU / "whole" / "dynamics" / "realgap-20261014"))
sys.path.insert(0, str(CMU / "pi"))
sys.path.insert(0, str(FL / "cad"))
import evaluate_delay as ev  # noqa: E402
from static_gap import cfg, feet_flat_rot, setup, sole_points  # noqa: E402
from stand_pose import STAND_POSE  # noqa: E402

FP = None
try:
    import flight_params as FP  # noqa: E402  (needs cad-practice/print_fit)
except Exception:
    FP = None

STATE = json.loads((SIMROOT / "CURRENT-STATE.json").read_text())["facts"]
SERVO_V = float(STATE["servo_rail_v"]["value"])          # 7.6 V, verified 2026-11-06
G = 9.81

# ---------------------------------------------------------------- fan (vendor point: racer.lt QX table, read 2026-11-10)
T_REF = 0.950 * G      # N, 950 g at 16.2 V, 34 A, 550.8 W, QF2611 4000KV 50 mm 12-blade
V_REF, P_REF, I_REF = 16.2, 550.8, 34.0
W_REF = 4000 * 16.2 * 0.9 * 2 * math.pi / 60   # rad/s at full throttle, loaded (KV x V x 0.9), estimate
FAN_POINTS = {
    "qx": dict(T=0.950, V=16.2, P=550.8, I=34.0, KV=4000),     # racer.lt QX table (read 2026-11-10)
    # ARESWEI HDS001 50 mm 11-blade 4650KV, seller claim 980 g and 40 A at 16.8 V (procurement.json fan_change_2026_11_10)
    "areswei": dict(T=0.980, V=16.8, P=16.8 * 40.0, I=40.0, KV=4650),
}


def set_fan(name):
    """Switch the module's vendor point (thrust, voltage, power, speed) to another fan."""
    global T_REF, V_REF, P_REF, I_REF, W_REF
    f = FAN_POINTS[name]
    T_REF, V_REF, P_REF, I_REF = f["T"] * G, f["V"], f["P"], f["I"]
    W_REF = f["KV"] * f["V"] * 0.9 * 2 * math.pi / 60


ETA_MOTOR = 0.85       # shaft / electrical power, estimate
J_ROTOR = 4e-6         # kg m2 rotor + fan, estimate (no data)
ESC_LIMIT_A = 55.0     # MicoAir AM32 per channel continuous
PACK_C, PACK_MAH = 130.0, 1300.0
# fan geometry (trunk frame = CAD guide frame, m); 1 RF CCW, 2 LR CCW, 3 LF CW, 4 RR CW (design page, ArduPilot QUAD X)
if FP is not None:      # read from the CAD (cad/flight_params.py)
    CANT = math.radians(FP.CANT_DEG); FAN_Y = FP.FAN_Y / 1000; LIP_TOP_Z = FP.LIP_TOP_Z / 1000; LIP_OD = FP.FAN["lip_od"] / 1000
    FAN_X = {k: v / 1000 for k, v in FP.FAN_X.items()}
else:                   # fallback copy of the 2026-11-10 values
    CANT = math.radians(6.0); FAN_Y = 0.110; LIP_TOP_Z = 0.075; LIP_OD = 0.063
    FAN_X = {"front": 0.020, "rear": -0.044}
DIR = {"front": +1, "rear": -1}
LIP_Z = LIP_TOP_Z - LIP_OD / 2 * math.sin(CANT)
FANS = []
for name, which, side, spin in (("1 RF", "front", -1, +1), ("2 LR", "rear", +1, +1), ("3 LF", "front", +1, -1), ("4 RR", "rear", -1, -1)):
    a = np.array([-DIR[which] * math.sin(CANT), 0.0, math.cos(CANT)])      # thrust direction (exhaust is -a)
    FANS.append(dict(name=name, p=np.array([FAN_X[which], side * FAN_Y, LIP_Z]), a=a, spin=spin))

# ---------------------------------------------------------------- battery: 2 x CNHL 4S 1300 130C in parallel
SOC_PTS = np.array([0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
OCV_CELL = np.array([3.30, 3.50, 3.62, 3.70, 3.75, 3.79, 3.83, 3.87, 3.93, 4.00, 4.08, 4.19])   # generic LiPo curve (estimate)


class Battery:
    def __init__(self, soc=1.0, r_pack=0.020, r_common=0.005):
        self.soc, self.r_pack, self.r_common = soc, r_pack, r_common
        self.mah = 0.0

    def ocv(self):
        return 4 * float(np.interp(self.soc, SOC_PTS, OCV_CELL))

    def solve(self, p_w):
        """Bus voltage and total current for an electrical load p_w (W)."""
        e, r = self.ocv(), self.r_pack / 2 + self.r_common
        disc = e * e - 4 * p_w * r
        if disc <= 0:
            return e / 2, e / (2 * r)          # collapsed: maximum power point
        v = (e + math.sqrt(disc)) / 2
        return v, p_w / v

    def drain(self, i_total, dt):
        self.mah += i_total * dt / 3.6
        self.soc = max(0.0, self.soc - i_total * dt / 3.6 / (2 * PACK_MAH))


class FanSet:
    def __init__(self, thrust_scale=1.0, weak=None, weak_frac=0.85, tau=0.10, tau_down=None, resid=0.3):
        self.scale = np.full(4, thrust_scale)
        if weak is not None:
            self.scale[weak] *= weak_frac
        self.tau_up, self.tau_down = tau, (tau_down or tau)
        self.resid = resid
        self.power_scale = 1.0     # electrical power for the same thrust (1 / efficiency relative to the vendor point)
        self.w = np.zeros(4)

    def step(self, u, v_bus, dt):
        w_ss = np.clip(u, 0, 1) * W_REF * v_bus / V_REF
        tau = np.where(w_ss > self.w, self.tau_up, self.tau_down)
        dw = (w_ss - self.w) * dt / tau
        self.w = self.w + dw
        r = self.w / W_REF
        T = T_REF * self.scale * r ** 2
        P = self.power_scale * P_REF * r ** 3 + J_ROTOR * self.w * np.maximum(dw / dt, 0) / ETA_MOTOR
        q_aero = ETA_MOTOR * P_REF * r ** 3 / np.maximum(self.w, 1.0)          # rotor drag torque, N m
        q_body = self.resid * q_aero + J_ROTOR * dw / dt                        # on the housing; stators recover the rest
        return T, P, q_body


# ---------------------------------------------------------------- scene with table and nacelle collision boxes
def write_scene(out):
    spec = mujoco.MjSpec.from_file(str(ev.MODEL_DIR / "scene.xml"))
    spec.meshdir = str((ev.MODEL_DIR / "assets").resolve())
    floor = spec.geom("floor"); floor.conaffinity = 5
    spec.worldbody.add_geom(name="table", type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.40, 0.50, 0.375], pos=[5.0, 0, 0.375],
                            contype=1, conaffinity=5, rgba=[0.55, 0.42, 0.3, 1])
    tb = spec.body("trunk_base")
    for side in (+1, -1):   # nacelle + fan envelope (cad/build nacelle bounds, guide frame): x -86..62, |y| 70..140, z -5..65
        tb.add_geom(name=f"nacelle_box_{'L' if side > 0 else 'R'}", type=mujoco.mjtGeom.mjGEOM_BOX,
                    size=[0.074, 0.035, 0.035], pos=[-0.012, side * 0.105, 0.030], contype=4, conaffinity=4, mass=0,
                    rgba=[0.9, 0.5, 0.1, 0.4], group=3)
    Path(out).write_text(spec.to_xml())
    return out


# ---------------------------------------------------------------- controller stand-in (ArduPilot Copter structure)
class Controller:
    """Cascade: position P -> velocity PI -> lean angle; altitude P -> climb PI -> collective; angle P -> rate PID -> torque;
    mixer with roll/pitch priority over yaw and collective. Gains set for a fan lag of 0.1 s (the controller does not
    re-tune itself unless --retune)."""

    def __init__(self, mass_est, I_est, com_est, tau_nom=0.10, wn=8.0):
        self.m, self.I, self.com = mass_est, np.array(I_est), np.array(com_est)
        wn = min(wn, 0.8 / tau_nom); z = 0.8
        self.kp_att = np.array([wn * wn, wn * wn, (0.6 * wn) ** 2])
        self.kd_att = np.array([2 * z * wn, 2 * z * wn, 2 * z * 0.6 * wn])
        self.ki_att = 0.3 * self.kp_att
        self.i_att = np.zeros(3)
        self.i_lim = np.array([0.97, 0.32, 0.12]) / np.maximum(self.ki_att * self.I, 1e-9)
        self.kp_pos, self.kp_vel, self.ki_vel = 0.9, 1.6, 0.4
        self.kp_z, self.kp_vz, self.ki_vz = 1.3, 3.0, 1.5
        self.i_vel, self.i_vz = np.zeros(2), 0.0
        self.lean_max = math.radians(20)
        B = np.zeros((4, 4))
        for i, f in enumerate(FANS):
            r = f["p"] - self.com
            M = np.cross(r, f["a"]) + (-f["spin"]) * 0.3 * ETA_MOTOR * P_REF / W_REF / T_REF * f["a"]   # per N of thrust
            B[:, i] = [f["a"][2], M[0], M[1], M[2]]
        self.B, self.Binv = B, np.linalg.inv(B)

    def mix(self, Fz, M, t_max):
        t_min = 0.03 * t_max
        base = self.Binv @ np.array([Fz, 0, 0, 0])
        rp = self.Binv @ np.array([0, M[0], M[1], 0])
        yw = self.Binv @ np.array([0, 0, 0, M[2]])
        T = base + rp
        # roll/pitch first: move collective to fit, then scale roll/pitch if they alone do not fit
        lo, hi = T.min(), T.max()
        if hi - lo > t_max - t_min:
            s = (t_max - t_min) / (hi - lo + 1e-9); rp *= s; T = base + rp; lo, hi = T.min(), T.max()
        if hi > t_max: T -= hi - t_max
        if lo < t_min: T += t_min - lo
        # yaw with what is left
        room_up, room_dn = t_max - T, T - t_min
        k = 1.0
        for i in range(4):
            if yw[i] > 0: k = min(k, room_up[i] / yw[i])
            elif yw[i] < 0: k = min(k, room_dn[i] / -yw[i])
        T = T + max(0.0, k) * yw
        return np.clip(T, t_min, t_max), (hi - lo > t_max - t_min) or k < 1.0

    def attitude(self, q_des_rpy, rpy, gyro, dt, freeze_i=False):
        e = np.array(q_des_rpy) - np.array(rpy)
        e[2] = (e[2] + math.pi) % (2 * math.pi) - math.pi
        if not freeze_i:
            # integrator limit as a moment (ArduPilot ATC_RAT_*_IMAX style): up to about half the hover authority
            # (roll 0.97, pitch 0.32 N m; sim/out/authority.json); the earlier 0.3 rad s clip capped the trim at 0.07 N m
            self.i_att = np.clip(self.i_att + e * dt, -self.i_lim, self.i_lim)
        acc = self.kp_att * e - self.kd_att * gyro + self.ki_att * self.i_att
        return self.I * acc


def rpy_of(R):
    roll = math.atan2(R[2, 1], R[2, 2]); pitch = math.asin(-max(-1, min(1, R[2, 0]))); yaw = math.atan2(R[1, 0], R[0, 0])
    return np.array([roll, pitch, yaw])


# ---------------------------------------------------------------- main run
def run(a):
    rng = np.random.default_rng(a.seed)
    scene = H / "out" / "scene_flight.xml"
    if not scene.exists():
        write_scene(scene)
    c0 = cfg(0.09, model="asbuilt", kp=a.kp, voltage=SERVO_V)
    # the visual copy: same mass parts plus the pack's visual_parts (drawn only; sim/pack_visual.py)
    import pack_visual
    c0["mass_manifest"] = str(pack_visual.with_visuals(H / "out" / f"manifest_pack_{a.mass_variant}.json"))
    c0["scene"] = str(scene)
    m, d, c, names, bam = ev.load(c0)
    dt = m.opt.timestep
    trunk = m.body("trunk_base").id
    table = m.geom("table").id; floor = m.geom("floor").id
    nac = {m.geom("nacelle_box_L").id, m.geom("nacelle_box_R").id}
    feet = {m.geom("left_foot_collision").id, m.geom("right_foot_collision").id}
    leg_act = [i for i, n in enumerate(names) if any(k in n for k in ("hip", "knee", "ankle"))]
    limit = float(m.actuator_forcerange[0, 1])
    # start pose: the Brain's stand pose, feet flat, on the floor or on the table
    pose = dict(STAND_POSE)
    for side, sgn in (("left", +1), ("right", -1)):      # mirrored joints: same physical rotation on both legs
        pose[f"{side}_ankle"] += sgn * math.radians(a.trim_ankle)
        pose[f"{side}_hip_pitch"] += sgn * math.radians(a.trim_hip)
        pose[f"{side}_knee"] += sgn * math.radians(a.trim_knee)
    p0 = np.array([pose[n] for n in names])
    Rt = feet_flat_rot(m, d, names, dict(zip(names, p0)))
    q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel())
    ji = setup(m, d, names, dict(zip(names, p0)), q)
    on_table = a.scenario == "table_down"
    tx = a.table_gap + 0.40   # table centre x: near edge --table-gap ahead of the floor start, 0.8 m deep
    if a.scenario in ("table_up", "table_down"):
        m.geom_pos[table] = [tx, 0, 0.375]
    if on_table:
        d.qpos[0] = a.table_gap + 0.30          # standing 0.30 m inside the edge
    mujoco.mj_forward(m, d)
    zmin = np.vstack(sole_points(m, d))[:, 2].min()
    d.qpos[2] -= zmin - (0.75 if on_table else 0.0) - 0.0005
    mujoco.mj_forward(m, d)
    if a.rigid_legs:      # diagnostic: every leg joint locked at the held pose by a zero-width joint limit (no servo compliance)
        for n in names:
            if any(k in n for k in ("hip", "knee", "ankle")):
                j = m.joint(n).id; qv = float(d.qpos[m.jnt_qposadr[j]])
                m.jnt_range[j] = [qv - 1e-4, qv + 1e-4]; m.jnt_limited[j] = 1
    if a.floor_mu is not None:   # diagnostic: sliding friction of floor and table
        m.geom_friction[floor, 0] = a.floor_mu; m.geom_friction[table, 0] = a.floor_mu
        for g in feet: m.geom_friction[g, 0] = a.floor_mu
    if a.start_air:       # diagnostic: start airborne at this feet height, zero velocity, fans at hover speed
        d.qpos[2] += a.start_air
        if a.air_level:
            d.qpos[3:7] = [1.0, 0.0, 0.0, 0.0]
        mujoco.mj_forward(m, d)
    c.q_target = p0.copy()
    M = float(m.body_mass[1:].sum())
    surface0 = 0.75 if on_table else 0.0
    # controller's model of itself: nominal manifest numbers (it does not know the perturbation)
    rep = json.loads((H / "out" / "mass_report.json").read_text())["duck_with_pack"]
    I = rep["inertia_about_com_kgm2"]
    com_est = np.array(rep["com_trunk_mm"]) / 1000
    if a.com_est == "true":   # the controller knows the nominal robot's COM in this start pose (a calibrated hover trim)
        R0_ = d.xmat[trunk].reshape(3, 3)
        com_est = R0_.T @ (d.subtree_com[trunk] - d.xpos[trunk])
        full = json.loads((H / "out" / "mass_report.json").read_text())
        if a.mass_variant.startswith(("mass", "com")):   # an unknown perturbation: subtract it again
            com_est = com_est - (np.array(full["variants"][a.mass_variant]["com_trunk_mm"]) - np.array(rep["com_trunk_mm"])) / 1000
    ctl = Controller(mass_est=rep["mass_g"] / 1000, I_est=[I["xx"], I["yy"], I["zz"]],
                     com_est=com_est, tau_nom=(a.tau if a.retune else 0.10), wn=a.wn)
    ctl.lean_max = math.radians(a.lean_max)
    fans = FanSet(thrust_scale=a.thrust, weak=a.weak_fan, tau=a.tau, resid=a.resid)
    fans.power_scale = a.power_scale
    bat = Battery(soc=a.soc, r_pack=a.r_pack)
    # sensors: gyro/attitude at 400 Hz with delay; rangefinder + flow at 50 Hz with 30 ms; yaw (A7Z ExternalNav) 50 Hz 40 ms
    n_att = max(1, int(round((0.0025 + a.sensor_delay) / dt)))
    n_rng = max(1, int(round((0.030 + a.sensor_delay) / dt)))
    hist = []
    gyro_bias = rng.normal(0, 0.005, 3)
    GG = np.array([1, 0, 0, 0, 0, 0], dtype=np.uint8)          # rays see group 0 only: floor and table
    MTF = np.array([-0.086, -0.059, 0.006])                     # MTF-01 lens, trunk frame (cad dummy_mtf01)
    R0 = d.xmat[trunk].reshape(3, 3)
    SENS0 = float((d.xpos[trunk] + R0 @ MTF)[2]) - surface0 - a.start_air   # sensor height above the surface when standing
    z_est, vz_est, surf_est = surface0 + SENS0 + a.start_air, 0.0, surface0
    com0_z = float(d.subtree_com[trunk][2]) - a.start_air
    if a.start_air:
        fans.w[:] = math.sqrt(M * G / 4 / (T_REF * a.thrust)) * W_REF
    qlog = []
    x_est = np.zeros(2); v_est = np.zeros(2)
    flow_v = np.zeros(2); rng_meas = None; rng_jumps = []
    # mission
    # hover: 6 + hover_s timed out at 80-90 % thrust from the ground (slower climb)
    T_end = {"hover": 10.0 + a.hover_s, "table_up": 20.0, "table_down": 20.0, "cut": 9.0}[a.scenario]
    armed_at, armed = a.arm_at, False
    phase = "idle"; t_phase = 0.0
    land_t = None; disarm_t = None; contact_t = None; spool = 0.0
    start_xy = d.qpos[0:2].copy()
    tgt = dict(z=surface0, x=0.0, y=0.0)
    # targets are feet heights above the floor (world), flown as rangefinder-sensor heights (+SENS0)
    hover_alt = {"hover": 0.30, "table_up": 1.00, "table_down": 1.00, "cut": a.cut_alt}[a.scenario] + SENS0
    tgt["z"] = surface0 + SENS0
    # relative to start: table_up lands 0.30 m inside the near edge; table_down lands 0.40 m in front of it
    x_goal = {"table_up": a.table_gap + 0.30, "table_down": -0.70}.get(a.scenario, 0.0)
    yaw0 = rpy_of(d.xmat[trunk].reshape(3, 3))[2]
    pitch_rest = rpy_of(d.xmat[trunk].reshape(3, 3))[1]   # trunk pitch of the held pose with the feet flat (+4.1 deg at ankle trim -4)
    log = []
    stats = dict(max_tilt=0.0, max_yaw=0.0, i_pack_peak=0.0, i_esc_peak=0.0, sat_s=0.0, nacelle_hit=None, vz_touch=None,
                 leg_tau_peak=0.0, leg_tau_peak_joint=None, u_hover=[], i_hover=[], fell=None, rng_jumps=0, z_max=0.0)
    i_sum, i_n = 0.0, 0
    first_air = None
    acc_hist = []
    gust = None
    if a.gust:
        gust = dict(t0={"hover": 5.0, "table_up": 6.5, "table_down": 6.5, "cut": 99}[a.scenario], dur=0.5, f=a.gust)
    steps = int(T_end / dt)
    for k in range(steps):
        t = k * dt
        R = d.xmat[trunk].reshape(3, 3)
        rpy = rpy_of(R)
        gyro_b = d.qvel[3:6].copy()   # free-joint angular velocity is in the body frame
        com = d.subtree_com[trunk].copy()
        mujoco.mj_subtreeVel(m, d)
        vcom = d.subtree_linvel[trunk].copy()
        hist.append((rpy + rng.normal(0, [0.003, 0.003, 0.005]), gyro_b + gyro_bias + rng.normal(0, 0.02, 3)))
        if len(hist) > 400: hist.pop(0)
        rpy_s, gyro_s = hist[-min(len(hist), n_att)]
        # vertical: accel integration (truth accel + noise) corrected by rangefinder + tracked surface height
        az = float(d.qacc[2]) + rng.normal(0, 0.3)
        vz_est += az * dt; z_est += vz_est * dt
        if k % 8 == 0 and k >= n_rng:      # 50 Hz range + flow samples, delayed
            past = log_state[(k - n_rng) % len(log_state)] if k > 0 else None
            if past is not None:
                rng_true, vxy_true, tilt_c = past
                r_m = rng_true + rng.normal(0, 0.01)
                h = z_est - r_m * tilt_c
                if abs(h - surf_est) > 0.25 and not a.naive_range:
                    rng_jumps.append(round(t, 2)); surf_est = h          # surface step (table edge): keep altitude, re-base surface
                if a.naive_range:
                    surf_est = 0.0 if not on_table else surface0
                    z_meas = r_m * tilt_c + surf_est
                else:
                    z_meas = r_m * tilt_c + surf_est
                e = z_meas - z_est
                z_est += 0.25 * e; vz_est += 2.0 * e * 0.02
                flow_v = vxy_true + rng.normal(0, 0.03, 2)
        # flow position (drifts)
        v_est = flow_v; x_est = x_est + v_est * dt
        # truth range below the MTF-01 (x -0.086, y -0.059, z 0.006 trunk frame), along body -z
        p_s = d.xpos[trunk] + R @ MTF
        geomid = np.array([-1], dtype=np.int32)
        dist = mujoco.mj_ray(m, d, p_s, -R[:, 2], GG, 1, trunk, geomid)
        rng_true = dist if dist >= 0 else 8.0
        vxy_true = vcom[:2]
        if k == 0:
            log_state = [None] * 64
        log_state[k % 64] = (min(rng_true, 8.0), vxy_true.copy(), float(R[2, 2]))
        # ---- mission state machine
        surface_now = surf_est
        hs = z_est - surf_est - SENS0       # estimated feet height above the surface below
        if not armed and a.start_air:       # airborne start: the mission continues from the climb (hover: climb to 0.3 m, hold)
            armed, phase, t_phase = True, "climb", t
            tgt["z"] = surface0 + SENS0 + a.start_air
        if not armed and t >= armed_at:
            armed, phase, t_phase = True, "spool", t
        if phase == "spool" and t - t_phase > a.spool_s:
            phase, t_phase = "climb", t
        if phase == "climb":
            tgt["z"] = min(hover_alt, tgt["z"] + 0.5 * dt)
            if z_est > hover_alt - 0.05 and tgt["z"] >= hover_alt:
                phase, t_phase = "hold1", t
        if phase == "hold1" and t - t_phase > 1.0:
            phase, t_phase = ("cut" if a.scenario == "cut" else "move" if a.scenario in ("table_up", "table_down") else "hover"), t
        if phase == "move":
            dx = x_goal - tgt["x"]; step = math.copysign(min(abs(dx), 0.3 * dt), dx); tgt["x"] += step
            if abs(x_goal - tgt["x"]) < 1e-6 and t - t_phase > 1.0 and abs(x_goal - x_est[0]) < 0.08:
                phase, t_phase = "hold2", t
            if t - t_phase > 8.0:
                phase, t_phase = "hold2", t
        if phase == "hold2" and t - t_phase > 1.5:
            phase, t_phase = "land", t
        if phase == "hover" and t - t_phase > a.hover_s:
            phase, t_phase = "land", t
        if phase == "land":
            tgt["z"] -= 0.30 * dt                                    # ArduPilot LAND_SPEED minimum 30 cm/s
            if land_t is None: land_t = t
            # land detector stand-in: commanded descent but measured climb rate > -0.08 m/s for 0.2 s
            if vz_est > -0.08 and t - t_phase > 0.5:
                contact_t = contact_t or t
                if t - contact_t > 0.2:
                    phase, t_phase = "spooldown", t
                    ctl.i_att[:] = 0; ctl.i_vel[:] = 0
            else:
                contact_t = None
        if phase == "spooldown" and t - t_phase > a.settle_s + a.spool_down:
            phase, disarm_t = "disarmed", t
        # ---- control
        v_bus_prev = getattr(bat, "v_last", bat.ocv())
        t_max_est = T_REF * (v_bus_prev / V_REF) ** 2
        if phase in ("idle", "disarmed", "cut"):
            u = np.zeros(4)
        else:
            yaw = rpy_s[2]
            if False:
                pass
            else:
                # horizontal (yaw frame)
                ex = np.array([tgt["x"], tgt["y"]]) - x_est
                vd = np.clip(ctl.kp_pos * ex, -0.5, 0.5)
                ev_ = vd - v_est
                on_ground = (phase == "spool") or (phase == "climb" and first_air is None)
                if not on_ground:
                    ctl.i_vel = np.clip(ctl.i_vel + ev_ * dt, -0.5, 0.5)
                acc = ctl.kp_vel * ev_ + ctl.ki_vel * ctl.i_vel
                cy, sy = math.cos(yaw), math.sin(yaw)
                ab = np.array([cy * acc[0] + sy * acc[1], -sy * acc[0] + cy * acc[1]])
                pitch_d = float(np.clip(math.atan2(ab[0], G), -ctl.lean_max, ctl.lean_max))
                roll_d = float(np.clip(-math.atan2(ab[1], G), -ctl.lean_max, ctl.lean_max))
                if on_ground:
                    if a.ground_pitch == "rest":
                        pitch_d, roll_d = pitch_rest, 0.0      # take off from the attitude the held legs stand at
                    elif a.ground_pitch == "level":
                        pitch_d, roll_d = 0.0, 0.0
                    else:                                      # "track": follow the measured attitude, rate damping only
                        pitch_d, roll_d = rpy_s[1], rpy_s[0]
                if phase == "land" and a.flare_h > 0:
                    w = float(np.clip(1 - hs / a.flare_h, 0, 1))   # touch down in the attitude the held legs stand at, feet flat
                    pitch_d = (1 - w) * pitch_d + w * pitch_rest
                if phase == "spooldown":
                    roll_d, pitch_d = 0.0, pitch_rest          # landed: hold the standing attitude while the weight goes onto the feet
                # vertical
                vzd = np.clip(ctl.kp_z * (tgt["z"] - z_est), -0.4, 0.6)
                if phase == "land":
                    vzd = -0.30
                if phase == "spooldown":
                    vzd = -0.5
                evz = vzd - vz_est
                ctl.i_vz = float(np.clip(ctl.i_vz + evz * dt, -3, 3)) if phase not in ("spooldown",) else ctl.i_vz
                azd = ctl.kp_vz * evz + ctl.ki_vz * ctl.i_vz
                tilt_c = max(0.5, math.cos(rpy_s[0]) * math.cos(rpy_s[1]))
                Fz = ctl.m * (G + azd) / tilt_c
                if phase == "spool":   # spool up to 40 % of the weight with the attitude loop holding the standing attitude
                    Fz = ctl.m * G * a.spool_frac * min(1.0, (t - t_phase) / a.spool_s)
                if phase == "climb" and on_ground:   # then leave the floor fast (thrust ramp to takeoff_twr x weight in 0.25 s)
                    Fz = ctl.m * G * min(a.takeoff_twr, a.spool_frac + (a.takeoff_twr - a.spool_frac) * (t - t_phase) / a.takeoff_ramp)
                if phase == "spooldown":
                    # fans carry spool_down_frac of the weight with the attitude loop on for settle_s, then ramp to zero
                    Fz = ctl.m * G * a.spool_down_frac * max(0.0, 1 - max(0.0, t - t_phase - a.settle_s) / a.spool_down)
                Mb = ctl.attitude([roll_d, pitch_d, yaw0], rpy_s, gyro_s, dt, freeze_i=on_ground or phase == "spooldown")
                T, sat = ctl.mix(Fz, Mb, t_max_est)
                if sat: stats["sat_s"] += dt
                u = np.sqrt(np.clip(T / t_max_est, 0, 1))
        # ---- plant: fans, battery, forces
        P_guess = getattr(bat, "p_last", 0.0)
        v_bus, i_tot = bat.solve(P_guess + 7.0)        # 7 W avionics (FC, flow, BEC), estimate
        bat.v_last = v_bus
        Tf, Pf, Qf = fans.step(u, v_bus, dt)
        bat.p_last = float(Pf.sum())
        bat.drain(i_tot, dt)
        F = np.zeros(3); Tq = np.zeros(3)
        for i, f in enumerate(FANS):
            pw = d.xpos[trunk] + R @ f["p"]; aw = R @ f["a"]
            Fi = Tf[i] * aw
            F += Fi; Tq += np.cross(pw - d.xipos[trunk], Fi) + (-f["spin"]) * Qf[i] * aw
        if gust and gust["t0"] <= t < gust["t0"] + gust["dur"]:
            F += np.array([0.0, gust["f"], 0.0])
        d.xfrc_applied[trunk, 0:3] = F; d.xfrc_applied[trunk, 3:6] = Tq
        c.update()
        mujoco.mj_step(m, d)
        # ---- readback
        tilt = math.degrees(math.acos(max(-1, min(1, R[2, 2]))))
        ycur = math.degrees(((rpy[2] - yaw0 + math.pi) % (2 * math.pi)) - math.pi)
        airborne = d.subtree_com[trunk][2] - com0_z > 0.03
        if airborne and first_air is None: first_air = t
        if phase not in ("idle", "spool", "disarmed") or (a.scenario == "cut" and phase == "cut"):
            stats["max_tilt"] = max(stats["max_tilt"], tilt); stats["max_yaw"] = max(stats["max_yaw"], abs(ycur))
        stats["z_max"] = max(stats["z_max"], float(com[2]))
        if phase == "hover":
            stats["hover_drift"] = max(stats.get("hover_drift", 0.0), float(np.hypot(*(d.qpos[0:2] - start_xy))))
            stats["hover_pitch"] = max(stats.get("hover_pitch", 0.0), abs(math.degrees(rpy[1])))
        if phase in ("spool", "climb", "hold1"):
            stats["takeoff_drift"] = max(stats.get("takeoff_drift", 0.0), float(np.hypot(*(d.qpos[0:2] - start_xy))))
            if phase != "hold1":
                stats["takeoff_pitch"] = max(stats.get("takeoff_pitch", 0.0), abs(math.degrees(rpy[1] - pitch_rest)))
        i_pack = i_tot / 2
        stats["i_pack_peak"] = max(stats["i_pack_peak"], i_pack)
        stats["i_esc_peak"] = max(stats["i_esc_peak"], float((Pf / v_bus).max()))
        if armed and phase not in ("disarmed",):
            i_sum += i_tot; i_n += 1
        if phase == "hover" or (phase in ("hold1", "hold2") and t - t_phase > 0.5):
            stats["u_hover"].append(float(u.mean())); stats["i_hover"].append(i_tot)
        # contacts
        touch_feet = touch_nac = False
        for j in range(d.ncon):
            g1, g2 = d.contact[j].geom1, d.contact[j].geom2
            other = g2 if g1 in (floor, table) else g1 if g2 in (floor, table) else None
            if other is None: continue
            if other in nac: touch_nac = True
            if other in feet: touch_feet = True
        if touch_nac and stats["nacelle_hit"] is None and first_air is not None:
            stats["nacelle_hit"] = round(t, 3)
        if (first_air is not None and touch_feet and stats["vz_touch"] is None and t > first_air + 0.3
                and phase in ("land", "spooldown", "disarmed", "cut")):
            stats["vz_touch"] = round(float(vcom[2]), 3); stats["touch_t"] = round(t, 3)
            stats["touch_err"] = round(float(np.hypot(*(com[:2] - start_xy - np.array([x_goal, 0.0])))), 3)
            stats["touch_tilt"] = round(tilt, 1)
            surf_hit = set()
            for j in range(d.ncon):
                g1, g2 = d.contact[j].geom1, d.contact[j].geom2
                if {g1, g2} & feet:
                    surf_hit |= {"table"} if table in (g1, g2) else {"floor"} if floor in (g1, g2) else set()
            stats["touch_surface"] = sorted(surf_hit)
        if stats["vz_touch"] is not None and t < stats["touch_t"] + 0.5:
            tl = np.abs(d.actuator_force[leg_act])
            if tl.max() > stats["leg_tau_peak"]:
                stats["leg_tau_peak"] = float(tl.max()); stats["leg_tau_peak_joint"] = names[leg_act[int(tl.argmax())]]
        # trunk acceleration (free-joint linear acceleration, world frame), 10 ms running mean, after first lift-off
        acc_hist.append(d.qacc[0:3].copy())
        if len(acc_hist) > 4: acc_hist.pop(0)
        if first_air is not None:
            am = np.mean(acc_hist, axis=0)
            stats["acc_v_peak_g"] = max(stats.get("acc_v_peak_g", 0.0), abs(float(am[2])) / G)
            stats["acc_h_peak_g"] = max(stats.get("acc_h_peak_g", 0.0), float(np.hypot(am[0], am[1])) / G)
        if tilt > 60 and stats["fell"] is None:
            stats["fell"] = round(t, 3)
        if k % 16 == 0 and a.video:
            qlog.append(d.qpos.copy())
        if k % 8 == 0:
            log.append([t, *d.qpos[0:3], *rpy, z_est, surf_est, *x_est, tgt["z"], tgt["x"], *u, *Tf, v_bus, i_tot,
                        rng_true, float(np.abs(d.actuator_force[leg_act]).max()), ["idle", "spool", "climb", "hold1", "move", "hold2", "hover",
                        "land", "spooldown", "disarmed", "cut"].index(phase)])
        if a.scenario == "cut" and phase == "cut" and stats.get("cut_t") is None:
            stats["cut_t"] = round(t, 3)
        if a.scenario == "cut" and stats.get("cut_t") and t > stats["cut_t"] + 2.0:
            break
        if stats["fell"] is not None and t > stats["fell"] + 1.0:
            break
    # ---- outcome
    R = d.xmat[trunk].reshape(3, 3)
    tilt_end = math.degrees(math.acos(max(-1, min(1, R[2, 2]))))
    feet_on = {"table": False, "floor": False}
    for j in range(d.ncon):
        g1, g2 = d.contact[j].geom1, d.contact[j].geom2
        if {g1, g2} & feet:
            if table in (g1, g2): feet_on["table"] = True
            if floor in (g1, g2): feet_on["floor"] = True
    sp = np.vstack(sole_points(m, d)); sp = sp[sp[:, 2] < sp[:, 2].min() + 0.003]
    comw = d.subtree_com[trunk]
    support = dict(heel_margin_mm=round(float(comw[0] - sp[:, 0].min()) * 1000, 1), toe_margin_mm=round(float(sp[:, 0].max() - comw[0]) * 1000, 1),
                   side_margin_mm=round(float(min(comw[1] - sp[:, 1].min(), sp[:, 1].max() - comw[1])) * 1000, 1),
                   trunk_pitch_deg=round(float(np.degrees(rpy_of(R)[1])), 2))
    weight = M * G
    t_max0 = T_REF * a.thrust * 4 * (bat.solve(0)[0] / V_REF) ** 2
    want = {"hover": "floor", "table_up": "table", "table_down": "floor", "cut": "floor"}[a.scenario]
    landed = phase == "disarmed" or a.scenario == "cut"
    ok = (stats["fell"] is None and tilt_end < 25 and feet_on[want] and stats["nacelle_hit"] is None and landed
          and (a.scenario == "cut" or (stats["vz_touch"] is not None and abs(stats["vz_touch"]) < 0.8)))
    if a.scenario == "table_up":
        ok = ok and stats["z_max"] < 1.6
    # airborne part only: lift-off to first foot touchdown on the wanted surface, upright, slow, nothing hit before it
    tt = stats.get("touch_t")
    air_ok = bool(tt is not None and abs(stats["vz_touch"]) < 0.8 and stats.get("touch_tilt", 99) < 25
                  and want in stats.get("touch_surface", []) and (stats["fell"] is None or stats["fell"] > tt)
                  and (stats["nacelle_hit"] is None or stats["nacelle_hit"] > tt) and stats["z_max"] < 1.6)
    i_avg = i_sum / max(1, i_n)
    hov_i = float(np.mean(stats["i_hover"])) if stats["i_hover"] else None
    row = dict(scenario=a.scenario, case=a.case, seed=a.seed, success=bool(ok), airborne_success=air_ok,
               touchdown_tilt_deg=stats.get("touch_tilt"), touchdown_surface=stats.get("touch_surface"),
               phase_end=phase, mass_g=round(M * 1000, 1),
               thrust_to_weight=round(t_max0 / weight, 3),
               hover_throttle_pct=round(100 * float(np.mean(stats["u_hover"])), 1) if stats["u_hover"] else None,
               hover_thrust_frac=round(float(np.mean(stats["u_hover"])) ** 2, 3) if stats["u_hover"] else None,
               max_tilt_deg=round(stats["max_tilt"], 1), max_yaw_deg=round(stats["max_yaw"], 1), tilt_end_deg=round(tilt_end, 1),
               fell_at=stats["fell"], nacelle_hit_at=stats["nacelle_hit"], feet_on=feet_on, z_max_m=round(stats["z_max"], 3),
               landing_vz_mps=stats["vz_touch"], takeoff_drift_m=round(stats.get("takeoff_drift", 0.0), 3),
               takeoff_pitch_excursion_deg=round(stats.get("takeoff_pitch", 0.0), 1),
               hover_drift_m=round(stats.get("hover_drift", 0.0), 3), hover_pitch_max_deg=round(stats.get("hover_pitch", 0.0), 1),
               touchdown_pos_err_m=stats.get("touch_err"), range_jumps_at=rng_jumps, mixer_saturated_s=round(stats["sat_s"], 2),
               pack_current_peak_a=round(stats["i_pack_peak"], 1), pack_current_avg_a=round(i_avg / 2, 1),
               pack_rating_a=PACK_C * PACK_MAH / 1000, esc_channel_peak_a=round(stats["i_esc_peak"], 1), esc_limit_a=ESC_LIMIT_A,
               mah_used=round(bat.mah, 1), mah_available=2 * PACK_MAH, flight_s=round(i_n * dt, 2),
               hover_current_a=round(hov_i, 1) if hov_i else None,
               hover_minutes_80pct=round(0.8 * 2 * PACK_MAH / 1000 / hov_i * 60, 2) if hov_i else None,
               leg_tau_peak_landing_nm=round(stats["leg_tau_peak"], 3), leg_tau_peak_joint=stats["leg_tau_peak_joint"],
               servo_limit_nm=round(limit, 3), soc_end=round(bat.soc, 3), support_end=support,
               trunk_acc_peak_g=dict(vertical=round(stats.get("acc_v_peak_g", 0.0), 2), horizontal=round(stats.get("acc_h_peak_g", 0.0), 2),
                                     note="10 ms mean of the trunk free-joint acceleration incl. contact; MuJoCo soft contact (solref 0.02)"),
               params=dict(thrust=a.thrust, tau=a.tau, resid=a.resid, sensor_delay=a.sensor_delay, weak_fan=a.weak_fan,
                           gust_n=a.gust, soc0=a.soc, mass_variant=a.mass_variant, naive_range=a.naive_range, retune=a.retune,
                           kp=a.kp, r_pack=a.r_pack, cut_alt=a.cut_alt, takeoff_twr=a.takeoff_twr, takeoff_ramp=a.takeoff_ramp,
                           spool_frac=a.spool_frac, spool_down=a.spool_down, flare_h=a.flare_h, trim_ankle=a.trim_ankle,
                           trim_hip=a.trim_hip, wn=a.wn, ground_pitch=a.ground_pitch, com_est=a.com_est,
                           rigid_legs=a.rigid_legs, start_air=a.start_air, floor_mu=a.floor_mu, power_scale=a.power_scale, settle_s=a.settle_s, trim_knee=a.trim_knee,
                           table_gap=a.table_gap, spool_down_frac=a.spool_down_frac, lean_max=a.lean_max))
    if a.log:
        np.savez_compressed(a.log, log=np.array(log, dtype=float))
    if a.video:
        render(m, d, a, qlog)
    return row


def render(m, d, a, qlog):
    """Replay the logged qpos (every 16 physics steps = 25 fps) to an mp4 and a contact sheet of frames."""
    import imageio
    r = mujoco.Renderer(m, 480, 640)
    cam = mujoco.MjvCamera(); cam.azimuth, cam.elevation, cam.distance = a.cam_az, a.cam_el, a.cam_dist
    opt = mujoco.MjvOption(); opt.geomgroup[3] = 0      # the pack itself is drawn (visual_parts); hide the collision boxes
    trunk = m.body("trunk_base").id
    frames = []
    for i, q in enumerate(qlog):
        d.qpos[:] = q
        mujoco.mj_forward(m, d)
        cam.lookat[:] = d.xpos[trunk] if a.cam_follow else [0.25, 0, 0.55]
        r.update_scene(d, cam, opt); frames.append(r.render())
        if a.still_t is not None and i == int(round(a.still_t * 25)):
            imageio.imwrite(str(Path(a.video).with_name(Path(a.video).stem + f"_t{a.still_t:g}.png")), frames[-1])
    imageio.mimwrite(a.video, frames, fps=25)
    pick = [frames[int(i)] for i in np.linspace(0, len(frames) - 1, 8)]
    sheet = np.concatenate([np.concatenate(pick[:4], axis=1), np.concatenate(pick[4:], axis=1)], axis=0)
    imageio.imwrite(str(Path(a.video).with_suffix(".png")), sheet[::2, ::2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", choices=("hover", "table_up", "table_down", "cut"), required=True)
    ap.add_argument("--case", default="nominal")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--thrust", type=float, default=1.0, help="fraction of the vendor 950 g per fan")
    ap.add_argument("--tau", type=float, default=0.10, help="fan spin-up time constant, s")
    ap.add_argument("--resid", type=float, default=0.3, help="fraction of rotor drag torque reaching the body (stators recover the rest)")
    ap.add_argument("--sensor-delay", type=float, default=0.0, help="extra delay on every sensor, s")
    ap.add_argument("--weak-fan", type=int, default=None, help="index 0..3 (1 RF, 2 LR, 3 LF, 4 RR) at --weak-frac")
    ap.add_argument("--gust", type=float, default=0.0, help="N sideways on the trunk for 0.5 s")
    ap.add_argument("--soc", type=float, default=1.0)
    ap.add_argument("--r-pack", type=float, default=0.020, help="ohm per pack incl. lead")
    ap.add_argument("--mass-variant", default="nominal")
    ap.add_argument("--naive-range", action="store_true", help="altitude = range (no surface step handling)")
    ap.add_argument("--retune", action="store_true", help="attitude gains set for the true fan lag (autotune stand-in)")
    ap.add_argument("--kp", type=int, default=400, help="servo P gain holding the legs (stand mode KP 400)")
    ap.add_argument("--cut-alt", type=float, default=0.30)
    ap.add_argument("--arm-at", type=float, default=0.3)
    ap.add_argument("--takeoff-twr", type=float, default=1.3, help="collective while still on the ground, x weight")
    ap.add_argument("--trim-ankle", type=float, default=-4.0, help="deg added to both ankles (mirrored) in the held pose; -4 is "
                    "the only trim in sim/out/hold that stands with the pack")
    ap.add_argument("--spool-s", type=float, default=0.25, help="s, spool-up to --spool-frac of the weight before the climb")
    ap.add_argument("--spool-frac", type=float, default=0.4)
    ap.add_argument("--settle-s", type=float, default=0.0, help="s after the land detector with the fans at --spool-down-frac and the attitude loop on")
    ap.add_argument("--trim-knee", type=float, default=0.0, help="deg added to both knees (mirrored) in the held pose")
    ap.add_argument("--power-scale", type=float, default=1.0, help="electrical power per thrust vs the vendor point (1/0.7, 1/0.4 for 30 %%, 60 %% less efficient)")
    ap.add_argument("--rigid-legs", action="store_true", help="diagnostic: lock the leg joints at the held pose")
    ap.add_argument("--cam-dist", type=float, default=2.4, help="video camera distance, m")
    ap.add_argument("--cam-az", type=float, default=125.0)
    ap.add_argument("--cam-el", type=float, default=-12.0)
    ap.add_argument("--cam-follow", action="store_true", help="video camera looks at the trunk")
    ap.add_argument("--still-t", type=float, default=None, help="also save the video frame at this time as <video>_t<T>.png")
    ap.add_argument("--lean-max", type=float, default=20.0, help="deg, lean angle limit of the position loop (ArduPilot ANGLE_MAX stand-in)")
    ap.add_argument("--start-air", type=float, default=0.0, help="diagnostic: start airborne at this feet height (m), fans at hover speed")
    ap.add_argument("--com-est", choices=("report", "true"), default="report",
                    help="COM the mixer assumes: mass_report.json estimate, or the model's true COM (hover trim calibrated)")
    ap.add_argument("--air-level", action="store_true", help="with --start-air: start with the trunk level instead of the standing pitch")
    ap.add_argument("--floor-mu", type=float, default=None, help="diagnostic: sliding friction of floor, table and feet")
    ap.add_argument("--hover-s", type=float, default=7.0, help="s of position hold in the hover scenario")
    ap.add_argument("--table-gap", type=float, default=0.30, help="m from the floor start to the table's near edge")
    ap.add_argument("--spool-down-frac", type=float, default=0.6, help="weight fraction the fans carry at the start of the spool-down")
    ap.add_argument("--ground-pitch", choices=("rest", "level", "track"), default="rest", help="attitude target while the feet are on the ground")
    ap.add_argument("--takeoff-ramp", type=float, default=0.25, help="s, ramp from spool thrust to --takeoff-twr while on the ground")
    ap.add_argument("--flare-h", type=float, default=0.10, help="m feet height below which the landing attitude blends to the standing pitch")
    ap.add_argument("--spool-down", type=float, default=0.3, help="s, thrust ramp to zero after the land detector")
    ap.add_argument("--wn", type=float, default=8.0, help="attitude loop natural frequency, rad/s (capped at 0.8 / fan lag)")
    ap.add_argument("--trim-hip", type=float, default=0.0, help="deg added to both hip pitches (mirrored) in the held pose")
    ap.add_argument("--out", default=None)
    ap.add_argument("--log", default=None)
    ap.add_argument("--video", default=None)
    ap.add_argument("--fan", choices=sorted(FAN_POINTS), default="qx", help="vendor thrust/current point (qx: QF2611 4000KV; areswei: HDS001 4650KV)")
    a = ap.parse_args()
    set_fan(a.fan)
    row = run(a)
    row["fan"] = dict(name=a.fan, **FAN_POINTS[a.fan])
    s = json.dumps(row)
    if a.out:
        Path(a.out).write_text(s)
    print(s)


if __name__ == "__main__":
    main()
