"""Separate the harness from the policy: nine +-1 cm placements, seeds 0-2, one knob per variant. Mac mini."""
import concurrent.futures as cf, json, os, subprocess, sys
MAC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
BASE = ["--model", "asbuilt", "--manifest", "../../../microduck_rl/cmu/model/manifests/plugged.json", "--com-x", "-2.25", "--volt", "7.0",
        "--drop", "0.04", "--wired-guards", "--walk-s", "0", "--walk-at", "1", "--sp-at", "4", "--sp-shape", "ball",
        "--sp-half", "0.006", "0.006", "0.006", "--sp-mass", "1.1", "--sp-cone", "elliptic", "--sp-impratio", "10", "--models", "models-t2"]
AIM = ["--head-pitch", "1.35", "--head-yaw", "0.0"]
GAP = ["--model", "asbuilt", "--manifest", "../../../microduck_rl/cmu/model/manifests/plugged.json", "--com-x", "-2.25", "--volt", "7.0",
       "--drop", "0.04", "--wired-guards", "--walk-s", "0", "--walk-at", "1", "--sp-at", "4", "--sp-shape", "ball", "--sp-cone", "elliptic", "--sp-impratio", "10", "--models", "models-t2"]
GAPV = {"old_gap": GAP, "t2_gap_aim": GAP + ["--sp-pix"] + AIM, "t2_gap_aim_tjaw": GAP + ["--sp-pix", "--sp-jaw-current", "1470", "--sp-jaw-kp", "400"] + AIM}
VARIANTS = {"old_noaim": [], "old_aim": AIM, "t2_noaim": ["--sp-pix"], "t2_aim": ["--sp-pix"] + AIM,
            "t2_aim_nodrop": ["--sp-pix", "--sp-camera-drop", "0", "--sp-camera-delay", "0.1", "--sp-no-stalls"] + AIM}
def one(a):
    v, dx, dy, s = a
    cmd = [PY, "brain_sim_check.py"] + (GAPV[v] if v in GAPV else BASE + VARIANTS[v]) + ["--sp-offset", str(dx), str(dy), "--seed", str(s)]
    for _ in range(3):
        p = subprocess.run(cmd, cwd=MAC, capture_output=True, text=True)
        l = p.stdout.strip().splitlines()
        if l and l[-1].startswith("{"):
            d = json.loads(l[-1]); e = d["seepick"]["events"]; c = e.get("close_at") or {}
            return dict(v=v, dx=dx, dy=dy, s=s, train=e.get("held_ticks", 0) >= 20, pinched=e.get("first_pinched_t"), err=c.get("pad_xy_err_m"),
                        z=c.get("pad_z_m"), jaw=c.get("jaw_measured_deg"), tilt=round(e["max_tilt"], 1), floorN=e["beak_floor_force_max_n"], clamps=sum((e.get("goal_clamped_ticks") or {}).values()),
                        fell=d["fell_at"], cwin=(e.get("close_window") or {}).get("rel_pad_mm"), maxa=e["max_action"])
    return dict(v=v, error=p.stderr[-300:])
jobs = [(v, dx, dy, s) for v in (sys.argv[1:] or VARIANTS) for dx in ((-0.03, 0, 0.03) if v in GAPV else (-0.01, 0, 0.01)) for dy in ((-0.03, 0, 0.03) if v in GAPV else (-0.01, 0, 0.01)) for s in (0, 1, 2)]
with cf.ThreadPoolExecutor(6) as ex, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "diag.jsonl"), "w") as f:
    rows = list(ex.map(one, jobs))
    for r in rows: f.write(json.dumps(r) + "\n")
import statistics as st
for v in dict.fromkeys(r["v"] for r in rows):
    R = [r for r in rows if r["v"] == v and "error" not in r]
    med = lambda k: round(st.median([r[k] for r in R if r[k] is not None]), 4) if any(r[k] is not None for r in R) else None
    print(v, "n", len(R), "train", sum(r["train"] for r in R), "pinched", sum(r["pinched"] is not None for r in R), "fell", sum(bool(r["fell"]) for r in R),
          "err", med("err"), "z", med("z"), "jaw", med("jaw"), "tilt", med("tilt"), "floorN", med("floorN"), "clamps", med("clamps"), "maxa", med("maxa"))
