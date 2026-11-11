"""Probe training checkpoints in the failing probe (flight_eval on Modal CPU), pulled from each run's Modal Volume.

  python3 train/probe_ckpt.py fw1:600 fw2:600 [fs1:400+fw1:600] [--episodes 20] [--cases stand,walk]
A target is RUN:ITER (that checkpoint fills both runtime roles: walk61 and stand61, the walk policy holding zero
command) or STAND_RUN:ITER+WALK_RUN:ITER (stand checkpoint in the stand61 slot, walk checkpoint in walk61).
Steps: `modal volume get` model_<ITER>.pt into train/ckpt/pt/, ckpt2onnx.py (the microduck_rl venv) into
train/ckpt/<tag>/{walk61,stand61}.onnx, write train/specs/probe_<tag>.json (nominal pack, one eval per case), run
flight_eval_modal.py, print falls / speed / p99 force per eval. Results land in train/eval/probe_<tag>_<case>.json.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
RL = TRAIN.parents[2] / "microduck_rl"
MODAL = "/Users/xiangzheng/code/robotics/omx-local/.venv/bin/modal"
PY_RL = str(RL / ".venv/bin/python")


def onnx_for(run, it):
    pt = TRAIN / "ckpt/pt" / f"{run}_model_{it}.pt"
    if not pt.exists():
        pt.parent.mkdir(parents=True, exist_ok=True)
        tmp = TRAIN / "ckpt/pt/_get"
        tmp.mkdir(parents=True, exist_ok=True)
        subprocess.run([MODAL, "volume", "get", "--force", f"microduck-flight-{run}", f"runs/{run}/model_{it}.pt", str(tmp)], check=True)
        if not (tmp / f"model_{it}.pt").exists():
            sys.exit(f"{run} model_{it}.pt is not on its Volume yet")
        (tmp / f"model_{it}.pt").rename(pt)
    out = TRAIN / "ckpt/onnx" / f"{run}_{it}.onnx"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([PY_RL, str(RL / "cmu/finetune/modal/ckpt2onnx.py"), str(pt), str(out)], check=True, capture_output=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--episodes", type=int, default=20)
    ap.add_argument("--cases", default="stand,walk")
    ap.add_argument("--manifest", default="manifests/flightpack-nominal.json")
    a = ap.parse_args()
    evals = []
    for t in a.targets:
        parts = t.split("+")
        sr, si = parts[0].split(":")
        wr, wi = (parts[1] if len(parts) > 1 else parts[0]).split(":")
        tag = t.replace(":", "_").replace("+", "__")
        d = TRAIN / "ckpt" / tag
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy(onnx_for(wr, wi), d / "walk61.onnx")
        shutil.copy(onnx_for(sr, si), d / "stand61.onnx")
        for c in a.cases.split(","):
            # --stand-s 0: the policy from the first tick. The runtime's open-loop stand mode alone falls at 0.54 s with
            # the pack (eval/olstand_pack.json), so a 0.3 s open-loop stand start measures that mode, not the policy
            evals.append(dict(name=f"probe_{tag}_{c}", models=f"ckpt/{tag}", manifest=a.manifest, case=c, episodes=a.episodes,
                              extra=["--stand-s", "0"]))
    spec = TRAIN / "specs" / f"probe_{'_'.join(e['name'] for e in evals)[:80]}.json"
    spec.write_text(json.dumps(dict(evals=evals)))
    subprocess.run([MODAL, "run", str(TRAIN / "flight_eval_modal.py"), "--spec", str(spec)], check=True, cwd=TRAIN.parent,
                   stdout=subprocess.DEVNULL)
    for e in evals:
        s = json.loads((TRAIN / "eval" / f"{e['name']}.json").read_text())["summary"]
        print(f"{e['name']}: falls {s['falls']}/{s['episodes']} at {s['fall_times'][:5]} speed {s['speed_median_upright']} "
              f"p99 {s.get('leg_force_p99_nm_upright_median')} sat {s.get('leg_force_sat_frac_upright_max')} tilt {s['max_tilt']}")


if __name__ == "__main__":
    sys.exit(main())
