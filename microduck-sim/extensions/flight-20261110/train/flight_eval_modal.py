"""Run flight_eval.py episodes on Modal CPU containers, one container per episode (the Mac mini is saturated by the
flight-sim jobs and the MacBook swaps). Same code, same probe, same pins as the Mac mini venv (sim/mini.sh setup:
mujoco 3.10.0, onnxruntime 1.24.4, numpy 2.4.1, scipy 1.18.0) plus the bam package copied from the microduck_rl venv.

  modal run train/flight_eval_modal.py --spec train/eval/<spec>.json
spec: {"evals": [{"name": ..., "models": "<dir relative to train/>", "manifest": "manifests/<file>", "case": "walk",
                  "episodes": 20, "shove_ns": 0, "shove_at": 8, "landing": false}, ...]}
Writes train/eval/<name>.json per eval (summary + episodes), same format as flight_eval.py. Cost: 1 core + 1 GiB per
episode, about $0.06 per core-hour; an episode takes about a minute.
"""
import json
import sys
from pathlib import Path

import modal

LOCAL = modal.is_local()
HERE = Path(__file__).resolve().parent
ROBO = HERE.parents[3] if LOCAL else Path("/root/robotics")
RL = ROBO / "microduck-sim/microduck_rl"
TRAIN = ROBO / "microduck-sim/extensions/flight-20261110/train"
BAM = RL / ".venv/lib/python3.12/site-packages/bam"
IGN = ["**/__pycache__/**", "**/.git/**"]
def make_image(apt=(), env=None, check=None):
    """the eval image; flight_video_modal.py adds OSMesa and a build-time render check (build steps must come before
    the add_local_* layers)"""
    base = modal.Image.debian_slim(python_version="3.12")
    if apt:
        base = base.apt_install(*apt)
    if env:
        base = base.env(env)
    # the Mac mini flight-sim venv's full package set (read 2026-11-10), so both hosts run the same probe
    base = base.pip_install("mujoco==3.10.0", "onnxruntime==1.24.4", "numpy==2.4.1", "scipy==1.18.0", "pyserial==3.5",
                            "colorama==0.4.6", "imageio==2.37.2", "imageio-ffmpeg==0.6.0", "pillow==13.0.0")
    if check:
        base = base.run_commands(check)
    return _layers(base)


def _layers(base):
    return (
    base
    .add_local_dir(str(BAM), "/usr/local/lib/python3.12/site-packages/bam", ignore=IGN)
    .add_local_dir(str(RL / "src"), "/root/robotics/microduck-sim/microduck_rl/src", ignore=IGN)
    .add_local_dir(str(RL / "cmu"), "/root/robotics/microduck-sim/microduck_rl/cmu",
                   ignore=IGN + ["finetune/**", "hardware/**", "simulator/**", "real-logs/**", "planning/**", "model/scans/**"])
    .add_local_file(str(ROBO / "microduck-sim/CURRENT-STATE.json"), "/root/robotics/microduck-sim/CURRENT-STATE.json")
    .add_local_dir(str(TRAIN), "/root/robotics/microduck-sim/extensions/flight-20261110/train",
                   ignore=IGN + ["kaggle/**", "eval/**", "video/**", "logs/**", "out/**", "ckpt/pt/**", "ckpt/progress/**"])
    )


image = make_image()
app = modal.App("microduck-flight-eval", image=image)


@app.function(cpu=1.0, memory=1024, timeout=900, retries=1, single_use_containers=True)
def run_episode(job: list) -> dict:
    import os
    name, models, manifest, case, seed, shove_ns, shove_at, landing = job[:8]
    extra = job[8] if len(job) > 8 else []
    # diagnostic switches of flight_eval.py (FLIGHT_WARMUP, FLIGHT_VX02, ...): spec key "env"; a value that starts with
    # "train/" is a path and is made absolute. One container per episode, so nothing leaks between evals.
    for k, v in (job[9] if len(job) > 9 else {}).items():
        os.environ[k] = str(TRAIN.parent / v) if str(v).startswith("train/") else str(v)
    sys.path.insert(0, str(TRAIN))
    import flight_eval
    r = flight_eval.episode((str(TRAIN / models), str(TRAIN / manifest), case, seed, shove_ns, shove_at, landing, extra))
    r["eval"] = name
    return r


@app.local_entrypoint()
def main(spec: str):
    sys.path.insert(0, str(HERE))
    import numpy as np
    import flight_eval as fe
    evals = json.loads(Path(spec).read_text())["evals"]
    jobs = []
    for e in evals:
        for s in range(e.get("episodes", 20)):
            jobs.append([e["name"], e["models"], e["manifest"], e["case"], s, e.get("shove_ns", 0.0), e.get("shove_at", 8.0),
                         bool(e.get("landing", False)), list(e.get("extra", [])), dict(e.get("env", {}))])
    print(f"{len(jobs)} episodes in {len(evals)} evals")
    res = {}
    for r in run_episode.map(jobs, order_outputs=False, return_exceptions=True):
        if isinstance(r, Exception):
            print("episode failed:", repr(r)[:300])
            continue
        res.setdefault(r["eval"], []).append(r)
    out = HERE / "eval"
    out.mkdir(exist_ok=True)
    for e in evals:
        eps = sorted(res.get(e["name"], []), key=lambda x: x["seed"])
        falls = [x for x in eps if x["fell_at"] is not None]
        up = [x for x in eps if x["fell_at"] is None]
        sp = [x["speed"] for x in up if x["speed"] is not None]
        summ = dict(name=e["name"], models=e["models"], manifest=Path(e["manifest"]).name, case=e["case"], episodes=len(eps),
                    episodes_planned=e.get("episodes", 20), falls=len(falls), fall_times=sorted(x["fell_at"] for x in falls),
                    shove_ns=e.get("shove_ns", 0.0), landing=bool(e.get("landing", False)),
                    speed_median_upright=round(float(np.median(sp)), 4) if sp else None,
                    speed_min_upright=round(float(np.min(sp)), 4) if sp else None,
                    peak_leg_force_nm_upright_eps=max((x["peak_leg_force_nm"] for x in up), default=None),
                    peak_leg_force_nm_all=max((x["peak_leg_force_nm"] for x in eps), default=None), limit_nm=fe.LIMIT_NM,
                    leg_force_p99_nm_upright_median=round(float(np.median([x["leg_force_p99_nm"] for x in up if x["leg_force_p99_nm"] is not None])), 4)
                    if any(x["leg_force_p99_nm"] is not None for x in up) else None,
                    leg_force_sat_frac_upright_max=max((x["leg_force_sat_frac"] for x in up if x["leg_force_sat_frac"] is not None), default=None),
                    max_tilt=max((x["max_tilt"] for x in eps), default=None),
                    action_jumps_median=float(np.median([x["action_jumps"] for x in eps])) if eps else None)
        # an eval whose episodes failed (missing model file, crash) must not read as "0 falls"
        summ["incomplete"] = len(eps) < e.get("episodes", 20)
        if summ["incomplete"]:
            print(f"INCOMPLETE {e['name']}: {len(eps)} of {e.get('episodes', 20)} episodes returned", flush=True)
        (out / f"{e['name']}.json").write_text(json.dumps(dict(summary=summ, episodes=eps), indent=1))
        print(json.dumps(summ))
