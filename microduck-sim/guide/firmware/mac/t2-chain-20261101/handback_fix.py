"""Hand-back repairs on the T2 runs that really hold (holding bit 1, neck bowed like the robot). Mac mini.
Criterion: no fall, the ball held to the end, stand61 stable, smallest post-hand-back peak."""
import concurrent.futures as cf, json, os, statistics as st, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
BASE = ["--model", "asbuilt", "--manifest", "../../../microduck_rl/cmu/model/manifests/plugged.json", "--com-x", "-2.25", "--volt", "7.0", "--drop", "0.04",
        "--wired-guards", "--walk-s", "0", "--walk-at", "1", "--head-pitch", "1.35", "--head-yaw", "0.0", "--sp-at", "4", "--sp-shape", "ball",
        "--sp-cone", "elliptic", "--sp-impratio", "10", "--sp-after", "4", "--sp-pix", "--models", "models-spx-b_1800", "--sp-jaw-current", "150"]
RUNS = [(-0.01, 0.0, 0), (0.0, -0.01, 1), (0.01, 0.0, 1), (0.01, 0.0, 2), (0.03, 0.0, 0), (0.03, 0.0, 1)]
VARS = {"current": [], "bit_off_0.60": ["--sp-bit-off", "0.60"], "bit_off_0.70": ["--sp-bit-off", "0.70"], "blend_1.5": ["--sp-blend", "1.5"],
        "bit_off_0.70_blend_1": ["--sp-bit-off", "0.70", "--sp-blend", "1.0"], "old_rise_0.44": ["--sp-rise-old", "0.44"], "old_rise_0.50": ["--sp-rise-old", "0.50"],
        "old_rise_0.58": ["--sp-rise-old", "0.58"]}


def one(a):
    v, (dx, dy, s) = a
    p = subprocess.run([PY, "brain_sim_check.py"] + BASE + VARS[v] + ["--sp-offset", str(dx), str(dy), "--seed", str(s)], cwd=MAC, capture_output=True, text=True)
    l = p.stdout.strip().splitlines()
    if not (l and l[-1].startswith("{")):
        return dict(v=v, error=(p.stderr or p.stdout)[-300:])
    d = json.loads(l[-1]); S = d["seepick"]; P = S.get("post_handback") or {}
    return dict(v=v, dx=dx, dy=dy, s=s, fell=d.get("fell_at"), guard=(S.get("guard") or {}).get("why"), held_hb=(S.get("at_handback") or {}).get("held"),
                held_end=(S.get("at_end") or {}).get("held"), jumps=d.get("action_jumps"), max_action=d.get("max_action"), **P)


NEW = sys.argv[1:] or list(VARS)
VARS = {k: VARS[k] for k in NEW}
jobs = [(v, r) for v in VARS for r in RUNS]
with cf.ThreadPoolExecutor(7) as ex, open(os.path.join(HERE, "results", "handback_fix.jsonl"), "a") as f:
    rows = list(ex.map(one, jobs))
    for r in rows:
        f.write(json.dumps(r) + "\n")
for v in VARS:
    R = [r for r in rows if r["v"] == v and "error" not in r]
    E = [r for r in rows if r["v"] == v and "error" in r]
    print(v, "n", len(R), "fell", sum(bool(r["fell"]) for r in R), "guard", sum(bool(r["guard"]) for r in R), "held_hb", sum(bool(r["held_hb"]) for r in R), "held_end", sum(bool(r["held_end"]) for r in R),
          "tilt1s", st.median(r["peak_tilt_1s"] for r in R) if R else None, "gyro", st.median(r["peak_gyro"] for r in R) if R else None,
          "stable", [r["stable_after_s"] for r in R], "jumps", st.median(r["jumps"] for r in R) if R else None, E[:1], flush=True)
