"""brain_sim_check (walk61/stand61 on the as-built model) with flight-pack additions, no training:

  --thrust-frac F   fans carry F x weight along the trunk axis (flight.py FanSet with its lag, the stand-in mixer and an
                    attitude loop: rate damping plus a slow hold of the attitude at policy start), from --thrust-at on
  --att-wn W        attitude loop natural frequency for the assist (rad/s); 0 = collective only, no moments
  --action-scale K  multiply walk61/stand61 actions (offsets from the default pose) by K
  --crouch H,K,A    open-loop stand pose = Brain stand pose + mirrored hip_pitch, knee, ankle deltas (deg); stand61 takes over
                    at --stand-s
  --shove-at T      0.5 N s lateral shove (5 N for 0.1 s) at T
plus every brain_sim_check option. Records per-joint peak and RMS actuator torque, time at the torque limit, trunk
pitch/roll RMS, achieved speed, fan currents and mAh; prints one JSON line (brain_sim_check result + "pack" block).
"""
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

H = Path(__file__).resolve().parent
MAC = H.parents[2] / "microduck_rl" / "cmu" / "mac"
sys.path.insert(0, str(MAC))
sys.path.insert(0, str(H))

ours = {"--thrust-frac": 0.0, "--att-wn": 4.0, "--action-scale": 1.0, "--crouch": None, "--shove-at": None, "--thrust-at": 0.3,
        "--out": None, "--yaw-hold": "0", "--shove-ns": "0.5", "--fwd-frac": "0"}
argv = [sys.argv[0]]
i = 1
while i < len(sys.argv):
    k = sys.argv[i]
    if k in ours:
        ours[k] = sys.argv[i + 1]; i += 2
    else:
        argv.append(k); i += 1
sys.argv = argv
TF, WN, AS = float(ours["--thrust-frac"]), float(ours["--att-wn"]), float(ours["--action-scale"])
SHOVE = None if ours["--shove-at"] is None else float(ours["--shove-at"])
T_ON = float(ours["--thrust-at"])
SHOVE_NS, FWD = float(ours["--shove-ns"]), float(ours["--fwd-frac"])
YAW_HOLD = ours["--yaw-hold"] == "1"   # fans also hold the heading at policy start (for zero-command standing)

import mujoco  # noqa: E402
import brain_sim_check as bsc  # noqa: E402
import walk_brain  # noqa: E402

fl_argv = sys.argv
sys.argv = [sys.argv[0], "--scenario", "hover"]
import flight as F  # noqa: E402
sys.argv = fl_argv

if ours["--crouch"]:
    dh, dk, da = [math.radians(float(x)) for x in ours["--crouch"].split(",")]
    for side, sgn in (("left", +1), ("right", -1)):
        walk_brain.STAND[f"{side}_hip_pitch"] += sgn * dh
        walk_brain.STAND[f"{side}_knee"] += sgn * dk
        walk_brain.STAND[f"{side}_ankle"] += sgn * da

if AS != 1.0:
    _Brain = bsc.Brain

    class ScaledBrain(_Brain):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            for name in ("walk", "stand"):
                s = self.sessions[name]

                class Wrap:
                    def __init__(self, s):
                        self.s = s

                    def run(self, outs, feeds):
                        r = self.s.run(outs, feeds)
                        return [np.asarray(r[0]) * AS] + list(r[1:])

                    def __getattr__(self, n):
                        return getattr(self.s, n)
                self.sessions[name] = Wrap(s)
    bsc.Brain = ScaledBrain

rec = dict(t=0.0, n=0)


class MjProxy:
    """bsc.mujoco stand-in: mj_step adds the fan forces and records torques; everything else is mujoco."""

    def __getattr__(self, n):
        return getattr(mujoco, n)

    def mj_step(self, m, d):
        if "trunk" not in rec:
            init(m, d)
        dt = m.opt.timestep
        t = rec["t"]
        F_add = np.zeros(6)
        R = d.xmat[rec["trunk"]].reshape(3, 3)
        if TF > 0 and t >= T_ON:
            rpy = F.rpy_of(R)
            if rec["att0"] is None:
                rec["att0"] = rpy.copy()
            gyro = d.qvel[3:6].copy()
            if WN > 0:
                kp, kd = WN * WN, 2 * 0.8 * WN
                ey = ((rec["att0"][2] - rpy[2] + math.pi) % (2 * math.pi) - math.pi) if YAW_HOLD else 0.0
                Mb = rec["I"] * (kp * np.array([rec["att0"][0] - rpy[0], rec["att0"][1] - rpy[1], 0.36 * ey])
                                 - kd * gyro * [1, 1, 0.6])
            else:
                Mb = np.zeros(3)
            ramp = min(1.0, (t - T_ON) / 0.5)
            v_bus, i_tot = rec["bat"].solve(rec["p_last"] + 7.0)
            tmax = F.T_REF * (v_bus / F.V_REF) ** 2
            T, sat = rec["ctl"].mix(TF * ramp * rec["W"], Mb, tmax)
            u = np.sqrt(np.clip(T / tmax, 0, 1))
            Tf, Pf, Qf = rec["fans"].step(u, v_bus, dt)
            rec["p_last"] = float(Pf.sum())
            rec["bat"].drain(i_tot, dt)
            rec["i_sum"] += i_tot; rec["i_n"] += 1
            rec["i_pk"] = max(rec["i_pk"], i_tot / 2)
            rec["esc_pk"] = max(rec["esc_pk"], float((Pf / v_bus).max()))
            tb = rec["trunk"]
            for k, f in enumerate(F.FANS):
                pw = d.xpos[tb] + R @ f["p"]; aw = R @ f["a"]
                Fi = Tf[k] * aw
                F_add[0:3] += Fi
                F_add[3:6] += np.cross(pw - d.xipos[tb], Fi) + (-f["spin"]) * Qf[k] * aw
        if SHOVE is not None and SHOVE <= t < SHOVE + 0.1:
            F_add[1] += SHOVE_NS / 0.1
        if FWD and t >= T_ON:          # idealised forward force along the trunk heading (an upper bound: the fixed fans
            hx = R[:, 0].copy(); hx[2] = 0.0   # can only make it by leaning the trunk or by coupled fore-aft differential)
            F_add[0:3] += FWD * rec["W"] * min(1.0, (t - T_ON) / 0.5) * hx / max(1e-9, np.linalg.norm(hx))
        saved = d.xfrc_applied[rec["trunk"]].copy()
        d.xfrc_applied[rec["trunk"]] += F_add
        mujoco.mj_step(m, d)
        d.xfrc_applied[rec["trunk"]] = saved
        rec["t"] = t + dt
        # readback
        tau = np.abs(d.actuator_force[rec["legs"]])
        rec["tau_pk"] = np.maximum(rec["tau_pk"], tau)
        rec["tau_sq"] += tau ** 2
        rec["at_lim"] += (tau >= 0.98 * rec["limit"]) * dt
        rpy = F.rpy_of(R)
        if t >= 1.0:
            rec["rp_sq"] += rpy[:2] ** 2; rec["rp_n"] += 1
        rec["n"] += 1


def init(m, d):
    tb = m.body("trunk_base").id
    names = [m.actuator(i).name for i in range(m.nu)]
    rec.update(trunk=tb, legs=[i for i, n in enumerate(names) if any(k in n for k in ("hip", "knee", "ankle"))],
               leg_names=[n for n in names if any(k in n for k in ("hip", "knee", "ankle"))],
               limit=float(m.actuator_forcerange[0, 1]))
    rec["tau_pk"] = np.zeros(len(rec["legs"])); rec["tau_sq"] = np.zeros(len(rec["legs"])); rec["at_lim"] = np.zeros(len(rec["legs"]))
    rec["rp_sq"] = np.zeros(2); rec["rp_n"] = 0
    M = float(m.body_mass[1:].sum())
    R = d.xmat[tb].reshape(3, 3)
    com_t = R.T @ (d.subtree_com[tb] - d.xpos[tb])
    rep = json.loads((H / "out" / "mass_report.json").read_text())["duck_with_pack"]
    I = rep["inertia_about_com_kgm2"]
    rec.update(W=M * F.G, I=np.array([I["xx"], I["yy"], I["zz"]]), ctl=F.Controller(M, [I["xx"], I["yy"], I["zz"]], com_t),
               fans=F.FanSet(tau=0.10), bat=F.Battery(), p_last=0.0, att0=None, i_sum=0.0, i_n=0, i_pk=0.0, esc_pk=0.0)


bsc.mujoco = MjProxy()
args_holder = {}
_run = bsc.run


def run_and_keep(args):
    args_holder["a"] = args
    return _run(args)


bsc.run = run_and_keep
_print = print


def capture_print(*a, **k):
    if a and isinstance(a[0], str) and a[0].startswith('{"model"'):
        out = json.loads(a[0])
        n = max(1, rec["n"]); dt_tot = rec["t"]
        ar = args_holder["a"]
        pack = dict(thrust_frac=TF, att_wn=WN, action_scale=AS, crouch=ours["--crouch"], shove_at=SHOVE, shove_ns=SHOVE_NS,
                    fwd_frac=FWD, yaw_hold=YAW_HOLD,
                    tau_peak_nm=dict(zip(rec["leg_names"], np.round(rec["tau_pk"], 3).tolist())),
                    tau_rms_nm=dict(zip(rec["leg_names"], np.round(np.sqrt(rec["tau_sq"] / n), 3).tolist())),
                    time_at_limit_s=dict(zip(rec["leg_names"], np.round(rec["at_lim"], 2).tolist())),
                    servo_limit_nm=round(rec["limit"], 3),
                    trunk_rms_deg=dict(zip(("roll", "pitch"), np.round(np.degrees(np.sqrt(rec["rp_sq"] / max(1, rec["rp_n"]))), 2).tolist())),
                    speed_mps=(round(out["dist_x"] / ar.walk_s, 3) if out.get("dist_x") is not None and ar.walk_s and not out.get("fell_at") else None),
                    fan_current_avg_a=round(rec["i_sum"] / max(1, rec["i_n"]), 1) if TF > 0 else 0.0,
                    pack_current_peak_a=round(rec["i_pk"], 1), esc_channel_peak_a=round(rec["esc_pk"], 1),
                    mah=round(rec["bat"].mah, 1) if TF > 0 else 0.0, sim_s=round(dt_tot, 2),
                    minutes_per_2600mah_80pct=(round(0.8 * 2.6 / (rec["i_sum"] / rec["i_n"]) * 60, 1) if TF > 0 and rec["i_n"] else None))
        out["pack"] = pack
        s = json.dumps(out)
        if ours["--out"]:
            Path(ours["--out"]).write_text(s)
        return _print(s, **k)
    return _print(*a, **k)


bsc.print = capture_print
bsc.main()
