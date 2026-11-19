"""Round 2 warm-up rule (2026-11-18), simulation only: a plain 61-input policy drives the first N control ticks at zero
command while the recurrent student sees every observation and builds its state, then the student drives
(flight_eval FLIGHT_WARMUP="<onnx>:<N>", counters warmup_driver_ticks / student_ticks; FLIGHT_VX02=1 records the
trunk's forward speed over the first 2 s). Runtime simulation on the Mac mini, one job at a time through mini.sh
(lock + pre-flight), 20 episodes, seeds 0..19, 8 workers.

  python3 train/ts2_warmup.py drivers          the drivers alone at comx+10 and full load (do they stand for 2 s?)
  python3 train/ts2_warmup.py run <driver> <student> <N>     the nine cells of one configuration
  <venv python> train/ts2_warmup.py summary    -> out/ts2_warmup.json

Drivers: ts_start = ckpt/ts_start/stand61.onnx (the one-frame start-point policy, same file as uni_a);
overlay = ckpt/overlay_models/stand61.onnx (copy of microduck_rl/cmu/whole/runtime-overlay/models/stand61.onnx).
The walk command starts at 2.0 s in every episode: with N = 100 the warm-up ends there, with N = 50 the student stands
at zero command for the second second. The cell "none" keeps ts2_pick's 0.3 s open-loop stand, so the driver has the
ticks 16 to N.
"""
import json
import subprocess
import sys
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
S0 = "--stand-s 0"
DRIVERS = {"ts_start": "train/ckpt/ts_start/stand61.onnx", "overlay": "train/ckpt/overlay_models/stand61.onnx"}
# (cell, manifest, extra flags, flight_eval flags); the first five as ts2_pick.py
CELLS = [("none", "none", "", ""), ("nobatt", "nobatt", S0, ""), ("full", "load100", S0, ""), ("comx", "comx+10", S0, ""),
         ("shove", "nominal", S0, "--shove-ns 0.5 --shove-at 8"),
         ("comx_d0", "comx+10", S0 + " --drop 0", ""), ("shove_d0", "nominal", S0 + " --drop 0", "--shove-ns 0.5 --shove-at 8"),
         ("comx_d072", "comx+10", S0 + " --drop 0.072", ""), ("comx_landing", "comx+10", S0, "--landing")]
CONFIGS = [("ts_start", "s2g_200", 100), ("ts_start", "s2g_140", 100), ("ts_start", "s2g_200", 50),
           ("overlay", "s2g_200", 100), ("overlay", "s2g_140", 100), ("overlay", "s2g_200", 50)]
# the same cells without the warm-up, where a record exists (pk_: the main session's Modal selection runs)
COLD = {"none": "pk_{s}_none", "nobatt": "pk_{s}_nobatt", "full": "pk_{s}_full", "comx": "pk_{s}_comx", "shove": "pk_{s}_shove",
        "comx_d072": "dr_{s}_comx_d072", "comx_landing": "cz_{s}_landing", "comx_d0": "cz_{s}_shadow_nodrop"}


def run(cmds):
    mini = str(TRAIN / "mini.sh")
    subprocess.run(["zsh", mini, "push"], check=True, capture_output=True)
    r = subprocess.run(["zsh", mini, "run", "; ".join(cmds)], capture_output=True, text=True)
    print(r.stdout.strip()[-500:].replace("\n", " "), r.stderr.strip()[-300:], flush=True)
    subprocess.run(["zsh", mini, "pull"], check=True, capture_output=True)


def cmd(env, models, man, case_flags, extra, stem):
    return (f"{env} $PY train/flight_eval.py --models train/ckpt/{models} --manifest train/manifests/flightpack-{man}.json "
            f"--case walk {case_flags} --episodes 20 --workers 8 --extra='{extra}' --out train/eval/{stem}.json > /dev/null "
            f"2> train/eval/{stem}.err; echo done {stem}")


def read(stem):
    p = TRAIN / f"eval/{stem}.json"
    if not p.exists():
        return None
    j = json.loads(p.read_text())
    eps, s = j["episodes"], j["summary"]
    stat = {}
    for e in eps:
        for k, v in (e.get("diag_stat") or {}).items():
            stat[k] = stat.get(k, 0) + v
    vx = [e["vx_0_2s"] for e in eps if e.get("vx_0_2s") is not None]
    falls = sorted(e["fell_at"] for e in eps if e["fell_at"] is not None)
    return dict(file=f"eval/{stem}.json", manifest=s["manifest"], falls_of_20=len(falls), fall_times=[round(x, 2) for x in falls],
                falls_before_2s=sum(1 for x in falls if x < 2.0),
                forward_speed_0_2s_mean=round(sum(vx) / len(vx), 4) if vx else None,
                forward_speed_0_2s_max_episode=round(max(vx), 4) if vx else None,
                walk_speed_median_upright=s["speed_median_upright"], counters_sum_over_episodes=stat or None)


def main():
    what = sys.argv[1]
    if what == "drivers":
        todo = [(d, m) for d in ("ts_start", "overlay_models") for m in ("comx+10", "load100")
                if not (TRAIN / f"eval/wu_driver_{d}_{m}.json").exists()]
        if todo:
            run([cmd("FLIGHT_VX02=1", d, m, "", S0, f"wu_driver_{d}_{m}") for d, m in todo])
        for d in ("ts_start", "overlay_models"):
            for m in ("comx+10", "load100"):
                print(d, m, read(f"wu_driver_{d}_{m}"), flush=True)
    elif what == "run":
        drv, stu, n = sys.argv[2], sys.argv[3], int(sys.argv[4])
        todo = [c for c in CELLS if not (TRAIN / f"eval/wu_{drv}_{stu}_n{n}_{c[0]}.json").exists()]
        if todo:
            run([cmd(f"FLIGHT_VX02=1 FLIGHT_WARMUP={DRIVERS[drv]}:{n}", stu, man, flags, extra, f"wu_{drv}_{stu}_n{n}_{name}")
                 for name, man, extra, flags in todo])
        for name, *_ in CELLS:
            r = read(f"wu_{drv}_{stu}_n{n}_{name}")
            print(drv, stu, n, name, None if r is None else {k: r[k] for k in ("falls_of_20", "fall_times", "forward_speed_0_2s_mean",
                                                                              "counters_sum_over_episodes")}, flush=True)
    else:
        out = dict(drivers_alone={f"{d}_{m}": read(f"wu_driver_{d}_{m}") for d in ("ts_start", "overlay_models") for m in ("comx+10", "load100")},
                   warmup={}, without_warmup={})
        for drv, stu, n in CONFIGS:
            cells = {name: read(f"wu_{drv}_{stu}_n{n}_{name}") for name, *_ in CELLS}
            if any(cells.values()):
                tot = [c["falls_of_20"] for c in cells.values() if c]
                out["warmup"][f"{drv}_{stu}_n{n}"] = dict(driver=DRIVERS[drv], student=stu, warmup_ticks=n, cells=cells, cells_run=len(tot),
                                                          falls_total=sum(tot), episodes_total=20 * len(tot))
        for stu in ("s2g_200", "s2g_140"):
            out["without_warmup"][stu] = {name: read(st.format(s=stu)) for name, st in COLD.items()}
        (TRAIN / "out/ts2_warmup.json").write_text(json.dumps(out, indent=1))
        for k, v in out["warmup"].items():
            print(k, v["falls_total"], "of", v["episodes_total"], {n: (c["falls_of_20"] if c else None) for n, c in v["cells"].items()})
        for s, v in out["without_warmup"].items():
            print("cold", s, {n: (c["falls_of_20"] if c else None) for n, c in v.items()})


if __name__ == "__main__":
    main()
