"""Name-call responses on the as-built MuJoCo duck under stand61, through walk_brain.Brain's own head command path.

Same plant as microduck-sim/guide/firmware/mac/getup-20261026/getup_sim.py (as-built model, saddle mass manifest,
BAM servo model, one tick sensor and action delay, servo read drops), standing start, want = {"mode": "walk", vx 0}
(stand61 at zero command) plus want["head"] from pet.express.duck (EMA pre-inverted). Nothing in microduck-sim is
edited; Brain is used as the robot uses it.

  --clip   five consecutive name calls, natural take choice: MP4 + frame strips + per-call metrics
  --tilt   tolerance table: every take forced N times at random caller directions, plus today's path (target step
           into HEAD_ALPHA 0.2) as the baseline; per-call trunk tilt, head tracking and falls

  ~/.venvs/microduck-dyn/bin/python pet/express/duck_sim.py --tilt --n 20
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
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
GETUP = os.path.join(ROOT, "microduck-sim", "guide", "firmware", "mac", "getup-20261026")
sys.path.insert(0, ROOT)
sys.path.insert(0, GETUP)

import mujoco  # noqa: E402
import numpy as np  # noqa: E402

import getup_sim as gs  # noqa: E402  (its imports set up the as-built plant and walk_brain)
from pet.express import Affect, Expressor, Target, acknowledge, content_idle, greet, startle  # noqa: E402
from pet.express.channels import load_card  # noqa: E402
from pet.express.duck import HEAD_JOINTS, ema, ema_preinverse, head_deltas, want_head  # noqa: E402
from pet.express.takes import SOCIAL_TAKES  # noqa: E402

OUT = os.path.join(HERE, "out")
CARD = os.path.join(HERE, "cards", "duck.json")
SETTLE_S = 1.5   # standing on stand61 before the first call
FALL_GZ = -0.5   # trunk past 60 deg


def state_defaults():
    facts = json.load(open(os.path.join(ROOT, "microduck-sim", "CURRENT-STATE.json")))["facts"]
    return float(facts["servo_rail_v"]["value"]), float(facts["servo_read_drop_fraction"]["value"])


def body_rp(R):
    """Trunk roll and pitch (deg) from the body-frame gravity direction."""
    g = R.T @ np.array([0.0, 0.0, -1.0])
    return math.degrees(math.atan2(g[1], -g[2])), math.degrees(math.atan2(g[0], -g[2]))


def simulate(r_rows, seed, volt, drop, render=None, label_fn=None):
    """Run the plant with head-command targets r_rows (n, 4; one per 50 Hz tick after SETTLE_S of zeros).
    Returns per-tick trace arrays and, when render is given, frames."""
    rng = np.random.default_rng(seed)
    c0 = gs.cfg(0.09, model="asbuilt", kp=200, voltage=volt)
    c0["friction"] = 1.0
    c0["mass_manifest"] = os.path.abspath(gs.SADDLE)
    m, d, c, names, bam = gs.ev.load(c0)
    idx = {n: names.index(n) for n in gs.NAMES}
    brain = gs.Brain(gs.MODELS)
    home = {n: brain.default[n] for n in names}
    gs.place(m, d, names, home, np.array([1.0, 0, 0, 0]))
    ji = np.array([m.actuator(n).trnid[0] for n in names])
    qa, va = m.jnt_qposadr[ji], m.jnt_dofadr[ji]
    trunk = m.body("trunk_base").id
    gyro_adr = m.sensor("imu_ang_vel").adr[0]
    c.q_target = np.array([home[n] for n in names])
    bam.actuator.kp = 400
    sub = round(0.02 / m.opt.timestep)
    aq = collections.deque([c.q_target.copy()] * 2, maxlen=2)
    sq = collections.deque(maxlen=2)
    n_settle = int(round(SETTLE_S / 0.02))
    rows = np.vstack([np.zeros((n_settle, 4)), np.asarray(r_rows)])
    hj = [names.index(j) for j in HEAD_JOINTS]
    tr = {k: [] for k in ("t", "roll", "pitch", "gz", "z", "x", "y", "head")}
    frames = []
    rend = None
    if render:
        rend = mujoco.Renderer(m, render["h"], render["w"])
        cam = mujoco.MjvCamera()
        cam.distance, cam.azimuth, cam.elevation = render.get("dist", 0.55), render.get("az", 205), render.get("el", -12)
    for k in range(len(rows)):
        t = k * 0.02
        Rt = d.xmat[trunk].reshape(3, 3)
        q_sensor = gs.qmul(gs.qmul(tuple(d.qpos[3:7].copy()), gs.conj(gs.IMU_MOUNT_QUAT)), gs.conj(gs.MOUNT_FIX))
        g_sensor = gs.apply(gs.MOUNT_FIX, gs.apply(gs.IMU_MOUNT_QUAT, d.sensordata[gyro_adr:gyro_adr + 3].copy()))
        sample = (q_sensor, tuple(float(x) for x in g_sensor), d.qpos[qa].copy(), d.qvel[va].copy())
        if not sq:
            sq.extend([sample] * sq.maxlen)
        sq.append(sample)
        q_s, g_s, qm, dqm = sq[0]
        pos_t = [gs.to_tick(n, float(qm[idx[n]])) for n in gs.NAMES]
        vel_t = [int(round(float(dqm[idx[n]]) / gs.VEL_UNIT / gs.SIGN[n])) for n in gs.NAMES]
        want = {"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0, "head": want_head(rows[k], brain.default)}
        fresh = rng.random() >= drop
        goal, kp, info = brain.tick(want, t, pos_t, vel_t, tuple(q_s), g_s, fresh, 0.024, 0.024)
        if goal is not None:
            target = np.array([goal[n] for n in names])
            if kp:
                bam.actuator.kp = kp
        else:
            target = aq[-1].copy()
        aq.append(target.copy())
        c.q_target = aq[0]
        for _ in range(sub):
            c.update()
            mujoco.mj_step(m, d)
        Rt = d.xmat[trunk].reshape(3, 3)
        roll, pitch = body_rp(Rt)
        tr["t"].append(t - SETTLE_S)
        tr["roll"].append(roll)
        tr["pitch"].append(pitch)
        tr["gz"].append(-float(Rt[2, 2]))
        tr["z"].append(float(d.xpos[trunk, 2]))
        tr["x"].append(float(d.xpos[trunk, 0]))
        tr["y"].append(float(d.xpos[trunk, 1]))
        tr["head"].append([float(d.qpos[qa[i]]) - home[HEAD_JOINTS[j]] for j, i in enumerate(hj)])
        if rend is not None and k % render.get("every", 2) == 0 and t >= SETTLE_S - 0.5:
            cam.lookat[:] = d.xpos[trunk] + np.array([0, 0, 0.05])
            rend.update_scene(d, camera=cam)
            frames.append((t - SETTLE_S, rend.render().copy()))
    if rend is not None:
        rend.close()  # an unclosed GL context aborts the interpreter at exit
    out = {k: np.asarray(v) for k, v in tr.items()}
    out["frames"] = frames
    return out


def call_metrics(tr, t_call, dur, y_full):
    """Trunk tilt deviation and head-yaw tracking for one call window. y_full: wanted head_cmd rows on the trace's
    tick grid (settle included)."""
    t = tr["t"]
    pre = (t >= t_call - 0.6) & (t < t_call)
    win = (t >= t_call) & (t < t_call + dur)
    r0, p0 = tr["roll"][pre].mean(), tr["pitch"][pre].mean()
    dev = np.hypot(tr["roll"][win] - r0, tr["pitch"][win] - p0)
    yaw, want = tr["head"][:, 2], y_full[:, 2]
    y0 = yaw[pre][-1]
    exc = np.abs(yaw[win] - y0)
    tw = t[win] - t_call
    i10 = np.flatnonzero(exc >= 0.1 * exc.max()) if exc.max() > 0.1 else np.array([], int)
    # lag of the joint behind the wanted command (best shift 0..0.3 s) and the error left after it
    best = min(range(16), key=lambda L: float(np.mean((yaw[win][L:] - want[win][:len(want[win]) - L]) ** 2)))
    resid = yaw[win][best:] - want[win][:len(want[win]) - best]
    side = np.sign(want[win][-1] - want[pre][-1]) or 1.0
    return dict(tilt_max_deg=round(float(dev.max()), 2), tilt_p95_deg=round(float(np.percentile(dev, 95)), 2),
                roll_max_deg=round(float(np.abs(tr["roll"][win] - r0).max()), 2),
                pitch_max_deg=round(float(np.abs(tr["pitch"][win] - p0).max()), 2),
                fell=bool((tr["gz"][win] > FALL_GZ).any()),
                drift_mm=round(1000 * float(np.hypot(tr["x"][win][-1] - tr["x"][pre][0], tr["y"][win][-1] - tr["y"][pre][0])), 1),
                head_latency_s=None if not i10.size else round(float(tw[i10[0]]), 3),
                head_peak_rad=round(float(exc.max()), 3),
                head_extra_overshoot_rad=round(float(max(0.0, side * (yaw[win] - want[win]).max() if side > 0
                                                         else -(yaw[win] - want[win]).min())), 3),
                track_lag_s=round(best * 0.02, 2), track_rms_rad=round(float(np.sqrt(np.mean(resid ** 2))), 4))


def name_calls(seed, n_calls, gap, force=None, rng_targets=None, affect=None, warmth=0.8, energy=0.7, kind="acknowledge"):
    """Schedule of n name calls from varying directions, each followed by content_idle (the head drifts home)."""
    rng = rng_targets or np.random.default_rng(seed + 1000)
    sched, targets = [], []
    for i in range(n_calls):
        side = 1 if (i % 2 == 0) else -1
        yaw = side * float(rng.uniform(0.5, 1.25))
        pitch = float(rng.uniform(0.1, 0.35))
        tc = 0.5 + i * gap
        a = affect or Affect(0.6, 0.6)
        if kind == "startle":
            intent = startle(Target(yaw, pitch))
        elif kind == "greet":
            intent = greet(Target(yaw, pitch), affect=a)
        else:
            intent = acknowledge(Target(yaw, pitch), warmth=warmth, energy=energy, affect=a)
        sched.append((tc, intent, force) if force else (tc, intent))
        sched.append((tc + gap * 0.7, content_idle(affect=Affect(a.valence, max(0.2, a.arousal - 0.2)))))
        targets.append((tc, yaw, pitch))
    return sched, targets, 0.5 + n_calls * gap


def run_express(seed, sched, until, volt, drop, render=None, reset_novelty=False):
    ex = Expressor(load_card(CARD), seed=seed)
    if reset_novelty:  # tolerance table: every call is fresh, so habituation does not shrink the gesture
        ex.hab.tau = 1e-6
    tl = ex.run(sched, until)
    y = head_deltas(tl["outputs"])
    r, c = ema_preinverse(y)
    tr = simulate(r, seed, volt, drop, render)
    return tl, y, r, c, tr


def baseline_rows(targets, gap, n):
    """Today's path: the target joint pose stepped in at the call (and back at the idle), walk_brain EMA smooths it."""
    card = load_card(CARD)
    r = np.zeros((n, 4))
    for (tc, yaw, pitch) in targets:
        k0, k1 = int(round(tc / 0.02)), int(round((tc + gap * 0.7) / 0.02))
        row = np.zeros(4)
        for mp in card["channels"]["ATTEND"]["map"]:
            row[HEAD_JOINTS.index(mp["to"])] += mp["gain"] * (yaw if mp["axis"] == "yaw" else pitch)
        r[k0:k1] = row
    return r


# tilt-table sets: (name, forced take, intent kind, affect, warmth, energy)
SETS = [("baseline", None, "acknowledge", Affect(0.6, 0.6), 0.8, 0.7)] + \
    [(k, k, "acknowledge", Affect(0.2, 0.15) if k == "groggy" else Affect(0.6, 0.6), 0.8, 0.7) for k in SOCIAL_TAKES] + \
    [("quick_snap_max", "quick_snap", "acknowledge", Affect(1.0, 1.0), 1.0, 1.0),
     ("greet", None, "greet", Affect(0.8, 0.8), 0.9, 0.8),
     ("startle", None, "startle", Affect(-0.3, 0.9), 0.0, 1.0)]


def tilt_table(args):
    volt, drop = args.volt, args.drop
    res = dict(volt=volt, drop=drop, gap_s=args.gap, n=args.n, takes={}, started=time.strftime("%Y-%m-%dT%H:%M:%S"))
    t0 = time.time()
    n_settle = int(round(SETTLE_S / 0.02))
    for k, (name, force, kind, aff, warmth, energy) in enumerate(SETS):
        sched, targets, until = name_calls(args.seed + k, args.n, args.gap, force=force, affect=aff, warmth=warmth,
                                           energy=energy, kind=kind)
        if name == "baseline":
            r = baseline_rows(targets, args.gap, int(round(until / 0.02)) + 1)
            y = ema(r)
            tr = simulate(r, args.seed + k, volt, drop)
            hist = [dict(take="baseline")] * len(targets)
        else:
            tl, y, r, c, tr = run_express(args.seed + k, sched, until, volt, drop, reset_novelty=True)
            hist = tl["takes"]
        y_full = np.vstack([np.zeros((n_settle, 4)), y])
        rows = []
        for (tc, yaw, pitch), h in zip(targets, hist):
            mtr = call_metrics(tr, tc, args.gap * 0.65, y_full)
            mtr.update(t=tc, target_yaw=round(yaw, 3), target_pitch=round(pitch, 3), take=h["take"])
            rows.append(mtr)
        sat = np.isclose(np.abs(r), [1.10, 1.10, 1.40, 0.31]).any(axis=1)
        res["takes"][name] = dict(intent=kind, forced=force, affect=[aff.valence, aff.arousal], rows=rows,
                                  fell_any=bool((tr["gz"] > FALL_GZ).any()), head_cmd_saturated_ticks=int(sat.sum()),
                                  ema_error_max_rad=round(float(np.abs(ema(r) - y).max()), 4))
        print(f"{name}: tilt max {max(x['tilt_max_deg'] for x in rows):.2f} deg, fell {res['takes'][name]['fell_any']}",
              flush=True)
    res["wall_s"] = round(time.time() - t0, 1)
    return res


def clip(args):
    from PIL import Image, ImageDraw
    sched, targets, until = name_calls(args.seed, 5, args.gap)
    render = dict(w=480, h=360, every=2)
    tl, y, r, c, tr = run_express(args.seed, sched, until, args.volt, args.drop, render)
    calls = []
    y_full = np.vstack([np.zeros((int(round(SETTLE_S / 0.02)), 4)), y])
    for i, ((tc, yaw, pitch), h) in enumerate(zip(targets, tl["takes"])):
        mtr = call_metrics(tr, tc, args.gap * 0.65, y_full)
        mtr.update(call=i + 1, t=tc, target_yaw=round(yaw, 3), take=h["take"], novelty=h["novelty"],
                   params=h["params"], events=h["events"])
        calls.append(mtr)
    os.makedirs(OUT, exist_ok=True)
    take_at = [(tc, h["take"], i + 1) for i, ((tc, _, _), h) in enumerate(zip(targets, tl["takes"]))]

    def label(t):
        cur = [x for x in take_at if x[0] <= t]
        return f"call {cur[-1][2]}: {cur[-1][1]}" if cur else "idle"

    def annotate(img, t):
        im = Image.fromarray(img)
        dr = ImageDraw.Draw(im)
        txt = f"t {t:5.2f} s   {label(t)}"
        evs = [e for e in tl["events"] if abs(e["t_abs"] - t) < 0.12]
        if evs:
            txt += f"   QUACK pitch x{evs[0]['pitch']:.2f}"
        dr.rectangle([0, 0, im.width, 18], fill=(255, 255, 255))
        dr.text((6, 3), txt, fill=(0, 0, 0))
        return im

    mp4 = os.path.join(OUT, "duck_5_calls.mp4")
    import subprocess
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                          f"{render['w']}x{render['h']}", "-r", "25", "-i", "-", "-pix_fmt", "yuv420p", "-vcodec",
                          "libx264", "-crf", "26", mp4], stdin=subprocess.PIPE)
    for t, img in tr["frames"]:
        p.stdin.write(np.asarray(annotate(img, t)).tobytes())
    p.stdin.close()
    p.wait()
    # one strip per call: 6 frames across the response
    offs = (0.0, 0.25, 0.5, 0.8, 1.2, 1.8)
    ftimes = np.array([f[0] for f in tr["frames"]])
    strips = []
    for (tc, _, _) in targets:
        row = [annotate(tr["frames"][int(np.argmin(np.abs(ftimes - (tc + o))))][1], tc + o) for o in offs]
        strips.append(np.hstack([np.asarray(x.resize((240, 180))) for x in row]))
    Image.fromarray(np.vstack(strips)).save(os.path.join(OUT, "duck_5_calls_strip.png"))
    pad = np.zeros((int(round(SETTLE_S / 0.02)), 4))
    y, r = np.vstack([pad, y]), np.vstack([pad, r])
    res = dict(volt=args.volt, drop=args.drop, seed=args.seed, gap_s=args.gap, calls=calls,
               trace=dict(t=tr["t"][::2].round(3).tolist(), roll=tr["roll"][::2].round(3).tolist(),
                          pitch=tr["pitch"][::2].round(3).tolist(),
                          head_yaw=tr["head"][::2, 2].round(4).tolist(), head_pitch=tr["head"][::2, 1].round(4).tolist(),
                          head_roll=tr["head"][::2, 3].round(4).tolist(), neck_pitch=tr["head"][::2, 0].round(4).tolist(),
                          cmd_yaw=y[::2, 2].round(4).tolist(), sent_yaw=r[::2, 2].round(4).tolist()),
               events=tl["events"], mp4=os.path.relpath(mp4, ROOT))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", action="store_true")
    ap.add_argument("--tilt", action="store_true")
    ap.add_argument("--n", type=int, default=20, help="calls per take in the tilt table")
    ap.add_argument("--gap", type=float, default=3.5, help="s between calls")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--volt", type=float, default=None, help="default: servo_rail_v in microduck-sim/CURRENT-STATE.json")
    ap.add_argument("--drop", type=float, default=None, help="default: servo_read_drop_fraction in CURRENT-STATE.json")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    v, dr = state_defaults()
    args.volt = v if args.volt is None else args.volt
    args.drop = dr if args.drop is None else args.drop
    os.makedirs(OUT, exist_ok=True)
    if args.tilt:
        res = tilt_table(args)
        json.dump(res, open(os.path.join(OUT, f"duck_tilt{args.tag}.json"), "w"), indent=1)
    if args.clip:
        res = clip(args)
        json.dump(res, open(os.path.join(OUT, f"duck_calls{args.tag}.json"), "w"))
        for cl in res["calls"]:
            print(cl["call"], cl["take"], cl["novelty"], "tilt", cl["tilt_max_deg"], "lat", cl["head_latency_s"],
                  "lag", cl["track_lag_s"], "rms", cl["track_rms_rad"], "fell", cl["fell"])


if __name__ == "__main__":
    main()
