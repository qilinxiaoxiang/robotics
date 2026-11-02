"""Walk-up then T2 bite in the as-built sim: approach_sim's end states (../approach-handover-20261101/runs-varB) become
the object placements of brain_sim_check.py --sp-pix with spx-b_2400 as seepickpix61.onnx (../models-t2). Run on the Mac mini.

  python3 run_chain.py <stage> ...   stages: control, plugged, plugged_trainmu, battery
  python3 run_chain.py summary       results/summary.json and one line per stage

Stages (ball 12 mm, 1.1 g, 7.0 V, three seeds per end state unless stated):
  control          nine placements within +-1 cm, training friction draw, 4 % read drops: the harness against the eval
  plugged          plugged manifest, friction 0.45 (printed PLA), 17 % read drops (CURRENT-STATE servo_read_drop_fraction)
  plugged_trainmu  as plugged with the training friction draw 0.35-1.1
  battery          battery manifest, friction 0.45, 17 % read drops
"""
import concurrent.futures as cf
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
RES = os.path.join(HERE, "results")
WORKERS = int(os.environ.get("CHAIN_WORKERS", "6"))
SPOT = 0.087
SEEDS = (0, 1, 2)
STOPS = os.path.join(MAC, "approach-handover-20261101", "runs-varB", "summary.json")
MANIFEST = "../../../microduck_rl/cmu/model/manifests/%s.json"


def head_for(r, b):
    """The hand-over look: the T2 reset's pitch from the range within what gaze.py commands, yaw = bearing."""
    return min(1.35, max(0.349, 1.1 + (0.245 - r) * (0.3 / 0.086))), max(-0.6, min(0.6, b))


def cases(stage):
    if stage == "control":
        return [dict(case=f"x{dx:+.2f}_y{dy:+.2f}", r=math.hypot(SPOT + dx, dy), b=math.atan2(dy, SPOT + dx), seed=s,
                     manifest="plugged", mu=None, drop=0.04)
                for dx in (-0.01, 0.0, 0.01) for dy in (-0.01, 0.0, 0.01) for s in SEEDS]
    rows = json.load(open(STOPS))["rows"]
    mu, man = {"plugged": (0.45, "plugged"), "plugged_trainmu": (None, "plugged"), "battery": (0.45, "battery")}[stage]
    return [dict(case=x["case"], r=x["r"], b=math.radians(x["bearing"]), seed=s, manifest=man, mu=mu, drop=0.17)
            for x in rows if x["ok"] for s in SEEDS]


def run(c):
    hp, hy = head_for(c["r"], c["b"])
    cmd = [PY, "brain_sim_check.py", "--model", "asbuilt", "--manifest", MANIFEST % c["manifest"], "--com-x", "-2.25",
           "--volt", "7.0", "--drop", str(c["drop"]), "--wired-guards", "--walk-s", "0", "--walk-at", "1",
           "--head-pitch", f"{hp:.3f}", "--head-yaw", f"{hy:.3f}", "--sp-at", "4",
           "--sp-offset", f"{c['r'] * math.cos(c['b']) - SPOT:.4f}", f"{c['r'] * math.sin(c['b']):.4f}",
           "--sp-shape", "ball", "--sp-half", "0.006", "0.006", "0.006", "--sp-mass", "1.1",
           "--sp-cone", "elliptic", "--sp-impratio", "10", "--sp-pix", "--models", "models-t2", "--seed", str(c["seed"])]
    if c["mu"] is not None:
        cmd += ["--sp-friction", str(c["mu"])]
    for _ in range(3):   # libc++ recursive_mutex crash under load (seepick-rehearsal README)
        p = subprocess.run(cmd, cwd=MAC, capture_output=True, text=True)
        lines = p.stdout.strip().splitlines()
        if lines and lines[-1].startswith("{"):
            d = json.loads(lines[-1])
            s, e = d["seepick"], d["seepick"]["events"]
            ca = e.get("close_at") or {}
            return dict(c, head=[round(hp, 3), round(hy, 3)], train=e.get("held_ticks", 0) >= 20,
                        held_ticks=e.get("held_ticks", 0), handback=bool((s.get("at_handback") or {}).get("held")),
                        end=bool((s.get("at_end") or {}).get("held")), fell_at=d["fell_at"],
                        guard=(s.get("guard") or {}).get("why"), tilt=round(e["max_tilt"], 1),
                        pad_err_m=ca.get("pad_xy_err_m"), pinched_t=e.get("first_pinched_t"),
                        seen_at_start=s["camera"]["handover"]["seen"], handover=s["camera"]["handover"],
                        frames_visible=s["camera"]["visible"], end_mode=d["end_mode"], cmd=" ".join(cmd))
    return dict(c, error=(p.stderr or p.stdout)[-600:], cmd=" ".join(cmd))


def summary():
    out = {}
    for f in sorted(os.listdir(RES)):
        if not f.endswith(".jsonl"):
            continue
        rows = [json.loads(x) for x in open(os.path.join(RES, f))]
        ok = [x for x in rows if "error" not in x]
        n = max(1, len(ok))
        errs = [x["pad_err_m"] for x in ok if x["pad_err_m"] is not None]
        out[f[:-6]] = dict(runs=len(rows), errors=len(rows) - len(ok), train=round(sum(x["train"] for x in ok) / n, 3),
                           handback=round(sum(x["handback"] for x in ok) / n, 3), end=round(sum(x["end"] for x in ok) / n, 3),
                           fell=sum(bool(x["fell_at"]) for x in ok), guard=sum(bool(x["guard"]) for x in ok),
                           seen_at_start=round(sum(x["seen_at_start"] for x in ok) / n, 3),
                           pad_err_median_m=sorted(errs)[len(errs) // 2] if errs else None)
        print(f[:-6], out[f[:-6]])
    json.dump(out, open(os.path.join(RES, "summary.json"), "w"), indent=1)


def main():
    os.makedirs(RES, exist_ok=True)
    for stage in sys.argv[1:]:
        if stage == "summary":
            summary()
            continue
        path = os.path.join(RES, stage + ".jsonl")
        with open(path, "w") as f, cf.ThreadPoolExecutor(WORKERS) as ex:
            for r in ex.map(run, cases(stage)):
                f.write(json.dumps(r) + "\n")
                f.flush()


if __name__ == "__main__":
    main()
