"""Acceptance of a seeing-pick pack fine-tune (FP-R7, REQUIREMENTS.json) in the runtime sim, on the Mac mini.

  python3 train/accept_seepick.py run <models dir under train/ckpt> [--set dev|final] [--only case,...] [--redo]
  python3 train/accept_seepick.py score <models dir> [--set dev|final] [--ref bend_spec]

The models dir holds the fine-tuned seepick61.onnx plus the stand slot it hands back to (stand61.onnx / walk61.onnx;
fq2 1999 for the pack loads, as ckpt/bend4 does). `run` runs the pickup test of 2026-11-12 (pickup_pack.sh: stand,
walk61 at zero command from 1 s, the seeing pick switched in at 4 s, wired guards, elliptic cone, impratio 10) for the
12 mm ball and the drawn box at no pack (flightpack-none), batteries out (nobatt) and the full pack (load100), through
train/mini.sh (one simulation at a time, behind other sessions' jobs), and pulls train/eval/<prefix>_<dir>_<load>_<shape>
[_c<k>].json back. Seed sets as accept_universal.py: "dev" seeds 0..19 (prefix spa) for picking checkpoints, "final"
seeds 1000..1099 (prefix spaf, 100 episodes, run as five 20-seed chunks so each job stays under 10 minutes), never
used for picking. `score` prints, per case, held at the hand-back, held at the end, falls, the fall times and the leg
torque p99, beside the reference dir's numbers from the same seed set (run the reference with `run` too; the original
pick policy without the pack is ckpt/bend_spec, the FP-R7 baseline).
Held = probe.seepick.at_handback.held (pinched, off the floor, lifted over 1 cm), at_end.held 3 s later.
"""
import argparse
import json
import subprocess
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
SP = "--stand-s 0 --walk-at 1 --walk-s 0 --wired-guards --sp-at 4 --sp-cone elliptic --sp-impratio 10"
SHAPES = {"ball": "--sp-shape ball --sp-size 0.012", "box": "--sp-shape box"}
LOADS = ("none", "nobatt", "load100")
SETS = {"dev": dict(prefix="spa", seed0=0, episodes=20, chunk=20),
        "final": dict(prefix="spaf", seed0=1000, episodes=100, chunk=20)}


def cases():
    return [dict(name=f"{ld}_{sh}", load=ld, shape=sh) for ld in LOADS for sh in SHAPES]


def chunks(s):
    return [(k, s["seed0"] + k * s["chunk"], min(s["chunk"], s["episodes"] - k * s["chunk"]))
            for k in range((s["episodes"] + s["chunk"] - 1) // s["chunk"])]


def out_path(s, models, case, k, n_chunks):
    tag = f"_c{k}" if n_chunks > 1 else ""
    return f"train/eval/{s['prefix']}_{models}_{case['name']}{tag}.json"


def command(s, models, case, k, seed0, n, n_chunks):
    out = out_path(s, models, case, k, n_chunks)
    name = Path(out).stem
    return (f"$PY train/style_eval.py --name {name} --models train/ckpt/{models} "
            f"--manifest train/manifests/flightpack-{case['load']}.json --case stand --episodes {n} --workers 8 "
            f"--seed0 {seed0} --extra='{SP} {SHAPES[case['shape']]}' --out {out} > /dev/null 2>&1; echo done {name}")


def run(a, s):
    mini = str(TRAIN / "mini.sh")
    subprocess.run(["zsh", mini, "push"], check=True, capture_output=True)
    ch = chunks(s)
    todo = []
    for c in cases():
        if a.only and c["name"] not in a.only.split(","):
            continue
        for k, seed0, n in ch:
            if a.redo or not (TRAIN.parent / out_path(s, a.models, c, k, len(ch))).exists():
                todo.append((c, k, seed0, n))
    print(f"{len(todo)} jobs for {a.models} ({a.set}: seeds {s['seed0']}..{s['seed0'] + s['episodes'] - 1})", flush=True)
    for c, k, seed0, n in todo:  # one style_eval per mini.sh call: each well under 10 minutes
        r = subprocess.run(["zsh", mini, "run", command(s, a.models, c, k, seed0, n, len(ch))],
                           capture_output=True, text=True)
        print(r.stdout.replace("busy\n", "").strip()[-300:], flush=True)
        subprocess.run(["zsh", mini, "pull"], check=True, capture_output=True)


def load(s, models, case):
    ch = chunks(s)
    eps = []
    for k, _, _ in ch:
        p = TRAIN.parent / out_path(s, models, case, k, len(ch))
        if not p.exists():
            return None
        eps += json.loads(p.read_text()).get("episodes", [])
    want = list(range(s["seed0"], s["seed0"] + s["episodes"]))
    got = sorted(e.get("seed") for e in eps)
    if got != want:
        print(f"seed check: {models} {case['name']} has {len(got)} episodes, expected seeds {want[0]}..{want[-1]}")
        return None
    sp = [e.get("probe", {}).get("seepick", {}) for e in eps]
    hb = sum(bool((x.get("at_handback") or {}).get("held")) for x in sp)
    end = sum(bool((x.get("at_end") or {}).get("held")) for x in sp)
    falls = [e["fell_at"] for e in eps if e.get("fell_at") is not None]
    p99 = sorted(e.get("leg_force_p99_nm") or 0.0 for e in eps)
    leg = {}
    for j in ("left_hip_pitch", "left_knee", "right_hip_pitch", "right_knee"):
        v = sorted((e.get("per_joint_all") or {}).get(j, {}).get("p99_nm", 0.0) for e in eps)
        leg[j] = v[len(v) // 2]
    return dict(n=len(eps), held_handback=hb, held_end=end, falls=len(falls),
                fall_times=sorted(round(t, 2) for t in falls)[:6], leg_p99_median=p99[len(p99) // 2], pitch_p99_median=leg)


def score(a, s):
    rows = []
    for c in cases():
        r, f = load(s, a.models, c), load(s, a.ref, c)
        rows.append(dict(case=c["name"], result=r, ref=f))
        if r is None:
            print(f"MISSING {c['name']}")
            continue
        ref = (f"{a.ref}: held {f['held_handback']}/{f['n']} (end {f['held_end']}), falls {f['falls']}" if f
               else f"{a.ref}: not run")
        print(f"{c['name']:15s} held at hand-back {r['held_handback']}/{r['n']}, held at end {r['held_end']}, "
              f"falls {r['falls']} {r['fall_times']}, leg p99 {r['leg_p99_median']}, pitch p99 {r['pitch_p99_median']}"
              f"  || {ref}")
    suffix = "" if a.set == "dev" else f"_{a.set}"
    out = dict(models=a.models, ref=a.ref, set=a.set, seeds=f"{s['seed0']}..{s['seed0'] + s['episodes'] - 1}",
               command=SP, rows=rows)
    (TRAIN / f"out/accept_seepick_{a.models}{suffix}.json").write_text(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("run", "score"))
    ap.add_argument("models")
    ap.add_argument("--set", choices=sorted(SETS), default="dev")
    ap.add_argument("--only", default="")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--ref", default="bend_spec")
    a = ap.parse_args()
    s = SETS[a.set]
    run(a, s) if a.mode == "run" else score(a, s)


if __name__ == "__main__":
    main()
