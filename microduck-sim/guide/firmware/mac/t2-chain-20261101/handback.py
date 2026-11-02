"""What each pick policy leaves at the hand-back to stand61 and what stand61 does next (as-built sim, Mac mini).
Placement of the 2026-11-01 robot pick: dx +1.3 dy -2.1 cm, real sphere, robot jaw."""
import concurrent.futures as cf, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
BASE = ["--model", "asbuilt", "--manifest", "../../../microduck_rl/cmu/model/manifests/plugged.json", "--com-x", "-2.25", "--volt", "7.0", "--drop", "0.04",
        "--wired-guards", "--walk-s", "0", "--walk-at", "1", "--head-pitch", "1.35", "--head-yaw", "0.0", "--sp-at", "4", "--sp-shape", "ball",
        "--sp-cone", "elliptic", "--sp-impratio", "10", "--sp-half", "0.006", "0.006", "0.006", "--sp-mass", "1.1", "--sp-friction", "0.45",
        "--sp-offset", "0.013", "-0.021", "--sp-after", "4"]
OUT = os.path.join(HERE, "results", "handback")
os.makedirs(OUT, exist_ok=True)


def one(a):
    name, extra, s = a
    tr = os.path.join(OUT, f"{name}_{s}.trace.jsonl")
    p = subprocess.run([PY, "brain_sim_check.py"] + BASE + extra + ["--seed", str(s), "--sp-trace", tr], cwd=MAC, capture_output=True, text=True)
    l = p.stdout.strip().splitlines()
    return dict(name=name, s=s, d=json.loads(l[-1]) if l and l[-1].startswith("{") else None, tail=(p.stderr or p.stdout)[-300:], tr=tr)


jobs = [(n, e, s) for n, e in (("t2", ["--sp-pix", "--models", "models-spx-b_1800"]), ("seepick61", ["--models", "models-t2"])) for s in (0, 1, 2)]
with cf.ThreadPoolExecutor(6) as ex, open(os.path.join(OUT, "summary.jsonl"), "w") as f:
    for r in ex.map(one, jobs):
        d = r["d"]
        if d is None:
            print(r["name"], r["s"], "FAILED", r["tail"]); continue
        S = d["seepick"]
        row = dict(name=r["name"], s=r["s"], fell=d.get("fell_at"), peak_tilt=d.get("peak_tilt_deg"), guard=(S.get("guard") or {}).get("why"),
                   handback=S.get("handback_from_switch_s"), at_handback=S.get("at_handback"), at_end=S.get("at_end"), max_action=d.get("max_action"), jumps=d.get("action_jumps"), max_tilt=d.get("max_tilt"), end_mode=d.get("end_mode"), max_action_pick=S["events"].get("max_action"))
        f.write(json.dumps(row) + "\n")
        print(json.dumps({k:v for k,v in row.items() if k not in ("at_handback","at_end")})[:300], flush=True)
