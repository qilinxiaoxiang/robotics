"""Evaluate stand/walk policies in the probe that failed (brain_sim_check.py, the runtime's walk_brain, as-built
MuJoCo model, real-condition flags --volt 7.6 --drop 0.036), with three additions done from outside the probe by
wrapping mujoco.mj_step: peak leg actuator force, a trunk shove, and a landing start (drop + tilt).

  $PY train/flight_eval.py --models <dir with walk61.onnx + stand61.onnx> --manifest <pack manifest> --case walk \
      --episodes 20 --out <file.json> [--shove-ns 0.5 --shove-at 8] [--landing] [--workers 6]

Episode = 20 s: open-loop stand --stand-s (0.3 s, as in sim/walk_probe.sh; 0 for landing so the policy catches the
touchdown), walk mode from 0.3 s at zero command (stand61 until the first step), the case's command from 2 s for
15 s, then 3 s at zero command. Seeds 0..episodes-1 drive the probe's dropped-read draw (and the landing draw).
Cases: stand (vx 0), walk (vx 0.25), turnL (vtheta +0.3), turnR (vtheta -0.3).
Per episode: fell_at, tracked speed (dist_x / 15 s for walk; yaw_walk / 15 s for turns), peak |actuator force| of
the ten leg servos (all ticks, and after 1 s), action jumps. Summary: falls out of N, median speed, max peak force.
"""
import argparse
import contextlib
import io
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RL = HERE.parents[2] / "microduck_rl" if (HERE.parents[2] / "microduck_rl").exists() else Path(os.environ["MICRODUCK_RL"])
LIMIT_NM = 0.538
CASES = {"stand": ["--vx", "0"], "walk": ["--vx", "0.25"], "turnL": ["--vx", "0", "--vtheta", "0.3"],
         "turnR": ["--vx", "0", "--vtheta", "-0.3"]}
WALK_AT, WALK_S = 2.0, 15.0
FRAME_HOOK = None  # optional callable(m, d, t) after every physics step
LEGS = ("left_hip_yaw", "left_hip_roll", "left_hip_pitch", "left_knee", "left_ankle",
        "right_hip_yaw", "right_hip_roll", "right_hip_pitch", "right_knee", "right_ankle")


def episode(job):
    models, manifest, case, seed, shove_ns, shove_at, landing = job[:7]
    extra = list(job[7]) if len(job) > 7 else []  # diagnostics only: probe flags appended last (they win)
    sys.path.insert(0, str(RL / "cmu/mac"))
    import mujoco
    import brain_sim_check as b

    rng = np.random.default_rng([seed, 99])
    st = dict(n=0, peak=0.0, peak_after1=0.0, legs=None, trunk=None, after1=[])
    drop_h = float(rng.uniform(0.02, 0.03)) if landing else 0.0
    tilt = rng.uniform(-5, 5, 2) if landing else np.zeros(2)
    orig = getattr(mujoco, "_flight_orig_step", mujoco.mj_step)  # worker processes are reused: never wrap a wrapper
    mujoco._flight_orig_step = orig

    def step(m, d):
        if st["legs"] is None:
            st["legs"] = [m.actuator(n).id for n in LEGS]
            st["trunk"] = m.body("trunk_base").id
            if landing:  # release from the hover hand-over: raised and tilted, at rest
                q = d.qpos[3:7].copy()
                r = np.zeros(4)
                mujoco.mju_euler2Quat(r, np.radians([tilt[0], tilt[1], 0.0]), "xyz")
                out = np.zeros(4)
                mujoco.mju_mulQuat(out, r, q)
                d.qpos[3:7] = out
                d.qpos[2] += drop_h + 0.005
                d.qvel[:] = 0
                mujoco.mj_forward(m, d)
        t = st["n"] * m.opt.timestep
        if shove_ns:
            on = shove_at <= t < shove_at + 0.1
            d.xfrc_applied[st["trunk"], 0] = (shove_ns / 0.1) if on else 0.0
        orig(m, d)
        st["n"] += 1
        if FRAME_HOOK is not None:  # flight_video.py renders from here
            FRAME_HOOK(m, d, t)
        f = float(np.max(np.abs(d.actuator_force[st["legs"]])))
        st["peak"] = max(st["peak"], f)
        if t >= 1.0:
            st["peak_after1"] = max(st["peak_after1"], f)
            st["after1"].append(f)
            st.setdefault("z", []).append(float(d.xpos[st["trunk"], 2]))
        st.setdefault("per", []).append(np.abs(d.actuator_force[st["legs"]]).copy())  # every step, from t = 0

    mujoco.mj_step = step
    b.mujoco.mj_step = step
    argv = ["brain_sim_check.py", "--model", "asbuilt", "--manifest", manifest, "--volt", "7.6", "--drop", "0.036",
            "--models", models, "--stand-s", "0" if landing else "0.3", "--walk-at", str(WALK_AT), "--walk-s", str(WALK_S),
            "--seed", str(seed)] + CASES[case] + extra
    sys.argv = argv
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        b.main()
    r = json.loads(buf.getvalue().strip().splitlines()[-1])
    speed = None
    if r.get("dist_x") is not None:
        speed = round(r["dist_x"] / WALK_S, 4) if case in ("walk", "stand") else round(math.radians(r["yaw_walk_deg"]) / WALK_S, 4)
    return dict(seed=seed, fell_at=r["fell_at"], fall_dir=r["fall_dir"], max_tilt=r["max_tilt"], speed=speed,
                dist_x=r.get("dist_x"), yaw_walk_deg=r.get("yaw_walk_deg"), action_jumps=r["action_jumps"],
                peak_leg_force_nm=round(st["peak"], 4), peak_leg_force_after1s_nm=round(st["peak_after1"], 4),
                # per physics step, the largest |force| of the ten leg servos, from 1 s on: 99th percentile and the share
                # of steps at or above 95 % of the limit (the BAM model clamps at the limit)
                leg_force_p99_nm=round(float(np.percentile(st["after1"], 99)), 4) if st["after1"] else None,
                leg_force_sat_frac=round(float(np.mean(np.array(st["after1"]) >= 0.95 * LIMIT_NM)), 4) if st["after1"] else None,
                per_joint_all=None if not st.get("per") else {
                    n: dict(mean_nm=round(float(np.mean(col)), 4), p99_nm=round(float(np.percentile(col, 99)), 4),
                            sat_frac=round(float(np.mean(col >= 0.95 * LIMIT_NM)), 4))
                    for n, col in zip(LEGS, np.array(st["per"]).T)},
                # trunk_base height from 1 s on: a policy that rests the trunk or pack on the floor reads low here
                trunk_z_m=None if not st.get("z") else dict(min=round(min(st["z"]), 4), median=round(float(np.median(st["z"])), 4)),
                landing=dict(drop_m=round(drop_h, 4), tilt_deg=np.round(tilt, 2).tolist()) if landing else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--case", choices=sorted(CASES), required=True)
    ap.add_argument("--episodes", type=int, default=20)
    ap.add_argument("--shove-ns", type=float, default=0.0)
    ap.add_argument("--shove-at", type=float, default=8.0)
    ap.add_argument("--landing", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", required=True)
    ap.add_argument("--extra", default="", help="probe flags appended last, space separated (e.g. '--stand-s 0')")
    a = ap.parse_args()
    jobs = [(os.path.abspath(a.models), os.path.abspath(a.manifest), a.case, s, a.shove_ns, a.shove_at, a.landing,
             a.extra.split()) for s in range(a.episodes)]
    with ProcessPoolExecutor(a.workers) as ex:
        eps = list(ex.map(episode, jobs))
    falls = [e for e in eps if e["fell_at"] is not None]
    sp = [e["speed"] for e in eps if e["fell_at"] is None and e["speed"] is not None]
    summ = dict(models=a.models, manifest=Path(a.manifest).name, case=a.case, episodes=len(eps), falls=len(falls),
                fall_times=sorted(e["fell_at"] for e in falls), shove_ns=a.shove_ns, landing=a.landing,
                speed_median_upright=round(float(np.median(sp)), 4) if sp else None,
                speed_min_upright=round(float(np.min(sp)), 4) if sp else None,
                peak_leg_force_nm=max(e["peak_leg_force_nm"] for e in eps),
                peak_leg_force_after1s_nm=max(e["peak_leg_force_after1s_nm"] for e in eps), limit_nm=LIMIT_NM,
                max_tilt=max(e["max_tilt"] for e in eps), action_jumps_median=float(np.median([e["action_jumps"] for e in eps])))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(dict(summary=summ, episodes=eps), indent=1))
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
