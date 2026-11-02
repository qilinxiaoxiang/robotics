"""Does the holding bit (body slot 58) make T2 raise the neck? The same placement with the bit from the runtime rule and forced on."""
import concurrent.futures as cf, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
BASE = ["--model", "asbuilt", "--manifest", "../../../microduck_rl/cmu/model/manifests/plugged.json", "--com-x", "-2.25", "--volt", "7.0", "--drop", "0.04",
        "--wired-guards", "--walk-s", "0", "--walk-at", "1", "--head-pitch", "1.35", "--head-yaw", "0.0", "--sp-at", "4", "--sp-shape", "ball",
        "--sp-cone", "elliptic", "--sp-impratio", "10", "--sp-offset", "0.0", "0.0", "--sp-after", "4", "--seed", "0"]
OUT = os.path.join(HERE, "results", "holdbit")
os.makedirs(OUT, exist_ok=True)
CASES = {"t2_stopped_draw": ["--sp-pix", "--models", "models-spx-b_1800", "--sp-holding", "stopped"],
         "t2_runtime_draw": ["--sp-pix", "--models", "models-spx-b_1800", "--sp-holding", "runtime"],
         "old_stopped_draw": ["--models", "models-t2", "--sp-holding", "stopped"],
         "old_runtime_draw": ["--models", "models-t2", "--sp-holding", "runtime"]}


def one(kv):
    n, e = kv
    tr = os.path.join(OUT, n + ".jsonl")
    p = subprocess.run([PY, "brain_sim_check.py"] + BASE + e + ["--sp-trace", tr], cwd=MAC, capture_output=True, text=True)
    l = p.stdout.strip().splitlines()
    d = json.loads(l[-1]) if l and l[-1].startswith("{") else {}
    S = d.get("seepick", {})
    rows = [json.loads(x) for x in open(tr)]
    last = rows[-1] if rows else {}
    neck = [(r["phase"], round(r["q"][5], 2), round(r["q"][6], 2)) for r in rows[::30]]
    return dict(n=n, fell=d.get("fell_at"), jumps=d.get("action_jumps"), max_action=d.get("max_action"), held_handback=(S.get("at_handback") or {}).get("held"),
                bit=(S.get("at_handback") or {}).get("holding_bit"), held_end=(S.get("at_end") or {}).get("held"),
                last_neck=round(last["q"][5], 2) if last else None, last_head=round(last["q"][6], 2) if last else None, neck=neck, err=(p.stderr or "")[-200:] if not d else "")


with cf.ThreadPoolExecutor(4) as ex, open(os.path.join(OUT, "summary.jsonl"), "w") as f:
    for r in ex.map(one, CASES.items()):
        f.write(json.dumps(r) + "\n")
        print(json.dumps(r)[:600], flush=True)
