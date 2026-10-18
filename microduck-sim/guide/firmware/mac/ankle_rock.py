"""Ankle-rock latency test: the robot stands feet flat, both ankles swing +-AMP rad at 1, 2 and 3 Hz, the trunk rocks with
them. Measures (1) servo lag, goal -> encoder, and (2) IMU lag, encoder-implied trunk motion -> IMU, against the
as-built simulation of the same goals (--sim). No walking; motion is a few degrees. Run only while walk_wired.py is
stopped and torque is on (it owns the port); the robot ends on STAND at KP_DEFAULT, torque on.

  ~/.venvs/microduck-walk/bin/python ankle_rock.py --out /tmp/ankle_rock.jsonl          # real robot, Shawn guarding
  ~/.venvs/microduck-dyn/bin/python ankle_rock.py --sim --out /tmp/ankle_rock_sim.jsonl  # same goals in the sim
  python3 ankle_rock.py --analyse /tmp/ankle_rock.jsonl [/tmp/ankle_rock_sim.jsonl]
"""
import argparse
import glob
import json
import math
import struct
import sys
import time

AMP = 0.15  # rad; small swings sit inside the servo deadband, large ones move the COM off the feet (--sim checks)
SEGMENTS = [(0.0, 1.0), (1.0, 2.0), (2.0, 2.0), (3.0, 2.0), (0.0, 1.0)]  # (Hz, s); 0 Hz holds STAND
PERIOD = 0.02
ANKLE_SIGN = {"left_ankle": 1.0, "right_ankle": -1.0}  # model rad: left + / right - tips both toes down


def schedule(amp=AMP):
    t, out = 0.0, []
    for f, dur in SEGMENTS:
        for k in range(int(round(dur / PERIOD))):
            s = k * PERIOD
            out.append((round(t + s, 4), f, amp * math.sin(2 * math.pi * f * s) if f else 0.0))
        t += dur
    return out


def goals(stand, off):
    g = dict(stand)
    for n, sg in ANKLE_SIGN.items():
        g[n] = stand[n] + sg * off
    return g


def run_real(args):
    from walk_brain import STAND, KP_DEFAULT, to_model, to_tick
    from walk_wired import ADDR_GOAL, ADDR_P_GAIN, ADDR_TORQUE, IDS, NAMES, Link
    link = Link(args.port or glob.glob("/dev/cu.usbmodem*")[0])
    time.sleep(0.3)
    tq = link.sync_read(ADDR_TORQUE, 1, IDS, timeout=0.05, allow_alert=True)
    if len(tq) != len(IDS) or any(b[0] != 1 for b in tq.values()):
        sys.exit(f"refused: torque must already be on for all servos (read {len(tq)}/{len(IDS)})")
    link.sync_write(ADDR_P_GAIN, 2, {i: args.kp for i in IDS})
    log = open(args.out, "w")
    t0 = time.perf_counter()
    try:
        for ts, f, off in schedule(args.amp):
            while time.perf_counter() - t0 < ts:
                time.sleep(0.0005)
            got = link.sync_read(132, 4, IDS, timeout=0.01, allow_alert=True)
            g = goals(STAND, off)
            link.sync_write(ADDR_GOAL, 4, {i: to_tick(n, g[n]) for i, n in zip(IDS, NAMES)})
            with link.lock:
                imu = link.imu
            row = dict(t=ts, wall=time.time(), f=f, off=off,
                       q={n: to_model(n, struct.unpack("<i", got[i])[0]) for i, n in zip(IDS, NAMES) if i in got},
                       imu=None if imu is None else dict(age=time.perf_counter() - imu[0] + imu[1][11],
                                                         quat=imu[1][1:5], gyro=imu[1][5:8]))
            log.write(json.dumps(row) + "\n")
            if imu and row["imu"]["age"] > 0.25:
                print("IMU stale, stopping at STAND", flush=True)
                break
    finally:
        link.sync_write(ADDR_GOAL, 4, {i: to_tick(n, STAND[n]) for i, n in zip(IDS, NAMES)})
        link.sync_write(ADDR_P_GAIN, 2, {i: KP_DEFAULT for i in IDS})
        log.close()
    print("done; STAND, KP", KP_DEFAULT, "torque on", flush=True)


def run_sim(args):
    import brain_sim_check as b  # re-execs under the sim venv
    import mujoco
    import numpy as np
    from walk_brain import STAND
    m, d, c, names, bam = b.ev.load(b.cfg(0.09, model="asbuilt", kp=args.kp, voltage=7.4))
    pose = {n: STAND[n] for n in names}
    Rt = b.feet_flat_rot(m, d, names, pose)
    qt = np.zeros(4)
    mujoco.mju_mat2Quat(qt, Rt.ravel())
    ji = b.setup(m, d, names, pose, qt)
    zmin = np.vstack(b.sole_points(m, d))[:, 2].min()
    d.qpos[2] -= zmin - 0.0005
    mujoco.mj_forward(m, d)
    qa = m.jnt_qposadr[ji]
    c.q_target = np.array([pose[n] for n in names])
    sub = round(PERIOD / m.opt.timestep)
    for _ in range(int(1.0 / PERIOD) * sub):  # settle
        c.update(); mujoco.mj_step(m, d)
    trunk = m.body("trunk_base").id
    gyro_adr = m.sensor("imu_ang_vel").adr[0]
    feet = [m.geom(g).id for g in ("left_foot_collision", "right_foot_collision")]
    R0 = [d.geom_xmat[g].reshape(3, 3).copy() for g in feet]
    worst = dict(tilt_deg=0.0, foot_deg=0.0)
    with open(args.out, "w") as log:
        prev = c.q_target.copy()
        for ts, f, off in schedule(args.amp):
            q = dict(zip(names, (d.qpos[qa]).tolist()))
            g = goals(STAND, off)
            R = d.xmat[trunk].reshape(3, 3)
            log.write(json.dumps(dict(t=ts, f=f, off=off, q=q, pitch=math.atan2(-R[2, 0], R[2, 2]),
                                      gyro_y=float(d.sensordata[gyro_adr + 1]))) + "\n")
            c.q_target, prev = prev, np.array([g[n] for n in names])  # one-tick action delay, as brain_sim_check
            for _ in range(sub):
                c.update(); mujoco.mj_step(m, d)
            worst["tilt_deg"] = max(worst["tilt_deg"], math.degrees(math.acos(min(1.0, d.xmat[trunk][8]))))
            for g, r0 in zip(feet, R0):  # a foot rotating from flat means it rocks onto its toe or heel edge
                c_ = (np.trace(r0.T @ d.geom_xmat[g].reshape(3, 3)) - 1) / 2
                worst["foot_deg"] = max(worst["foot_deg"], math.degrees(math.acos(max(-1.0, min(1.0, c_)))))
    print(json.dumps(dict(amp=args.amp, kp=args.kp, max_tilt_deg=round(worst["tilt_deg"], 1),
                          max_foot_rock_deg=round(worst["foot_deg"], 1), fell=worst["tilt_deg"] > 30)), flush=True)


def phase_lag(t, x, y, f):
    """Delay (s) of y behind x at frequency f, from sinusoid fits."""
    import numpy as np
    A = np.column_stack([np.sin(2 * np.pi * f * t), np.cos(2 * np.pi * f * t), np.ones_like(t)])
    px = np.linalg.lstsq(A, x, rcond=None)[0]
    py = np.linalg.lstsq(A, y, rcond=None)[0]
    ph = lambda p: math.atan2(p[1], p[0])
    dphi = (ph(px) - ph(py)) % (2 * math.pi)
    if dphi > math.pi:
        dphi -= 2 * math.pi
    return dphi / (2 * math.pi * f), math.hypot(py[0], py[1]) / max(math.hypot(px[0], px[1]), 1e-9)


def analyse(paths):
    import numpy as np
    for p in paths:
        rows = [json.loads(l) for l in open(p)]
        sim = "pitch" in rows[0]
        if not sim:
            from walk_brain import IMU_MOUNT_QUAT, IMU_PITCH_TRIM, MOUNT_FIX, apply_inverse, qmul
            trim_inv = (IMU_PITCH_TRIM[0], -IMU_PITCH_TRIM[1], -IMU_PITCH_TRIM[2], -IMU_PITCH_TRIM[3])
            for r in rows:
                if r["imu"]:
                    qb = qmul(qmul(qmul(tuple(r["imu"]["quat"]), MOUNT_FIX), IMU_MOUNT_QUAT), trim_inv)
                    gb = apply_inverse(qb, [0.0, 0.0, -1.0])
                    r["pitch"] = math.atan2(gb[0], -gb[2])
                    gy = apply_inverse(trim_inv, apply_inverse(IMU_MOUNT_QUAT, apply_inverse(MOUNT_FIX, r["imu"]["gyro"])))
                    r["gyro_y"] = float(gy[1])
        print(f"== {p} ({'sim' if sim else 'real'})")
        for f in (1.0, 2.0, 3.0):
            seg = [r for r in rows if r["f"] == f and "pitch" in r and "left_ankle" in r["q"]]
            seg = seg[len(seg) // 4:]  # skip the start transient
            t = np.array([r["t"] for r in seg])
            goal = np.array([r["off"] for r in seg])
            enc = np.array([r["q"]["left_ankle"] - seg[0]["q"]["left_ankle"] for r in seg])
            enc_r = np.array([-(r["q"]["right_ankle"] - seg[0]["q"]["right_ankle"]) for r in seg])
            pitch = np.array([r["pitch"] for r in seg])
            gyro = np.array([r["gyro_y"] for r in seg])
            # encoder rows hold the reading taken before this tick's goal write; goals go out in the same tick
            ds, gs = phase_lag(t, goal, enc, f)
            dr, _ = phase_lag(t, goal, enc_r, f)
            di, gi = phase_lag(t, enc, pitch, f)
            dg, _ = phase_lag(t, enc, gyro, f)
            print(f"  {f:.0f} Hz: servo lag L {ds * 1000:5.0f} ms R {dr * 1000:5.0f} ms (gain {gs:.2f}) | "
                  f"IMU pitch lag behind encoder {di * 1000:5.0f} ms (|pitch|/|ankle| {gi:.2f}) | gyro lag {dg * 1000 - 250 / f:5.0f} ms")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--kp", type=int, default=200, help="servo P gain during the test (walking uses 200)")
    ap.add_argument("--amp", type=float, default=AMP, help="ankle swing amplitude, model rad")
    ap.add_argument("--port")
    ap.add_argument("--analyse", nargs="+")
    args = ap.parse_args()
    if args.analyse:
        analyse(args.analyse)
    elif args.sim:
        run_sim(args)
    else:
        run_real(args)


if __name__ == "__main__":
    main()
