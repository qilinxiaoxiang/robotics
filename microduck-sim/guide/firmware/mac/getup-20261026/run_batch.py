"""Serial get-up batch (one sim at a time; each run is about 2-3 s). Writes results.jsonl (one row per run) and
summary.json (success, rise time and loads per case).

  ~/.venvs/microduck-dyn/bin/python run_batch.py [--seeds 10] [--only CASE ...]
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
SIM = os.path.join(HERE, "getup_sim.py")
VEL = os.path.join(HERE, "models-velstand")
POSES = ("face_down", "face_up", "side", "sitting", "push")

# name -> (getup mode, extra args); --hard-max-action 3.0 is walk_wired's default, 99 means that guard is off
CASES = {
    "stand61-off": ("off", ["--hard-max-action", "99"]),
    "stand61-nogate-guard3": ("nogate", ["--hard-max-action", "3.0"]),
    "stand61-nogate": ("nogate", ["--hard-max-action", "99"]),
    "stand61-recover": ("recover", ["--hard-max-action", "99"]),
    "stand61-recover-guard3": ("recover", ["--hard-max-action", "3.0"]),
    "stand61-recover-pose0.6": ("recover", ["--hard-max-action", "99", "--set", "POSE_S", "0.6"]),
    "stand61-recover-headA7Z": ("recover", ["--hard-max-action", "99", "--manifest", "asbuilt"]),
    "stand61-recover-imu4": ("recover", ["--hard-max-action", "99", "--imu-pitch", "4"]),
    "velstand-nogate": ("nogate", ["--hard-max-action", "99", "--models", VEL]),
    "velstand-recover": ("recover", ["--hard-max-action", "99", "--models", VEL]),
    "velstand-nogate-guard3": ("nogate", ["--hard-max-action", "3.0", "--models", VEL]),
}


def one(case, pose, seed):
    mode, extra = CASES[case]
    cmd = [PY, SIM, "--start", pose, "--getup", mode, "--seed", str(seed)] + extra
    if pose == "sitting":
        cmd += ["--settle-kp", "200"]  # a seat held under torque; at KP 50 the seat tips over backwards while settling
    if pose == "push":
        cmd += ["--push-dir", f"{2 * math.pi * seed / 10:.4f}", "--run-s", "10"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    row = json.loads(out.stdout.strip().splitlines()[-1])
    row["case"] = case
    row["cmd"] = " ".join(["getup_sim.py"] + cmd[2:]).replace(HERE + "/", "")
    return row


def summarize(rows):
    out = {}
    for r in rows:
        k = f"{r['case']}|{r['start']}"
        s = out.setdefault(k, dict(case=r["case"], start=r["start"], n=0, ok=0, guard_stops=0, up_s=[], max_action=[],
                                   sat_s_max_joint=[], sat_s_total=[], peak_tau_nm={}, fell_after_up=0, gave_up=0))
        s["n"] += 1
        s["ok"] += r["success"]
        s["guard_stops"] += r["guard_stop_at"] is not None
        s["fell_after_up"] += bool(r.get("fell_after_up"))
        s["gave_up"] += any(p[1] == "gave_up" for p in r["phases"])
        if r["up_after_s"] is not None:
            s["up_s"].append(r["up_after_s"])
        s["max_action"].append(r["max_action"])
        s["sat_s_max_joint"].append(r["sat_s_max_joint"])
        s["sat_s_total"].append(r["sat_s_total"])
        for j, v in r["peak_tau_nm"].items():
            s["peak_tau_nm"][j] = max(s["peak_tau_nm"].get(j, 0.0), v)
    for s in out.values():
        for key in ("up_s", "max_action", "sat_s_max_joint", "sat_s_total"):
            v = sorted(s[key])
            s[key] = None if not v else dict(median=v[len(v) // 2], max=v[-1], min=v[0])
        s["rate"] = f"{s['ok']}/{s['n']}"
        s["sat_joints"] = sorted(j for j, v in s["peak_tau_nm"].items() if v >= 0.95 * 0.538)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--poses", nargs="*", default=list(POSES))
    ap.add_argument("--out", default=os.path.join(HERE, "results.jsonl"))
    args = ap.parse_args()
    cases = args.only or list(CASES)
    done = set()
    rows = []
    if os.path.exists(args.out):
        for line in open(args.out):
            r = json.loads(line)
            rows.append(r)
            done.add((r["case"], r["start"], r["seed"]))
    t0 = time.time()
    with open(args.out, "a") as f:
        for case in cases:
            seeds = 3 if case == "stand61-off" else args.seeds
            for pose in args.poses:
                for seed in range(seeds):
                    if (case, pose, seed) in done:
                        continue
                    r = one(case, pose, seed)
                    rows.append(r)
                    f.write(json.dumps(r) + "\n")
                    f.flush()
                    print(f"{time.time() - t0:6.0f}s {case:26s} {pose:9s} seed {seed} ok {r['success']} up {r['up_after_s']} "
                          f"maxact {r['max_action']} sat {r['sat_s_max_joint']}", flush=True)
    with open(os.path.join(HERE, "summary.json"), "w") as f:
        json.dump(summarize(rows), f, indent=1)


if __name__ == "__main__":
    main()
