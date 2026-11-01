"""Head-only name-call answers on the as-built MuJoCo duck (R11 standing, R12 seated; D-038). Mac mini only.

The robot's own paths end to end: namecall.HeadPath (the take, attention hold, release and drift home; seated: the
tilt and SIT_HEAD_RATE) writes want["head"] into walk_brain.Brain, which runs stand61 (walk at zero command) or
sitstand61 (its own sit sequence: {"mode": "sit"} from standing, then the head command while seated). Plant as
pet/express/duck_sim.py (getup_sim: as-built config, BAM servos, one tick sensor and action delay, dropped reads) with
the 2026-11-01 as-built mass manifest built here from variant-asbuilt-20261101.json.

  ~/.venvs/microduck-dyn/bin/python glance_sim.py --build-manifest
  ~/.venvs/microduck-dyn/bin/python glance_sim.py --out results.json [--seeds 3] [--volts 7.0,7.8] [--drop 0.17]

Per case: fell (trunk past 60 deg), the walk_wired tilt guard (30 deg from vertical), trunk tilt change against the
0.5 s before the call, trunk drift (feet slipping), head yaw and roll reached, and seated: knees inside the seated
range (walk_brain SIT_SEATED_KNEE) for the whole answer.
"""
import argparse
import collections
import json
import math
import os
import sys
import time

SIM_PYTHON = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
if os.path.realpath(sys.prefix) != os.path.realpath(os.path.dirname(os.path.dirname(SIM_PYTHON))):
    os.execv(SIM_PYTHON, [SIM_PYTHON, os.path.abspath(__file__)] + sys.argv[1:])

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.abspath(os.path.join(HERE, "..", ".."))
ROOT = os.path.abspath(os.path.join(MAC, "..", "..", "..", ".."))
TEAM_MODEL = os.path.join(ROOT, "microduck-sim", "microduck_rl", "cmu", "model")
VARIANT = os.path.join(HERE, "variant-asbuilt-20261101.json")
MANIFEST = os.path.join(HERE, "manifest-asbuilt-20261101.json")
sys.path[:0] = [ROOT, MAC, os.path.join(MAC, "getup-20261026")]

import mujoco  # noqa: E402
import numpy as np  # noqa: E402

import getup_sim as gs  # noqa: E402
import namecall as nc  # noqa: E402
from walk_brain import SIT_SEATED_KNEE  # noqa: E402
from pet.express.duck import HEAD_JOINTS  # noqa: E402

FALL_GZ = -0.5
GUARD_TILT_DEG = 30.0      # walk_wired --max-tilt / --max-tilt-sit default
DT = 0.02
SIT_AT = 4.0               # s of stand61 before {"mode": "sit"}, as sit-rise-20261029


def build_manifest():
    """Resolve the variant chain with the team repo's own make_variants and write it in the base manifest schema."""
    from pathlib import Path
    sys.path.insert(0, TEAM_MODEL)
    import apply_masses
    import make_variants
    variant, parts, removed, added, chain = make_variants.resolve_variant(Path(VARIANT))
    base = apply_masses.load_manifest(apply_masses.BASE_MANIFEST)
    man = dict(schema=base["schema"], build=f"{variant['variant']} ({variant['describes']}); built by glance_sim.py "
               f"--build-manifest from {os.path.basename(VARIANT)} on top of {' -> '.join(chain)}",
               frame=base["frame"], excluded=base["excluded"] + ["NP-F970 battery: removed by the runner (remove_old_battery_kg)"],
               derived=dict(removed=[p["id"] for p in removed], added=[p["id"] for p in added],
                            net_delta_g=round(sum(p["mass_kg"] for p in added) * 1000 - sum(p["mass_kg"] for p in removed) * 1000, 2)),
               parts=parts)
    json.dump(man, open(MANIFEST, "w"), indent=1)
    print("wrote", MANIFEST, "net", man["derived"]["net_delta_g"], "g against", chain[0])


def plant(seed, volt):
    c0 = gs.cfg(0.09, model="asbuilt", kp=200, voltage=volt)
    c0["friction"] = 1.0
    c0["mass_manifest"] = MANIFEST
    m, d, c, names, bam = gs.ev.load(c0)
    brain = gs.Brain(gs.MODELS)
    home = {n: brain.default[n] for n in names}
    gs.place(m, d, names, home, np.array([1.0, 0, 0, 0]))
    c.q_target = np.array([home[n] for n in names])
    bam.actuator.kp = 400
    return m, d, c, names, bam, brain, home


def run_case(case, seed, volt, drop):
    """case: dict(posture "stand" | "sit", az (rad), cap, rate (seated), hold_s). Returns metrics."""
    rng = np.random.default_rng(seed)
    m, d, c, names, bam, brain, home = plant(seed, volt)
    idx = {n: names.index(n) for n in gs.NAMES}
    ji = np.array([m.actuator(n).trnid[0] for n in names])
    qa, va = m.jnt_qposadr[ji], m.jnt_dofadr[ji]
    trunk = m.body("trunk_base").id
    gyro_adr = m.sensor("imu_ang_vel").adr[0]
    sub = round(DT / m.opt.timestep)
    aq = collections.deque([c.q_target.copy()] * 2, maxlen=2)
    sq = collections.deque(maxlen=2)
    hj = [names.index(j) for j in HEAD_JOINTS]
    lk, rk = names.index("left_knee"), names.index("right_knee")

    hp = nc.HeadPath(seed=seed, default={j: brain.default[j] for j in HEAD_JOINTS}, yaw_cap=case["cap"])
    sit = case["posture"] == "sit"
    nc.SIT_HEAD_RATE = case.get("rate", nc.SIT_HEAD_RATE)
    hp.seated = False
    t_call = None
    seated_at = None
    t_end_max = 30.0
    tr = collections.defaultdict(list)
    k = 0
    while True:
        t = k * DT
        # the command this tick: settle standing, (sit down), then the call through HeadPath
        if not sit:
            want = dict(nc.WALK_ZERO)
            if t_call is None and t >= 2.0:
                t_call = t
        else:
            want = dict(nc.WALK_ZERO) if t < SIT_AT else {"mode": "sit"}
            if seated_at is None and brain.mode == "sit" and brain.sit is not None and brain.sit.get("phase") == "seated":
                seated_at = t
            if t_call is None and seated_at is not None and t >= seated_at + 2.0:
                t_call = t
                hp.seated = True
        if t_call is not None:
            if abs(t - t_call) < 1e-9:
                hp.start(t, case["az"], nc.LOOK_PITCH, hold=True)
            if hp.holding and t >= t_call + case["hold_s"]:
                hp.release(t)
            head, _, active = hp.tick(t)
            if head is not None:
                want["head"] = head
        # plant tick (as duck_sim.simulate)
        q_sensor = gs.qmul(gs.qmul(tuple(d.qpos[3:7].copy()), gs.conj(gs.IMU_MOUNT_QUAT)), gs.conj(gs.MOUNT_FIX))
        g_sensor = gs.apply(gs.MOUNT_FIX, gs.apply(gs.IMU_MOUNT_QUAT, d.sensordata[gyro_adr:gyro_adr + 3].copy()))
        sample = (q_sensor, tuple(float(x) for x in g_sensor), d.qpos[qa].copy(), d.qvel[va].copy())
        if not sq:
            sq.extend([sample] * sq.maxlen)
        sq.append(sample)
        q_s, g_s, qm, dqm = sq[0]
        pos_t = [gs.to_tick(n, float(qm[idx[n]])) for n in gs.NAMES]
        vel_t = [int(round(float(dqm[idx[n]]) / gs.VEL_UNIT / gs.SIGN[n])) for n in gs.NAMES]
        fresh = rng.random() >= drop
        goal, kp, info = brain.tick(want, t, pos_t, vel_t, tuple(q_s), g_s, fresh, 0.024, 0.024)
        target = np.array([goal[n] for n in names]) if goal is not None else aq[-1].copy()
        if goal is not None and kp:
            bam.actuator.kp = kp
        aq.append(target.copy())
        c.q_target = aq[0]
        for _ in range(sub):
            c.update()
            mujoco.mj_step(m, d)
        R = d.xmat[trunk].reshape(3, 3)
        tr["t"].append(t)
        tr["gz"].append(-float(R[2, 2]))
        tr["tilt"].append(math.degrees(math.acos(max(-1.0, min(1.0, float(R[2, 2]))))))
        tr["roll"].append(math.degrees(math.atan2(R[2, 1], R[2, 2])))
        tr["pitch"].append(math.degrees(math.asin(max(-1.0, min(1.0, -float(R[2, 0]))))))
        tr["xy"].append(d.xpos[trunk, :2].copy())
        tr["head"].append([float(d.qpos[qa[i]]) - home[HEAD_JOINTS[j]] for j, i in enumerate(hj)])
        tr["knees"].append((abs(float(d.qpos[qa[lk]])), abs(float(d.qpos[qa[rk]]))))
        tr["mode"].append(brain.mode)
        k += 1
        if t_call is not None and t >= t_call + case["hold_s"] + 4.0:
            break
        if t > t_end_max:
            break
    t_arr = np.array(tr["t"])
    out = dict(case, seed=seed, volt=volt, drop=drop, t_call=t_call, seated_at=seated_at)
    if sit:
        # the sit-down alone, as real_sits.py reads it from the robot logs: sit command to 3 s later
        down = (t_arr >= SIT_AT) & (t_arr < SIT_AT + 3.0)
        out["sit_peak_deg"] = round(float(np.array(tr["tilt"])[down].max()), 2)
        out["sit_tipped"] = bool(np.array(tr["tilt"])[t_arr >= SIT_AT].max() > GUARD_TILT_DEG)
    if t_call is None:
        out["error"] = "the call never started (no seat reached)" if sit else "no call"
        return out
    pre = (t_arr >= t_call - 0.5) & (t_arr < t_call)
    post = t_arr >= t_call
    tilt = np.array(tr["tilt"])
    roll, pitch = np.array(tr["roll"]), np.array(tr["pitch"])
    head = np.array(tr["head"])
    xy = np.array(tr["xy"])
    out.update(
        tipped_before_call=bool(tilt[pre].mean() > GUARD_TILT_DEG),   # the sit-down itself tipped (not the answer)
        fell=bool((np.array(tr["gz"])[post] > FALL_GZ).any()),
        guard_trip=bool((tilt[post] > GUARD_TILT_DEG).any()),
        monitor=bool(any(mo == "monitor" for mo, p in zip(tr["mode"], post) if p)),
        tilt_pre_deg=round(float(tilt[pre].mean()), 2),
        tilt_max_deg=round(float(tilt[post].max()), 2),
        dtilt_max_deg=round(float(max(np.abs(roll[post] - roll[pre].mean()).max(), np.abs(pitch[post] - pitch[pre].mean()).max())), 2),
        drift_cm=round(float(np.linalg.norm(xy[post] - xy[pre].mean(axis=0), axis=1).max() * 100), 2),
        head_yaw_reached=round(float(np.abs(head[post, 2]).max()), 3),
        head_roll_reached=round(float(np.abs(head[post, 3]).max()), 3),
        head_pitch_min=round(float(head[post, 1].min()), 3),
    )
    if sit:
        kn = np.array(tr["knees"])[post]
        out["knees_seated_all"] = bool(((kn >= SIT_SEATED_KNEE[0]) & (kn <= SIT_SEATED_KNEE[1])).all())
        out["knee_min"] = round(float(kn.min()), 3)
    return out


CASES = (
    [dict(name=f"stand_cap{cap}_az{deg}", posture="stand", az=math.radians(deg), cap=cap, hold_s=6.0)
     for cap in (1.2, 1.40) for deg in (90, -90, 150)]
    + [dict(name=f"sit_rate{rate}_az{deg}", posture="sit", az=math.radians(deg), cap=1.40, rate=rate, hold_s=6.0)
       for rate in (1.0, 2.0) for deg in (90, -90, 30)]
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-manifest", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "results.json"))
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--volts", default="7.0,7.8")
    ap.add_argument("--drop", type=float, default=0.17)
    ap.add_argument("--only", default=None, help="substring of case names")
    ap.add_argument("--sit-entry", default=None, metavar="DROPS",
                    help="sit-down only, at these comma-separated read-drop fractions (8 seeds, --volts, --manifest)")
    ap.add_argument("--manifest", default=None, help="mass manifest path instead of the 11-01 as-built one")
    a = ap.parse_args()
    if a.build_manifest:
        build_manifest()
        return
    global MANIFEST
    if a.manifest:
        MANIFEST = os.path.abspath(a.manifest)
    if a.sit_entry:
        rows, t0 = [], time.time()
        case = dict(name="sit_entry", posture="sit", az=0.0, cap=nc.YAW_CAP, rate=1.0, hold_s=0.5)
        for drop in (float(x) for x in a.sit_entry.split(",")):
            for volt in (float(v) for v in a.volts.split(",")):
                for s in range(a.seeds):
                    r = run_case(case, 7 + s, volt, drop)
                    rows.append({k: r.get(k) for k in ("drop", "volt", "seed", "sit_peak_deg", "sit_tipped", "seated_at")})
                    print(json.dumps(rows[-1]), flush=True)
        json.dump(dict(started=time.strftime("%Y-%m-%dT%H:%M:%S"), wall_s=round(time.time() - t0, 1),
                       manifest=os.path.basename(MANIFEST), rows=rows), open(a.out, "w"), indent=1)
        return
    rows, t0 = [], time.time()
    for case in CASES:
        if a.only and a.only not in case["name"]:
            continue
        for volt in (float(v) for v in a.volts.split(",")):
            for s in range(a.seeds):
                r = run_case(case, 7 + s, volt, a.drop)
                rows.append(r)
                print(json.dumps({k: v for k, v in r.items() if k not in ("az",)}), flush=True)
    json.dump(dict(started=time.strftime("%Y-%m-%dT%H:%M:%S"), wall_s=round(time.time() - t0, 1), manifest=os.path.basename(MANIFEST),
                   rows=rows), open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
