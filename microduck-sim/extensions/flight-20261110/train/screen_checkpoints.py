"""Screen every checkpoint of a fetched Kaggle run on the decision cases (HISTORY-PLAN.md section 6), dev seed set.

  python3 train/screen_checkpoints.py stage fk-uni3 [--kernel fk-uni3] [--tag u3]   .pt -> train/ckpt/<tag>_<iter>/
  python3 train/screen_checkpoints.py run   fk-uni3 [--tag u3]                      five cases per checkpoint, Mac mini
  python3 train/screen_checkpoints.py table fk-uni3 [--tag u3] [--ref uni_a,fq2_1999]

`stage` converts runs/<run>/model_<iter>.pt of train/kaggle/out/<kernel>/ with ckpt2onnx.py (61-input actors only) and
copies the run's final and best ONNX; each checkpoint fills both runtime roles (walk61 and stand61). `run` goes through
accept_universal.py (seeds 0..19, files eval/ua_<tag>_<iter>_<case>.json). `table` prints falls, speed, walk torque p99
and step width per checkpoint beside the references and writes out/screen_<run>.json. A screen, not a verdict: 20
episodes without a fall bound the fall rate only below about 14 %.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
RL = TRAIN.parents[2] / "microduck_rl"
PY_RL = str(RL / ".venv/bin/python")
CASES = ["comx+10_stand", "comx+10_walk", "nominal_walk_shove05", "nominal_walk", "nopack_walk"]


def dirs(tag):
    def key(p):
        s = p.name[len(tag) + 1:]
        return (0, int(s)) if s.isdigit() else (1, 0 if s == "best" else 1)
    return sorted((p for p in (TRAIN / "ckpt").glob(f"{tag}_*") if (p / "walk61.onnx").exists()), key=key)


def stage(a):
    src = TRAIN / "kaggle/out" / a.kernel / "runs" / a.run
    if not src.exists():
        sys.exit(f"{src} missing: fetch the kernel first")
    made = []
    for pt in sorted(src.glob("model_[0-9]*.pt"), key=lambda p: int(p.stem.split("_")[1])):
        it = int(pt.stem.split("_")[1])
        d = TRAIN / "ckpt" / f"{a.tag}_{it}"
        d.mkdir(parents=True, exist_ok=True)
        if not (d / "walk61.onnx").exists():
            subprocess.run([PY_RL, str(RL / "cmu/finetune/modal/ckpt2onnx.py"), str(pt), str(d / "walk61.onnx")],
                           check=True, capture_output=True)
        shutil.copy(d / "walk61.onnx", d / "stand61.onnx")
        made.append(d.name)
    for name, suffix in (("final", ""), ("best", "_best")):
        f = src / f"{a.run}{suffix}.onnx"
        if f.exists():
            d = TRAIN / "ckpt" / f"{a.tag}_{name}"
            d.mkdir(parents=True, exist_ok=True)
            shutil.copy(f, d / "walk61.onnx")
            shutil.copy(f, d / "stand61.onnx")
            made.append(d.name)
    print("staged", made)


def run(a):
    for d in dirs(a.tag):
        subprocess.run([sys.executable, str(TRAIN / "accept_universal.py"), "run", d.name, "--only", ",".join(CASES),
                        "--chunk", "5"], check=False)


def row(models):
    out = {}
    for c in CASES:
        p = TRAIN / f"eval/ua_{models}_{c}.json"
        if not p.exists():
            out[c] = None
            continue
        d = json.loads(p.read_text())
        s = d["summary"]
        seeds = sorted(e.get("seed") for e in d.get("episodes", []))
        out[c] = dict(falls=s["falls"], episodes=len(seeds), seeds_ok=seeds == list(range(20)),
                      speed=s.get("speed_median_upright"), p99=s.get("leg_force_p99_nm_median"),
                      width=s.get("step_width_mm"), fall_times=s.get("fall_times", [])[:4])
    return out


def table(a):
    names = a.ref.split(",") + [d.name for d in dirs(a.tag)]
    res = {n: row(n) for n in names}
    print(f"{'checkpoint':14s} comx+10 stand  comx+10 walk  walk shove  nominal walk (falls, m/s, p99, width)  no-pack walk")
    for n, r in res.items():
        def f(c):
            return "  -" if r[c] is None else f"{r[c]['falls']:3d}" + ("" if r[c]["seeds_ok"] else "?")
        nw, npk = r["nominal_walk"], r["nopack_walk"]
        nws = "-" if nw is None else f"{nw['falls']}, {nw['speed']}, {nw['p99']}, {nw['width']}"
        nps = "-" if npk is None else f"{npk['falls']}, {npk['speed']}, {npk['p99']}, {npk['width']}"
        print(f"{n:14s} {f('comx+10_stand'):>13s}  {f('comx+10_walk'):>12s}  {f('nominal_walk_shove05'):>10s}  {nws:38s} {nps}")
    (TRAIN / f"out/screen_{a.run}.json").write_text(json.dumps(res, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("stage", "run", "table"))
    ap.add_argument("run")
    ap.add_argument("--kernel", default=None, help="kernel output folder under train/kaggle/out (default: the run name)")
    ap.add_argument("--tag", default="u3")
    ap.add_argument("--ref", default="uni_a,fq2_1999")
    a = ap.parse_args()
    a.kernel = a.kernel or a.run
    dict(stage=stage, run=run, table=table)[a.mode](a)


if __name__ == "__main__":
    main()
