"""spx-b_1800 with the real sphere at 150 mA on the placements the robot actually reaches: dx +1..+6 cm, dy -4..+2 cm, seeds 0-2.
Decides the T2 pick window (seepick.PICK_WIN came from seepick61 robot picks). Mac mini. Writes results/window_sweep.jsonl."""
import concurrent.futures as cf, json, os, subprocess, collections
HERE = os.path.dirname(os.path.abspath(__file__)); MAC = os.path.dirname(HERE)
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
BASE = ["--model", "asbuilt", "--manifest", "../../../microduck_rl/cmu/model/manifests/plugged.json", "--com-x", "-2.25", "--volt", "7.0", "--drop", "0.04",
        "--wired-guards", "--walk-s", "0", "--walk-at", "1", "--head-pitch", "1.35", "--head-yaw", "0.0", "--sp-at", "4", "--sp-shape", "ball",
        "--sp-cone", "elliptic", "--sp-impratio", "10", "--sp-half", "0.006", "0.006", "0.006", "--sp-mass", "1.1", "--sp-friction", "0.45",
        "--sp-pix", "--models", "models-spx-b_1800", "--sp-jaw-current", "150"]


def one(a):
    dx, dy, s = a
    cmd = [PY, "brain_sim_check.py"] + BASE + ["--sp-offset", str(dx / 100), str(dy / 100), "--seed", str(s)]
    p = subprocess.run(cmd, cwd=MAC, capture_output=True, text=True)
    l = p.stdout.strip().splitlines()
    if not (l and l[-1].startswith("{")):
        return dict(dx=dx, dy=dy, s=s, error=(p.stderr or p.stdout)[-300:])
    d = json.loads(l[-1]); S = d["seepick"]; e = S["events"]; ca = e.get("close_at") or {}
    return dict(dx=dx, dy=dy, s=s, train=e.get("held_ticks", 0) >= 20, handback=bool((S.get("at_handback") or {}).get("held")),
                end=bool((S.get("at_end") or {}).get("held")), pinched=e.get("first_pinched_t"), err=ca.get("pad_xy_err_m"), fell=d["fell_at"])


jobs = [(dx, dy, s) for dx in (1, 2, 3, 4, 5, 6) for dy in (-4, -2, 0, 2) for s in (0, 1, 2)]
with cf.ThreadPoolExecutor(7) as ex, open(os.path.join(HERE, "results", "window_sweep.jsonl"), "w") as f:
    rows = []
    for r in ex.map(one, jobs):
        rows.append(r); f.write(json.dumps(r) + "\n"); f.flush()
b = collections.defaultdict(lambda: [0, 0, 0, 0])
for r in rows:
    v = b[(r["dx"], r["dy"])]; v[0] += 1
    if "error" not in r: v[1] += r["train"]; v[2] += r["handback"]; v[3] += bool(r["fell"])
for k in sorted(b): print("dx %+d dy %+d n %d train %d handback %d fell %d" % (*k, *b[k]), flush=True)
