"""Step 1 of the seeing-pick gap study (2026-10-29): the installed policy's source (cmu/grasp/policies/sp-b-1027_2000.onnx)
in the training env's own eval (gap_trace.py, the eval's domain randomisation on) with exactly the rehearsal's 54 object
draws and placements (results/main.jsonl of seepick-rehearsal-20261027: shape, per-axis half extents, mass, friction,
object yaw, offset from the landing spot). One row per case in results/train_eval.jsonl with its command line and the
training success measure (grasp_held paid on >= 20 steps; 8 envs per case, each with its own DR draw).

  python3 run_train_eval.py --grasp-root <microduck_rl-grasp checkout with .venv> --main <rehearsal main.jsonl> \
      --scratch <dir for the per-tick traces> [--workers 2]
"""
import argparse
import concurrent.futures as cf
import json
import os
import shlex
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def cases(main_path):
    out = []
    for line in open(main_path):
        row = json.loads(line)
        o = row["result"]["seepick"]["object"]
        out.append(dict(case="train-eval", dx=row["dx"], dy=row["dy"], shape=row["shape"], seed=row["seed"],
                        half=o["half"], mass=o["mass"], mu=o["mu"], yaw_deg=o["yaw_deg"], size=o["size"]))
    return out


def run_one(meta, a):
    py = os.path.join(a.grasp_root, ".venv", "bin", "python")
    out = os.path.join(a.scratch, f"{meta['shape']}_{meta['dx']:+.2f}_{meta['dy']:+.2f}_s{meta['seed']}")
    cmd = [py, "cmu/grasp/gap_trace.py", "--out", out, "--num-envs", str(a.num_envs), "--seed", str(meta["seed"]),
           "--exact", "--shape", meta["shape"], "--half", *[str(v) for v in meta["half"]], "--mass", str(meta["mass"]),
           "--mu", str(meta["mu"]), "--object-yaw", str(meta["yaw_deg"]), "--offset", str(meta["dx"]), str(meta["dy"])]
    line = " ".join(shlex.quote(c) for c in cmd)
    t0 = time.time()
    try:
        p = subprocess.run(["nice", "-n", "10"] + cmd, cwd=a.grasp_root, capture_output=True, text=True, timeout=a.timeout)
    except subprocess.TimeoutExpired:
        return dict(meta, cmd=line, error=f"timeout {a.timeout} s")
    last = [x for x in p.stdout.splitlines() if x.startswith("{")]
    if p.returncode or not last:
        return dict(meta, cmd=line, error=(p.stderr or p.stdout)[-2000:])
    r = json.loads(last[-1])
    return dict(meta, cmd=line, trace=out + ".jsonl", wall_s=round(time.time() - t0), result=r)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--grasp-root", required=True)
    ap.add_argument("--main", required=True)
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--num-envs", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--out", default=os.path.join(HERE, "results", "train_eval.jsonl"))
    ap.add_argument("--only", type=int, default=None, help="run only the first N cases")
    a = ap.parse_args()
    os.makedirs(a.scratch, exist_ok=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    todo = cases(a.main)[: a.only]
    with open(a.out, "w") as f, cf.ThreadPoolExecutor(a.workers) as ex:
        for row in ex.map(lambda m: run_one(m, a), todo):
            f.write(json.dumps(row) + "\n")
            f.flush()
            r = row.get("result", {})
            print(json.dumps({k: row.get(k) for k in ("shape", "dx", "dy", "seed", "wall_s", "error")}
                             | {"success": r.get("success"), "held_steps": r.get("held_steps"), "pinched": r.get("pinched_ever")}),
                  flush=True)


if __name__ == "__main__":
    main()
