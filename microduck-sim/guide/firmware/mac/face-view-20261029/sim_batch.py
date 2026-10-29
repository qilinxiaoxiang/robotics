"""Simulation sets for the face-view study (Mac mini batches; one process at a time on the MacBook under sim_host_guard).

Every set uses the as-built plant at the real conditions from microduck-sim/CURRENT-STATE.json (servo rail 7.0 V,
4 % dropped reads) on the cmu plugged manifest (V1.35 saddle, 6530B, camera lead; the stand-saddle study's model).
Rows go to results/<set>.jsonl with the command line or the in-process arguments; the camera numbers come from
facegeom on the pose the sim actually reached (mean q and gb over the window), not on the commanded pose.

  policy_head   stand61 at zero command with a head_pose command (deltas from the default head, brain_sim_check
                --dance), from poses_policy.json; fell, peak tilt, head reached, camera elevation. Seeds 0-2.
  walk_head     walk61 at 0.25 m/s for 6 s with --head-pitch (absolute head_pitch target): the look-up while walking.
  sit           sitstand61 seat (--sit-at 4) with --sit-head deltas from poses_sit.json; the seated trunk tilt and
                the camera elevation with the head up. 20 s.
  gp            groundpick61 bow (phase 0.4, held 4 s): the camera in the bow (the wrong direction, recorded).
  openloop      open-loop stand (walk_brain stand mode, KP 400) holding a candidate 14-joint pose from
                poses_openloop.json, as stand-saddle-20261026/olsearch.py: start from the stand61 pose, 2 s ramp,
                hold; whole-robot COM moved dx in (-2.0, -2.5, -3.0) mm (the robot's calibrated range), seeds 0-2
                with N(0, 0.03 rad) start-pose noise, T 8 s (ramp 2 s + hold 6 s), plus a 0.1 m/s push each way at
                4 s at dx -2.5. Reports falls, tilt after 5 s, rest pitch and the camera from the target head pose at
                the rest trunk pitch.
  lying         on the back (getup_sim face-up placement), servos at KP 50 for 1.5 s then KP 400 holding the head
                pose for 3 s: camera height and elevation for several head pitches.

  ~/.venvs/microduck-dyn/bin/python sim_batch.py <set> [--workers N]
"""
import argparse
import json
import math
import multiprocessing as mp
import os
import subprocess
import sys
import tempfile

SIM_PYTHON = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
if os.path.realpath(sys.prefix) != os.path.realpath(os.path.dirname(os.path.dirname(SIM_PYTHON))):
    os.execv(SIM_PYTHON, [SIM_PYTHON, os.path.abspath(__file__)] + sys.argv[1:])

import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, MAC)
sys.path.insert(0, os.path.join(MAC, "stand-gap-20261021"))
RES = os.path.join(HERE, "results")
TICKS = os.path.join(HERE, "results", "ticks")
MANIFEST = os.path.abspath(os.path.join(MAC, "..", "..", "..", "microduck_rl", "cmu", "model", "manifests", "plugged.json"))
STATE = json.load(open(os.path.join(MAC, "..", "..", "..", "CURRENT-STATE.json")))["facts"]
VOLT = float(STATE["servo_rail_v"]["value"])
DROP = float(STATE["servo_read_drop_fraction"]["value"])
BSC = os.path.join(MAC, "brain_sim_check.py")
COMMON = ["--model", "asbuilt", "--manifest", MANIFEST, "--volt", str(VOLT), "--drop", str(DROP)]
from walk_brain import NAMES  # noqa: E402  (the order of info["q"] in the tick log: walk_brain's servo order)


def window_pose(tick_path, t0, t1):
    """Mean q (dict) and gb over rows with t0 <= t < t1, and the peak tilt in that window."""
    qs, gbs, tilt = [], [], 0.0
    with open(tick_path) as f:
        for line in f:
            r = json.loads(line)
            if t0 <= r["t"] < t1 and r.get("q") is not None and r.get("gb") is not None:
                qs.append(r["q"]); gbs.append(r["gb"])
                g = np.asarray(r["gb"], float); g = g / np.linalg.norm(g)
                tilt = max(tilt, math.degrees(math.acos(float(np.clip(-g[2], -1, 1)))))
    if not qs:
        return None, None, None
    q = dict(zip(NAMES, np.mean(qs, axis=0).tolist()))
    gb = tuple(np.mean(gbs, axis=0).tolist())
    return q, gb, round(tilt, 2)


def camera_block(q, gb):
    import facegeom as fg
    rep = fg.posture_report(q, gb)
    rep.pop("name")
    return rep


def run_bsc(label, extra, tick_name, window, seed=0):
    os.makedirs(TICKS, exist_ok=True)
    tick = os.path.join(TICKS, f"{tick_name}_s{seed}.jsonl")
    cmd = [SIM_PYTHON, BSC] + COMMON + ["--seed", str(seed), "--tick-log", tick] + extra
    env = dict(os.environ, MICRODUCK_SIM_LOCAL_OK=os.environ.get("MICRODUCK_SIM_LOCAL_OK", ""))
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    out = {}
    for line in p.stdout.splitlines()[::-1]:
        if line.startswith("{"):
            out = json.loads(line); break
    row = dict(label=label, seed=seed, cmd=" ".join(cmd), fell=out.get("fell"), max_tilt=out.get("max_tilt"),
               tick=tick, window=window, rc=p.returncode, stderr_tail=p.stderr[-400:] if p.returncode else "")
    for k in ("sit", "gp", "walk"):
        if k in out:
            row[k] = out[k]
    return analyze(row)


def analyze(row):
    """The camera numbers of a brain_sim_check row from its tick log (re-run by `reanalyze SET` without simulating)."""
    if "tick" not in row:
        parts = row["cmd"].split()
        row["tick"] = parts[parts.index("--tick-log") + 1]
    q, gb, wtilt = window_pose(row["tick"], *row["window"])
    row["window_tilt"] = wtilt
    if q is not None:
        row["reached_head"] = {n: round(q[n], 3) for n in ("neck_pitch", "head_pitch", "head_yaw", "head_roll")}
        row["reached_q"] = {n: round(q[n], 4) for n in NAMES}
        row["trunk_gb"] = [round(x, 4) for x in gb]
        row["camera"] = camera_block(q, gb)
    return row


def dance_file(deltas):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=RES)
    json.dump({"about": "face-view head command", "end_s": 30.0, "steps": [{"t": 0.0, "head": deltas}]}, f)
    f.close()
    return f.name


def job(spec):
    kind, label, args, seed = spec
    if kind == "policy_head":
        return run_bsc(label, ["--stand-s", "1", "--walk-at", "2", "--vx", "0", "--walk-s", "12", "--until", "14",
                               "--dance", dance_file(args)], f"ph_{label}", (10.0, 14.0), seed)
    if kind == "walk_head":
        return run_bsc(label, ["--stand-s", "1", "--walk-at", "2", "--vx", "0.25", "--walk-s", "6", "--until", "12",
                               "--head-pitch", str(args), "--head-yaw", "0"], f"wh_{label}", (4.0, 8.0), seed)
    if kind == "sit":
        return run_bsc(label, ["--stand-s", "1", "--walk-at", "2", "--vx", "0", "--walk-s", "1", "--sit-at", "4",
                               "--until", "20"] + (["--sit-head", json.dumps(args)] if args else []),
                       f"sit_{label}", (14.0, 20.0), seed)
    if kind == "gp":
        return run_bsc(label, ["--stand-s", "1", "--walk-at", "2", "--vx", "0", "--walk-s", "1", "--gp-at", "4",
                               "--gp-phase", "0.4", "--gp-hold-s", "4", "--until", "14"], f"gp_{label}", (6.0, 8.0), seed)
    if kind == "openloop":
        return openloop_job(label, args, seed)
    if kind == "lying":
        return lying_job(label, args)
    raise ValueError(kind)


def openloop_job(label, args, seed):
    import comsim
    import facegeom as fg
    comsim.S.MANIFEST = MANIFEST
    pose, dx, push = args["pose"], args["dx"], args.get("push")
    s61 = json.load(open(os.path.join(MAC, "stand-saddle-20261026", "stand61_real_1026.json")))
    rng = np.random.default_rng(seed)
    # rounds 1-2 (O_, O2_) added N(0, 0.03 rad) start noise on all 14 joints; the STAND control showed that noise alone
    # tips the open-loop stand (7 of 11 falls, 0 of 11 without), so round 3 on (O3_) starts from the stand61 pose exactly
    # and takes its spread from the COM range, the pushes and the read-drop seeds, as stand-saddle-20261026 did
    sd = 0.03 if (label.startswith(("O_", "O2_")) and not label.endswith("_noise0")) else 0.0
    start = {n: s61[n] + float(rng.normal(0, sd)) for n in NAMES}
    ramp_s = args.get("ramp_s")  # what-if: a slower entry ramp than walk_brain's 2 s (openloop4: is the fall static or from the swing?)
    r = comsim.run(pose, dx, start=start, T=8.0 + (ramp_s or 0.0), seed=seed, push=tuple(push) if push else None, ramp_s=ramp_s)
    tr = r.pop("trace") or []
    r.update(label=label, seed=seed, dx_mm=dx, push=push, pose=pose,
             pitch_trace=[(round(t, 2), round(p, 2)) for t, _, p, _ in tr[::4]])
    rest_pitch = r["end_pitch"] if r["fell_at"] is None else None
    if rest_pitch is not None:
        # end_pitch is nose-down positive in stand_sim (atan2(-R20, R22)), the same convention as facegeom.gb_from_pitch
        gb = fg.gb_from_pitch(rest_pitch)
        r["camera"] = camera_block(pose, gb)
    return r


def lying_job(label, head):
    """Face-up on the floor: place as getup_sim does, settle at KP 50, then hold STAND legs + the head pose at KP 400."""
    sys.path.insert(0, os.path.join(MAC, "getup-20261026"))
    import getup_sim as gs
    import mujoco
    from walk_brain import STAND
    import duck_kin
    c0 = gs.cfg(0.09, model="asbuilt", kp=400, voltage=VOLT)
    c0["mass_manifest"] = MANIFEST
    m, d, c, names, bam = gs.ev.load(c0)
    pose = dict(STAND, **head)
    quat = np.array([gs.S2, 0, -gs.S2, 0])  # -90 deg pitch: back to the floor (getup_sim face_up, no yaw/roll noise)
    gs.place(m, d, names, pose, quat)
    ji = np.array([m.actuator(n).trnid[0] for n in names])
    qa = m.jnt_qposadr[ji]
    c.q_target = np.array([pose[n] for n in names])
    sub = round(0.02 / m.opt.timestep)
    for kp, T in ((50, 1.5), (400, 3.0)):
        bam.actuator.kp = kp
        for _ in range(int(T / 0.02)):
            for _ in range(sub):
                c.update(); mujoco.mj_step(m, d)
    kin = duck_kin.DuckKin()
    s = kin.cam_site
    b = m.body("jaw_soft").id
    Rb, pb = d.xmat[b].reshape(3, 3), d.xpos[b]
    pos, R = kin.camera_from_body(Rb, pb)
    import facegeom as fg
    trunk = m.body("trunk_base").id
    Rt = d.xmat[trunk].reshape(3, 3)
    reached = {n: round(float(d.qpos[qa[names.index(n)]]), 3) for n in ("neck_pitch", "head_pitch", "head_yaw", "head_roll")}
    row = dict(label=label, head=head, reached_head=reached, cam_height_m=round(float(pos[2]), 3),
               elev_deg=round(fg.elevation_deg(R), 1), image_roll_deg=round(fg.image_roll_deg(R), 1),
               trunk_z_m=round(float(d.xpos[trunk, 2]), 3), trunk_pitch_deg=round(math.degrees(math.atan2(-Rt[2, 0], Rt[2, 2])), 1),
               faces={})
    for D in (0.3, 0.5, 1.0):
        for person, H in fg.PEOPLE.items():
            row["faces"][f"{person}@{D}"] = fg.face_view(pos, R, D, H)
    return row


def specs(name):
    if name == "policy_head":
        poses = json.load(open(os.path.join(HERE, "poses_policy.json")))
        return [("policy_head", k, v, s) for k, v in poses.items() for s in (0, 1, 2)]
    if name == "walk_head":
        return [("walk_head", f"hp{x:+.2f}", x, s) for x in (-0.75, -0.40, -0.15) for s in (0, 1, 2)]
    if name == "sit":
        poses = json.load(open(os.path.join(HERE, "poses_sit.json")))
        return [("sit", k, v, s) for k, v in poses.items() for s in (0, 1)]
    if name == "gp":
        return [("gp", "phase0.4", None, s) for s in (0, 1)]
    if name.startswith("openloop"):  # openloop -> poses_openloop.json, openloop2 -> poses_openloop2.json, ...
        poses = json.load(open(os.path.join(HERE, f"poses_{name}.json")))
        extra = dict(ramp_s=6.0) if name == "openloop4" else {}  # openloop4: round-3 poses with a 6 s entry ramp
        out = []
        for k, p in poses.items():
            for dx in (-2.0, -2.5, -3.0):
                for s in (0, 1, 2):
                    out.append(("openloop", k, dict(pose=p, dx=dx, **extra), s))
            for pv in (0.1, -0.1):
                out.append(("openloop", k, dict(pose=p, dx=-2.5, push=(4.0 + extra.get("ramp_s", 0.0), pv), **extra), 0))
        return out
    if name == "lying":
        poses = json.load(open(os.path.join(HERE, "poses_lying.json")))
        return [("lying", k, v, 0) for k, v in poses.items()]
    raise ValueError(name)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("set")
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()
    if args.set.startswith("reanalyze:"):
        name = args.set.split(":", 1)[1]
        path = os.path.join(RES, f"{name}.jsonl")
        rows = [analyze(json.loads(l)) for l in open(path) if l.strip()]
        with open(path, "w") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
        print("reanalyzed", path, len(rows))
        sys.exit(0)
    if args.workers <= 1:
        import sim_host_guard
        sim_host_guard.one_sim_on_laptop("face-view " + args.set)
    os.makedirs(RES, exist_ok=True)
    sp = specs(args.set)
    out_path = os.path.join(RES, f"{args.set}.jsonl")
    with open(out_path, "w") as f:
        if args.workers > 1:
            with mp.get_context("spawn").Pool(args.workers) as pool:
                for row in pool.imap_unordered(job, sp):
                    f.write(json.dumps(row) + "\n"); f.flush()
                    print(row.get("label"), row.get("seed"), "fell", row.get("fell", row.get("fell_at")), "elev", (row.get("camera") or row).get("elev_deg"), flush=True)
        else:
            for s in sp:
                row = job(s)
                f.write(json.dumps(row) + "\n"); f.flush()
                print(row.get("label"), row.get("seed"), "fell", row.get("fell", row.get("fell_at")), "elev", (row.get("camera") or row).get("elev_deg"), flush=True)
    print("wrote", out_path)
