"""Joint-failure study: walk61 with one joint frozen or weak, 10 seeds each, on the as-built duck.

Conditions: no fault, then each of neck_pitch, head_pitch, head_yaw, head_roll, left_ankle, right_ankle frozen at its
stand angle and weak (P gain halved); walk_fault.py has the fault model. Every run: stand 1 s, stand61 at zero command
to 2 s, walk61 at vx 0.25 for 4 s, zero command for 3 s; saddle mass manifest; rail voltage and read-drop fraction
from microduck-sim/CURRENT-STATE.json via robot_state_check.py --print-sim-args; walk_wired.py's walk guards on.
Seeds change the dropped-read pattern (the only random input of brain_sim_check.py).

  ~/.venvs/microduck-dyn/bin/python run_study.py [--workers 8]      # writes results.jsonl and results.json here
Heavy: run it on the Mac mini (README.md has the command).
"""
import argparse
import datetime
import json
import os
import socket
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
MAC = os.path.join(REPO, "microduck-sim", "guide", "firmware", "mac")
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
SADDLE = "microduck-sim/guide/print/a7z-saddle/balance/manifest-saddle.json"
JOINTS = ["neck_pitch", "head_pitch", "head_yaw", "head_roll", "left_ankle", "right_ankle"]
VX, WALK_S = 0.25, 4.0


def sim_args():
    out = subprocess.run([PY, os.path.join(MAC, "robot_state_check.py"), "--print-sim-args"], capture_output=True,
                         text=True, check=True, cwd=MAC).stdout.split()
    return out


def one(cond, seed, base):
    joint, mode = cond
    cmd = [PY, os.path.join(HERE, "walk_fault.py"), "--mode", mode] + (["--joint", joint] if joint else []) + ["--"] + base + [
        "--seed", str(seed)]
    for attempt in range(3):  # under load a run can die in onnxruntime/MuJoCo teardown ("recursive_mutex lock failed")
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
        if p.returncode == 0:
            break
    if p.returncode != 0:
        return dict(fault_joint=joint, fault_mode=mode, seed=seed, error=p.stderr[-2000:], attempts=3)
    r = json.loads(p.stdout.strip().splitlines()[-1])
    r.update(seed=seed, attempts=attempt + 1)
    return r


WALKS_FALL_MAX, WALKS_DIST_MIN = 0.1, 0.5  # "still walks": at most 1 fall in 10 and half the healthy median distance


def summarise(rows):
    def stats(rs, base_dist=None):
        ok = [r for r in rs if "error" not in r]
        fell = [r for r in ok if r["fell_at"] is not None]
        dist = [r["dist_x"] for r in ok if r["dist_x"] is not None]
        out = dict(n=len(ok), errors=len(rs) - len(ok), falls=len(fell), fall_rate=round(len(fell) / len(ok), 2) if ok else None,
                    guard_stops=sum(r["guard_stop"] for r in ok),
                    fell_at=sorted(r["fell_at"] for r in fell),
                    dist_x_median=round(statistics.median(dist), 3) if dist else None,
                    dist_x_min=round(min(dist), 3) if dist else None, dist_x_max=round(max(dist), 3) if dist else None,
                    max_tilt_median=round(statistics.median(r["max_tilt"] for r in ok), 1) if ok else None,
                    yaw_walk_deg_median=round(statistics.median(r["yaw_walk_deg"] for r in ok if r["yaw_walk_deg"] is not None), 1) if ok else None,
                    retried=sum(r.get("attempts", 1) > 1 for r in rs))
        if base_dist and out["dist_x_median"] is not None:
            out["dist_ratio"] = round(out["dist_x_median"] / base_dist, 2)
            out["still_walks"] = out["fall_rate"] <= WALKS_FALL_MAX and out["dist_ratio"] >= WALKS_DIST_MIN
        return out
    base = stats([r for r in rows if r["fault_mode"] == "none"])
    per = {}
    for j in JOINTS:
        per[j] = {m: stats([r for r in rows if r["fault_joint"] == j and r["fault_mode"] == m], base["dist_x_median"])
                  for m in ("frozen", "weak")}
    return base, per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--seeds", type=int, default=10)
    args = ap.parse_args()
    state = sim_args()
    base = ["--model", "asbuilt", "--manifest", SADDLE] + state + ["--stand-s", "1", "--walk-at", "2", "--walk-s", str(WALK_S),
                                                               "--vx", str(VX), "--wired-guards", "--trace"]
    conds = [(None, "none")] + [(j, m) for m in ("frozen", "weak") for j in JOINTS]
    jobs = [(c, s) for c in conds for s in range(args.seeds)]
    t0 = datetime.datetime.now()
    with ThreadPoolExecutor(args.workers) as ex:
        rows = list(ex.map(lambda cs: one(cs[0], cs[1], base), jobs))
    with open(os.path.join(HERE, "results.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    b, per = summarise(rows)
    out = dict(
        what="walk61 with one joint frozen at its stand angle or weak (P gain halved); fall rate and forward distance",
        when=t0.isoformat(timespec="seconds"), host=socket.gethostname(), wall_s=round((datetime.datetime.now() - t0).total_seconds(), 1),
        conditions=dict(policy="walk61.onnx (runtime-overlay/models)", vx=VX, walk_s=WALK_S, seeds=args.seeds,
                        state_args=" ".join(state),
                        state_source="microduck-sim/CURRENT-STATE.json servo_rail_v and servo_read_drop_fraction via "
                                     "guide/firmware/mac/robot_state_check.py --print-sim-args (flagged stale on 2026-10-26: "
                                     "the robot was offline, not re-measured)",
                        mass=SADDLE, guards="walk_wired.py walk guards (3.0 rad action, 30 deg tilt -> stand)",
                        fall="trunk tilt over 45 deg or trunk below 0.04 m (brain_sim_check.py)",
                        dist="trunk x displacement over the walk window (dist_x)",
                        still_walks=f"fall rate <= {WALKS_FALL_MAX} and median distance >= {WALKS_DIST_MIN} x the no-fault median",
                        cmd_example=f"{PY} pet/body/failure_study/walk_fault.py --joint neck_pitch --mode frozen -- {' '.join(base)} --seed 0"),
        baseline=b, per_joint=per)
    json.dump(out, open(os.path.join(HERE, "results.json"), "w"), indent=1)
    print(json.dumps(dict(baseline=b, per_joint={j: {m: (v["falls"], v["dist_x_median"]) for m, v in d.items()} for j, d in per.items()})))


if __name__ == "__main__":
    main()
