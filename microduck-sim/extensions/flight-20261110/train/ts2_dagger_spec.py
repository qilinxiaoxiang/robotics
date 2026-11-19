"""Round 2 DAgger: the held-out evaluation of a student checkpoint on Modal (flight_eval_modal.py), ten cells of 20
episodes with the 0 to 2 s forward speed recorded (FLIGHT_VX02).

  python3 train/ts2_dagger_spec.py <ckpt dir> [seed0]      ->  train/eval/spec_dg_<dir>[_s<seed0>].json
  modal run train/flight_eval_modal.py --spec <that file>
  python3 train/ts2_dagger_spec.py --table <ckpt dir> [seed0] [...]   one summary per dir -> also out/dagger/eval_<dir>[_s<seed0>].json

Cells (names dg_<dir>[_s<seed0>]_<cell>): the seven acceptance cells none, nobatt, full, comx, shove (as ts2_pick.py),
comx_d0, shove_d0 (--drop 0); then comx_d072 (--drop 0.072), comx_landing (released 2.5 to 3.5 cm, tilt up to 5 deg)
and comx_stand (zero command for the whole 20 s). Seeds seed0 .. seed0+19 (0 or 2000: never collected for training).
"""
import json
import sys
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
S0 = ["--stand-s", "0"]
# cell, manifest, case, shove N s, landing, extra
CELLS = [("none", "none", "walk", 0.0, False, []), ("nobatt", "nobatt", "walk", 0.0, False, S0), ("full", "load100", "walk", 0.0, False, S0),
         ("comx", "comx+10", "walk", 0.0, False, S0), ("shove", "nominal", "walk", 0.5, False, S0),
         ("comx_d0", "comx+10", "walk", 0.0, False, S0 + ["--drop", "0"]), ("shove_d0", "nominal", "walk", 0.5, False, S0 + ["--drop", "0"]),
         ("comx_d072", "comx+10", "walk", 0.0, False, S0 + ["--drop", "0.072"]), ("comx_landing", "comx+10", "walk", 0.0, True, S0),
         ("comx_stand", "comx+10", "stand", 0.0, False, S0)]
SEVEN = [c[0] for c in CELLS[:7]]


def stem(d, seed0):
    return f"dg_{d}" + (f"_s{seed0}" if seed0 else "")


def read(name):
    p = TRAIN / f"eval/{name}.json"
    if not p.exists():
        return None
    j = json.loads(p.read_text())
    if j["summary"].get("incomplete"):
        return None
    eps = j["episodes"]
    vx = [e["vx_0_2s"] for e in eps if e.get("vx_0_2s") is not None]
    falls = sorted(e["fell_at"] for e in eps if e["fell_at"] is not None)
    return dict(falls_of_20=len(falls), fall_times=falls, forward_speed_0_2s_mean=round(sum(vx) / len(vx), 4) if vx else None,
                walk_speed_median_upright=j["summary"]["speed_median_upright"], seeds=[eps[0]["seed"], eps[-1]["seed"]])


if sys.argv[1] == "--table":
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        d = args[i]
        seed0 = int(args[i + 1]) if i + 1 < len(args) and args[i + 1].isdigit() else 0
        i += 2 if i + 1 < len(args) and args[i + 1].isdigit() else 1
        cells = {c[0]: read(f"{stem(d, seed0)}_{c[0]}") for c in CELLS}
        f = {k: (v["falls_of_20"] if v else None) for k, v in cells.items()}
        seven = None if any(f[k] is None for k in SEVEN) else sum(f[k] for k in SEVEN)
        out = dict(ckpt=d, seed0=seed0, falls=f, seven_cells_total=seven,
                   creep_comx_0_2s=cells["comx"] and cells["comx"]["forward_speed_0_2s_mean"],
                   creep_comx_stand_0_2s=cells["comx_stand"] and cells["comx_stand"]["forward_speed_0_2s_mean"], cells=cells)
        (TRAIN / "out/dagger").mkdir(parents=True, exist_ok=True)
        (TRAIN / f"out/dagger/eval_{d}{f'_s{seed0}' if seed0 else ''}.json").write_text(json.dumps(out, indent=1))
        print(d, f"seed0 {seed0}", f, "seven", seven, "creep comx", out["creep_comx_0_2s"], "stand", out["creep_comx_stand_0_2s"])
else:
    d = sys.argv[1]
    seed0 = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    assert (TRAIN / f"ckpt/{d}/walk61.onnx").exists(), d
    evals = [dict(name=f"{stem(d, seed0)}_{name}", models=f"ckpt/{d}", manifest=f"manifests/flightpack-{man}.json", case=case, episodes=20,
                  seed0=seed0, shove_ns=sh, shove_at=8.0, landing=landing, extra=extra, env={"FLIGHT_VX02": "1"})
             for name, man, case, sh, landing, extra in CELLS if not (TRAIN / f"eval/{stem(d, seed0)}_{name}.json").exists()]
    out = TRAIN / f"eval/spec_{stem(d, seed0)}.json"
    out.write_text(json.dumps(dict(evals=evals), indent=1))
    print(f"{out}: {len(evals)} evals, {len(evals) * 20} episodes")
