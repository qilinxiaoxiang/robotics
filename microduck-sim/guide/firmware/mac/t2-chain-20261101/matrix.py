"""Candidates x object x jaw current on the gap study's nine placements, seeds 0-2. Mac mini. Writes results/matrix.jsonl.
Objects: draw = the training 'ball' (an ellipsoid, three radii 5.3-7.2 mm, 0.5-10 g, mu 0.35-1.1);
sphere = the printed ball (radius 6 mm, 1.1 g, mu 0.45)."""
import concurrent.futures as cf, json, os, shutil, subprocess, sys, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
BASE = ["--model", "asbuilt", "--manifest", "../../../microduck_rl/cmu/model/manifests/plugged.json", "--com-x", "-2.25", "--volt", "7.0", "--drop", "0.04",
        "--wired-guards", "--walk-s", "0", "--walk-at", "1", "--head-pitch", "1.35", "--head-yaw", "0.0", "--sp-at", "4", "--sp-shape", "ball",
        "--sp-cone", "elliptic", "--sp-impratio", "10"]
SPHERE = ["--sp-half", "0.006", "0.006", "0.006", "--sp-mass", "1.1", "--sp-friction", "0.45"]
CANDS = ["spx-a_2500", "spx-a_1400", "spx-b_1800", "spx-b_2400"]
OFFS = [(-0.03, 0.0), (-0.01, 0.0), (0.0, -0.03), (0.0, -0.01), (0.0, 0.0), (0.0, 0.01), (0.0, 0.03), (0.01, 0.0), (0.03, 0.0)]


def dirs(c):
    d = os.path.join(MAC, "models-" + c)
    if not os.path.isdir(d):
        shutil.copytree(os.path.join(MAC, "models-t2"), d)
        shutil.copy(os.path.join(HERE, "policies", c + ".onnx"), os.path.join(d, "seepickpix61.onnx"))
    return "models-" + c


def one(a):
    c, obj, ma, (dx, dy), s = a
    pix = [] if c == "seepick61" else ["--sp-pix"]
    cmd = [PY, "brain_sim_check.py"] + BASE + pix + ["--models", "models-t2" if c == "seepick61" else dirs(c)] + (SPHERE if obj == "sphere" else []) + \
        ["--sp-jaw-current", str(ma), "--sp-offset", str(dx), str(dy), "--seed", str(s)]
    for _ in range(3):
        p = subprocess.run(cmd, cwd=MAC, capture_output=True, text=True)
        l = p.stdout.strip().splitlines()
        if l and l[-1].startswith("{"):
            d = json.loads(l[-1]); S = d["seepick"]; e = S["events"]; ca = e.get("close_at") or {}
            return dict(c=c, obj=obj, ma=ma, dx=dx, dy=dy, s=s, train=e.get("held_ticks", 0) >= 20, handback=bool((S.get("at_handback") or {}).get("held")),
                        end=bool((S.get("at_end") or {}).get("held")), pinched=e.get("first_pinched_t"), err=ca.get("pad_xy_err_m"), z=ca.get("pad_z_m"),
                        fell=d["fell_at"], guard=(S.get("guard") or {}).get("why"))
    return dict(c=c, obj=obj, ma=ma, error=(p.stderr or p.stdout)[-300:])


jobs = [(c, o, m, f, s) for c in CANDS + ["seepick61"] for o, m in (("draw", 150), ("sphere", 150), ("sphere", 300), ("sphere", 1470)) for f in OFFS for s in (0, 1, 2)]
for c in CANDS:
    dirs(c)
with cf.ThreadPoolExecutor(7) as ex, open(os.path.join(HERE, "results", "matrix.jsonl"), "w") as f:
    rows = list(ex.map(one, jobs))
    for r in rows:
        f.write(json.dumps(r) + "\n")
for key in dict.fromkeys((r["c"], r["obj"], r["ma"]) for r in rows):
    R = [r for r in rows if (r["c"], r["obj"], r["ma"]) == key and "error" not in r]
    med = lambda k: round(st.median([r[k] for r in R if r[k] is not None]), 4)
    print(*key, "n", len(R), "train", sum(r["train"] for r in R), "handback", sum(r["handback"] for r in R), "end", sum(r["end"] for r in R),
          "pinched", sum(r["pinched"] is not None for r in R), "fell", sum(bool(r["fell"]) for r in R), "err", med("err"), "z", med("z"), flush=True)
