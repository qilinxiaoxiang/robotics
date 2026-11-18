"""Round 2 (2026-11-18): how precisely must the privileged inputs of teacher A-999 be known? Runtime simulation, 20
episodes per cell, seeds as in selection, one job at a time through mini.sh (lock + pre-flight).

  python3 train/ts2_bprec.py [<models dir, default t2a_999>]

Sanity cell: no pack with FLIGHT_PRIV_FIX=loadonly (the constants equal the truth there) must give the baseline 0/20;
the sweep is skipped when it does not. Sweep at full pack, plain walk and COM x +10 mm walk, true values except one
group (flight_eval FLIGHT_PRIV_MOD): payload input x 0.9 / 0.75 / 0.5; trunk COM x input -5 / -10 / +5 mm; the three
velocity inputs zeroed. Result files eval/bp_<dir>_<case>_<tag>.json, summary out/ts2_bprec.json.
"""
import json
import subprocess
import sys
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
models = sys.argv[1] if len(sys.argv) > 1 else "t2a_999"
mini = str(TRAIN / "mini.sh")
MODS = {"kg090": {"kg_scale": 0.9}, "kg075": {"kg_scale": 0.75}, "kg050": {"kg_scale": 0.5},
        "comx-5": {"comx_add": -0.005}, "comx-10": {"comx_add": -0.010}, "comx+5": {"comx_add": 0.005},
        "vel0": {"vel_zero": 1}}
CASES = [("full", "load100"), ("comx", "comx+10")]


def run(cells):
    """cells: [(file stem, env prefix, manifest, extra flags)]"""
    todo = [c for c in cells if not (TRAIN / f"eval/{c[0]}.json").exists()]
    if not todo:
        return
    subprocess.run(["zsh", mini, "push"], check=True, capture_output=True)
    for i in range(0, len(todo), 5):
        cmd = "; ".join(
            f"{env}$PY train/flight_eval.py --models train/ckpt/{models} --manifest train/manifests/flightpack-{man}.json "
            f"--case walk --episodes 20 --workers 8 --extra='{extra}' --out train/eval/{stem}.json > /dev/null "
            f"2> train/eval/{stem}.err; echo done {stem}" for stem, env, man, extra in todo[i:i + 5])
        r = subprocess.run(["zsh", mini, "run", cmd], capture_output=True, text=True)
        print(r.stdout.strip()[-300:].replace("\n", " "), r.stderr.strip()[-300:], flush=True)
        subprocess.run(["zsh", mini, "pull"], check=True, capture_output=True)


def read(stem):
    p = TRAIN / f"eval/{stem}.json"
    if not p.exists():
        return None
    s = json.loads(p.read_text())["summary"]
    return dict(falls_of_20=s["falls"], fall_times=[round(x, 1) for x in s["fall_times"]], speed=s["speed_median_upright"])


out = dict(models=models)
sanity = f"bp_{models}_none_loadonly"
run([(sanity, "FLIGHT_PRIV_FIX=loadonly ", "none", "")])
out["sanity_none_loadonly"] = read(sanity)
print("sanity (no pack, constants = truth):", out["sanity_none_loadonly"], flush=True)
if not out["sanity_none_loadonly"] or out["sanity_none_loadonly"]["falls_of_20"] != 0:
    (TRAIN / "out/ts2_bprec.json").write_text(json.dumps(out, indent=1))
    sys.exit("sanity cell does not reproduce the baseline 0/20: the replacement is wrong, sweep not run")
cells = [(f"bp_{models}_{c}_{t}", f"FLIGHT_PRIV_MOD='{json.dumps(m)}' ", man, "--stand-s 0")
         for t, m in MODS.items() for c, man in CASES]
run(cells)
out["sweep"] = {}
for t in MODS:
    out["sweep"][t] = {c: read(f"bp_{models}_{c}_{t}") for c, _ in CASES}
    print(t, " ; ".join(f"{c} {v['falls_of_20'] if v else 'missing'}/20 "
                        f"(speed {v['speed'] if v else None}, first falls {v['fall_times'][:4] if v else None})"
                        for c, v in out["sweep"][t].items()), flush=True)
(TRAIN / "out/ts2_bprec.json").write_text(json.dumps(out, indent=1))
