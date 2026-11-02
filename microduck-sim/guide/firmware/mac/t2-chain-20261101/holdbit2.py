"""T2 in runs that really pinch, so the holding bit goes to 1: does the neck stay bowed as on the robot?"""
import concurrent.futures as cf, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
BASE = ["--model", "asbuilt", "--manifest", "../../../microduck_rl/cmu/model/manifests/plugged.json", "--com-x", "-2.25", "--volt", "7.0", "--drop", "0.04",
        "--wired-guards", "--walk-s", "0", "--walk-at", "1", "--head-pitch", "1.35", "--head-yaw", "0.0", "--sp-at", "4", "--sp-shape", "ball",
        "--sp-cone", "elliptic", "--sp-impratio", "10", "--sp-after", "4", "--sp-pix", "--models", "models-spx-b_1800", "--sp-jaw-current", "150"]
rows = [json.loads(l) for l in open(os.path.join(HERE, "results", "matrix.jsonl"))]
sel = [r for r in rows if r["c"] == "spx-b_1800" and r["train"] and r["handback"] and r["ma"] == 150]
SPHERE = ["--sp-half", "0.006", "0.006", "0.006", "--sp-mass", "1.1", "--sp-friction", "0.45"]
OUT = os.path.join(HERE, "results", "holdbit2")
os.makedirs(OUT, exist_ok=True)


def one(r):
    n = f"{r['obj']}_{r['dx']}_{r['dy']}_{r['s']}"
    tr = os.path.join(OUT, n + ".jsonl")
    cmd = [PY, "brain_sim_check.py"] + BASE + (SPHERE if r["obj"] == "sphere" else []) + ["--sp-offset", str(r["dx"]), str(r["dy"]), "--seed", str(r["s"]), "--sp-trace", tr]
    p = subprocess.run(cmd, cwd=MAC, capture_output=True, text=True)
    l = p.stdout.strip().splitlines()
    d = json.loads(l[-1]) if l and l[-1].startswith("{") else {}
    S = d.get("seepick", {})
    tr_rows = [json.loads(x) for x in open(tr)]
    H = S.get("at_handback") or {}
    return dict(n=n, fell=d.get("fell_at"), max_tilt=d.get("max_tilt"), jumps=d.get("action_jumps"), held=H.get("held"), bit=H.get("holding_bit"), jaw=H.get("jaw_opening_deg"),
                held_end=(S.get("at_end") or {}).get("held"), last_tilt=tr_rows[-1]["tilt_deg"] if tr_rows else None,
                neck=[(r2["phase"], round(r2["q"][5], 2), round(r2["q"][6], 2), round(r2["action"][5], 2)) for r2 in tr_rows[60::30]])


with cf.ThreadPoolExecutor(7) as ex, open(os.path.join(OUT, "summary.jsonl"), "w") as f:
    for r in ex.map(one, sel):
        f.write(json.dumps(r) + "\n")
        print(json.dumps(r)[:420], flush=True)
