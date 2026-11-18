"""Round 2: pick a checkpoint on runtime-simulation falls (TEACHER-STUDENT-PLAN.md "Round 2", step 4).

  python3 train/ts2_pick.py <models dir under train/ckpt> [<models dir> ...]

Each dir holds walk61.onnx + stand61.onnx (the same file twice). A privileged teacher (obs [1, 68]) is fed its seven
privileged inputs from the simulator by flight_eval.py (_PrivSession); a one-frame or recurrent policy runs as always.
Five walk cases per dir in the runtime simulation on the Mac mini (flight_eval.py: 20 s, vx 0.25 from 2 s for 15 s,
seeds 0..19, --volt 7.6 --drop 0.036, sensor and action delay 1 tick each), one chunk per dir, under 10 minutes:
  none      no pack, started as today (0.3 s open-loop stand)
  nobatt    batteries out               full      full pack (load100)
  comx      full pack, COM x +10 mm     shove     full pack, 0.5 N s shove at 8 s
Result files eval/pk_<dir>_<case>.json (existing files are reused). Printed per dir: falls of 20 per case, the sum, the
median upright speed and leg torque p99; for a teacher also its first privileged inputs.
"""
import json
import subprocess
import sys
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
S0 = "--stand-s 0"
CASES = [("none", "none", "", ""), ("nobatt", "nobatt", S0, ""), ("full", "load100", S0, ""),
         ("comx", "comx+10", S0, ""), ("shove", "nominal", S0, "--shove-ns 0.5 --shove-at 8")]
mini = str(TRAIN / "mini.sh")
pushed = False
rows = {}
for models in sys.argv[1:]:
    todo = [c for c in CASES if not (TRAIN / f"eval/pk_{models}_{c[0]}.json").exists()]
    if todo:
        if not pushed:
            subprocess.run(["zsh", mini, "push"], check=True, capture_output=True)
            pushed = True
        cmd = "; ".join(
            f"$PY train/flight_eval.py --models train/ckpt/{models} --manifest train/manifests/flightpack-{man}.json "
            f"--case walk --episodes 20 --workers 8 {flags} --extra='{extra}' "
            f"--out train/eval/pk_{models}_{name}.json > /dev/null 2> train/eval/pk_{models}_{name}.err; echo done {name}"
            for name, man, extra, flags in todo)
        r = subprocess.run(["zsh", mini, "run", cmd], capture_output=True, text=True)
        print(r.stdout.replace("busy\n", "").strip()[-200:].replace("\n", " "), r.stderr.strip()[-300:], flush=True)
        subprocess.run(["zsh", mini, "pull"], check=True, capture_output=True)
    falls, parts = 0, []
    for name, *_ in CASES:
        p = TRAIN / f"eval/pk_{models}_{name}.json"
        if not p.exists():
            parts.append(f"{name} missing")
            falls = None
            continue
        j = json.loads(p.read_text())
        s, eps = j["summary"], j["episodes"]
        p99 = sorted(e["leg_force_p99_nm"] for e in eps if e.get("leg_force_p99_nm") is not None)
        parts.append(f"{name} {s['falls']}/20 (speed {s['speed_median_upright']}, p99 {round(p99[len(p99) // 2], 3) if p99 else None})")
        if falls is not None:
            falls += s["falls"]
        if name == "full" and eps[0].get("priv_first"):
            parts.append(f"priv {eps[0]['priv_first'][0]}")
    rows[models] = falls
    print(f"{models}: total falls {falls} of 100; " + "; ".join(parts), flush=True)
(TRAIN / "out/ts2_pick.json").write_text(json.dumps(dict(
    cases=[c[0] for c in CASES], total_falls_of_100=dict(
        json.loads((TRAIN / "out/ts2_pick.json").read_text())["total_falls_of_100"] if (TRAIN / "out/ts2_pick.json").exists() else {},
        **rows)), indent=1))
