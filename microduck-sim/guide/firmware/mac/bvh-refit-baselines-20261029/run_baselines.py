"""Every as-built sim baseline twice, without (BVH_REFIT=0) and with (BVH_REFIT=1) the body-BVH refit inside
evaluate_delay.load, same seeds and real-condition flags; each harness runs unchanged through bvh_run.py.

  cd <snapshot>/microduck-sim/guide/firmware/mac/bvh-refit-baselines-20261029
  BVH_WORKERS=5 nice -n 10 ~/.venvs/microduck-dyn/bin/python run_baselines.py [GROUP ...]   # Mac mini

Groups (results/<group>.jsonl, one row per run: group, case, seed, refit, cmd, result = the harness's JSON row,
contacts = bvh_hook's floor/missed/self-contact counts):
  suite     brain_sim_check.py, the sim_suite cases (real: nominal, vx0.25, vx0.2, com+5, imu_pitch4; stress: volt6.3,
            drop8_imu35 seeds 0/1, floor_mu bare 0.3 / sole 0.7), asbuilt manifest, walk61, 10 s walks
  teleop    teleop_sim_batch.py's eight kick / sit-stand / groundpick cases, plugged manifest, seeds 0-2
  getup     getup-20261026 stand61-recover, five starts x seeds 0-9 (saddle manifest)
  approach  approach_sim.py, the 11 suite placements, no drift (drift 0, trim 0) and robot drift (0.015 N m forward,
            trim -1.1079)
  namecall  namecall_sim.py seeds 0-11, 6 calls each (results/namecall_<refit>_<seed>.json)
  failure   pet/body/failure_study walk_fault.py: no fault + six joints frozen / weak, seeds 0-9
Real condition: robot_state_check.py --print-sim-args (CURRENT-STATE servo_rail_v, servo_read_drop_fraction).
"""
import concurrent.futures as cf
import json
import math
import os
import pathlib
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(MAC, "..", "..", "..", ".."))
SIM = os.path.join(REPO, "microduck-sim")
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
RUN = os.path.join(HERE, "bvh_run.py")
RES = os.path.join(HERE, "results")
TMP = os.path.join(HERE, "out", "tmp")
PLUGGED = os.path.join(SIM, "microduck_rl", "cmu", "model", "manifests", "plugged.json")
SADDLE = os.path.join(SIM, "guide", "print", "a7z-saddle", "balance", "manifest-saddle.json")
MODELS = os.path.join(SIM, "hardware-design-20260912", "whole-robot-20260912", "runtime-overlay", "models")
REAL = subprocess.run([PY, os.path.join(MAC, "robot_state_check.py"), "--print-sim-args"], capture_output=True, text=True,
                      check=True, cwd=MAC).stdout.split()

SUITE = [("real", "nominal", []), ("real", "vx0.25", ["--vx", "0.25"]), ("real", "vx0.2", ["--vx", "0.2"]),
         ("real", "com+5", ["--com-x", "5"]), ("real", "imu_pitch4", ["--imu-pitch", "4"]),
         ("stress", "volt6.3", ["--volt", "6.3"]), ("stress", "drop8_imu35", ["--drop", "0.08", "--imu-hz", "35", "--seed", "0"]),
         ("stress", "drop8_imu35_s1", ["--drop", "0.08", "--imu-hz", "35", "--seed", "1"]),
         ("stress", "floor_mu_bare", ["--vx", "0.25", "--floor-mu", "0.3"]), ("stress", "floor_mu_sole", ["--vx", "0.25", "--floor-mu", "0.7"])]
TELEOP = {
    "kick_left_from_stand61": ["--walk-s", "0", "--kick-at", "4", "--kick-foot", "left"],
    "kick_right_from_stand61": ["--walk-s", "0", "--kick-at", "4", "--kick-foot", "right"],
    "kick_left_from_STAND": ["--stand-s", "4", "--walk-s", "0", "--kick-at", "4", "--kick-foot", "left"],
    "kick_right_mid_walk_0.25": ["--vx", "0.25", "--walk-at", "4", "--walk-s", "4", "--kick-at", "6", "--kick-foot", "right"],
    "sit_stand_from_stand61": ["--walk-s", "0", "--sit-at", "4", "--unsit-at", "10"],
    "sit_stand_from_STAND": ["--stand-s", "4", "--walk-s", "0", "--sit-at", "4", "--unsit-at", "10"],
    "groundpick_from_stand61": ["--walk-s", "0", "--gp-at", "4", "--gp-phase", "0.33"],
    "groundpick_from_STAND": ["--stand-s", "4", "--walk-s", "0", "--gp-at", "4", "--gp-phase", "0.33"],
}
APPROACH = (((0.6, 0.0), None), ((0.86, -0.31), None), ((0.5, -0.2), None), ((0.55, 0.2), None), ((0.8, 0.35), None),
            ((0.8, 0.0), (3.0, 0.0, -0.2)), ((0.7, -0.15), (3.0, 0.0, 0.3)),
            ((0.35, -0.55), None), ((0.25, 0.45), None), ((0.45, 0.0), (5.0, 0.0, 0.15)), ((-0.2, -0.4), None))
DRIFTS = {"nodrift": ["--drift", "0", "--trim", "0"], "drift015": ["--drift", "0.015", "--trim", "-1.1079", "--drift-when", "forward"]}
# getup-20261026/run_batch.py cases: stand61-recover (the CURRENT-STATE getup fact) and three of its variants
GETUP = {"getup": ["--getup", "recover", "--hard-max-action", "99"],
         "getup_imu4": ["--getup", "recover", "--hard-max-action", "99", "--imu-pitch", "4"],
         "getup_guard3": ["--getup", "recover", "--hard-max-action", "3.0"],
         "getup_velstand": ["--getup", "recover", "--hard-max-action", "99", "--models",
                            os.path.join(MAC, "getup-20261026", "models-velstand")]}
FAULT_JOINTS = ["neck_pitch", "head_pitch", "head_yaw", "head_roll", "left_ankle", "right_ankle"]


def tasks(group):
    out = []  # (case, seed, harness argv, cwd)
    bsc = os.path.join(MAC, "brain_sim_check.py")
    if group == "suite":
        for cls, name, extra in SUITE:
            out.append((f"{cls}:{name}", None, [bsc, "--model", "asbuilt", "--walk-s", "10", "--models", MODELS] + REAL + extra, MAC))
    elif group == "teleop":
        for name, extra in TELEOP.items():
            for s in (0, 1, 2):
                out.append((name, s, [bsc, "--model", "asbuilt", "--manifest", PLUGGED] + REAL + extra + ["--seed", str(s)], MAC))
    elif group in GETUP:
        gs = os.path.join(MAC, "getup-20261026", "getup_sim.py")
        for pose in ("face_down", "face_up", "side", "sitting", "push"):
            for s in range(10):
                cmd = [gs, "--start", pose, "--seed", str(s)] + GETUP[group]
                if pose == "sitting":
                    cmd += ["--settle-kp", "200"]
                if pose == "push":
                    cmd += ["--push-dir", f"{2 * math.pi * s / 10:.4f}", "--run-s", "10"]
                out.append((pose, s, cmd, os.path.dirname(gs)))
    elif group == "approach":
        ap = os.path.join(MAC, "approach_sim.py")
        for dname, dflags in DRIFTS.items():
            for obj, move in APPROACH:
                tag = f"{dname}:obj_{obj[0]:+.2f}_{obj[1]:+.2f}" + ("_moved" if move else "")
                cmd = [ap, "--obj", str(obj[0]), str(obj[1])] + (["--move"] + [str(v) for v in move] if move else []) + dflags
                out.append((tag, None, cmd, MAC))
    elif group == "namecall":
        nc = os.path.join(MAC, "namecall-20261029", "namecall_sim.py")
        for s in range(12):
            out.append(("real", s, [nc, "--seeds", f"{s}-{s}", "--n", "6", "--out", "@OUT@"], os.path.dirname(nc)))
    elif group == "failure":
        wf = os.path.join(REPO, "pet", "body", "failure_study", "walk_fault.py")
        base = ["--model", "asbuilt", "--manifest", SADDLE] + REAL + ["--stand-s", "1", "--walk-at", "2", "--walk-s", "4.0",
                                                                     "--vx", "0.25", "--wired-guards"]
        conds = [(None, "none")] + [(j, m) for m in ("frozen", "weak") for j in FAULT_JOINTS]
        for j, m in conds:
            for s in range(10):
                out.append((f"{j or 'none'}:{m}", s, [wf, "--mode", m] + (["--joint", j] if j else []) + ["--"] + base + ["--seed", str(s)], REPO))
    return out


def slim(v, depth=0):
    if isinstance(v, dict):
        return {k: slim(x, depth + 1) for k, x in v.items() if k not in ("trace", "log", "samples", "series")}
    if isinstance(v, list) and len(v) > 40:
        return f"<list of {len(v)}>"
    return v


def run(group, case, seed, argv, cwd, refit):
    tid = f"{group}_{case}_{seed}_{refit}".replace(":", "_").replace("/", "_")
    contacts_path = pathlib.Path(TMP) / f"{tid}.jsonl"
    nc_out = os.path.join(RES, f"namecall_{refit}_{seed}.json")
    argv = [nc_out if a == "@OUT@" else a for a in argv]
    env = dict(os.environ, BVH_REFIT=str(refit), BVH_OUT=str(contacts_path))
    t0 = time.time()
    for attempt in range(3):  # onnxruntime/MuJoCo teardown abort under load ("recursive_mutex lock failed")
        if contacts_path.exists():
            contacts_path.unlink()
        p = subprocess.run([PY, RUN] + argv, capture_output=True, text=True, cwd=cwd, env=env)
        lines = [ln for ln in p.stdout.splitlines() if ln.startswith("{")]
        if p.returncode == 0 and lines:
            break
    row = dict(group=group, case=case, seed=seed, refit=refit, attempts=attempt + 1, wall_s=round(time.time() - t0, 1),
               cmd=" ".join(os.path.relpath(a, REPO) if a.startswith("/") else a for a in argv))
    if p.returncode != 0 or not lines:
        row["error"] = (p.stderr or p.stdout)[-1500:]
    elif group == "namecall":  # its stdout is a printed summary; the run's JSON file holds it
        res = json.load(open(nc_out))
        row["result"] = dict(summary=res["summary"], runs=res["runs"])
    else:
        row["result"] = slim(json.loads(lines[-1]))
    if contacts_path.exists():
        hook = [json.loads(ln) for ln in contacts_path.read_text().splitlines() if ln.strip()]
        row["contacts"] = [mdl for h in hook for mdl in h["models"]]
        contacts_path.unlink()
    return row


def main():
    groups = sys.argv[1:] or ["suite", "teleop", "getup", "approach", "namecall", "failure"]
    os.makedirs(RES, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    workers = int(os.environ.get("BVH_WORKERS", "4"))
    print("real-condition flags:", " ".join(REAL), flush=True)
    for group in groups:
        jobs = [(group, c, s, a, cwd, r) for (c, s, a, cwd) in tasks(group) for r in (0, 1)]
        t0 = time.time()
        with open(os.path.join(RES, f"{group}.jsonl"), "w") as f, cf.ThreadPoolExecutor(workers) as ex:
            for row in ex.map(lambda j: run(*j), jobs):
                f.write(json.dumps(row) + "\n")
                f.flush()
        print(f"{group}: {len(jobs)} runs in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
