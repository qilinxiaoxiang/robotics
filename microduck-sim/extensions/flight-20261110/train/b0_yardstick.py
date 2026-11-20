"""Stage B0 of ../TRAIN-CONTRACT.json (2026-11-20): is any simulation condition a yardstick the robot agrees with?

The robot has already ranked five policies without the jet pack (../../../CURRENT-STATE.json walking_policy,
walking_stability): the deployed set works (walk61 walks, stand61 stands); ft3 it999 fell while walking at 2.5 to 4 s
(2026-10-18), t1 it800 fell while walking at 3.4 s (2026-10-30), s2r6_4 was stopped by the tilt guard 4.4 s after
entering zero-command walk mode (2026-11-19). A condition is a yardstick only if it puts all five on the robot's side.

  $PY train/b0_yardstick.py [workers=7] [seeds=60] [seed0=1000] [out=yardstick_b0] [only=<substring>]   (Mac mini only)

Policies (no pack, manifests/flightpack-none.json), each with the files that ran on the robot:
  deployed  runtime-overlay/models (walk61 in the walk slot, stand61 at zero command)          stand, walk
  s2r6_4    ckpt/s2r6_4 (the recurrent student in both slots)                                   stand, walk
  ft3       runtime-overlay/models-ft3-it999 (walk slot ft3 it999; stand slot = deployed)       walk
  t1        ckpt/ref_t1 (walk slot t1 it800; stand slot = deployed)                             walk
Conditions (candidates named before the run):
  nominal   the simulation as it is (walk mode gain 200, the robot's own value)
  gain400   --kp-rl 400; chosen on 2026-11-19 from walk61 and s2r6_4 only, so ft3, t1 and stand61 test it
  jitter    --bam-friction-scale 1.4 with FLIGHT_GYRO_NOISE_DQ=0.25 (the 2026-10-30 jitter-matched condition)
Episode as the gates: stand mode to 2.0 s, the case's command (0 or 0.25 m/s) to 17.0 s, zero command to 20.0 s.
Falls are counted inside the robot-tested window: the first 4 s of a walk (fell_at <= 6.0), the first 10 s of standing
at zero command (fell_at <= 12.0). Jumps = tick-to-tick action jumps over 0.5 rad per 10 s of upright time.

Rule fixed before the run (contract stage B0, check 1). In one condition all of this must hold:
  - deployed walk and deployed stand: at most 6 falls of 60 in the window;
  - ft3 walk, t1 walk, s2r6_4 stand each fail: at least 12 more window falls of 60 than the deployed set in the same
    cell, or median jumps above max(1.5 x deployed, deployed + 2).
Spread (check 2): window falls per block of 10 seeds and the Wilson 95 % interval of the 60.
Writes train/out/<out>/<cell>.json and summary.json after every cell; heartbeat train/logs/b0_<out>_heartbeat.txt
(last line DONE or FAILED). Nothing is trained.
"""
import hashlib
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
opts = dict(a.split("=", 1) for a in sys.argv[1:])
SEEDS, SEED0, WORKERS = int(opts.get("seeds", 60)), int(opts.get("seed0", 1000)), min(int(opts.get("workers", 7)), 8)
NAME = opts.get("out", "yardstick_b0")
OUT, HB = HERE / "out" / NAME, HERE / "logs" / f"b0_{NAME}_heartbeat.txt"
OVERLAY = (HERE / "../../../microduck_rl/cmu/whole/runtime-overlay").resolve()
NONE = str(HERE / "manifests/flightpack-none.json")
POL = {"deployed": (str(OVERLAY / "models"), ("stand", "walk")),
       "s2r6_4": (str(HERE / "ckpt/s2r6_4"), ("stand", "walk")),
       "ft3": (str(OVERLAY / "models-ft3-it999"), ("walk",)),
       "t1": (str(HERE / "ckpt/ref_t1"), ("walk",))}
COND = {"nominal": ([], {}),
        "gain400": (["--kp-rl", "400"], {}),
        "jitter": (["--bam-friction-scale", "1.4"], {"FLIGHT_GYRO_NOISE_DQ": "0.25"})}
COND_ENV = ("FLIGHT_GYRO_NOISE_DQ",)
TUNED_ON = {"nominal": [], "gain400": ["walk61", "s2r6_4"],
            "jitter": ["walk61 robot logs (guide/firmware/mac/jitter-20261018/README.md)"]}
WINDOW = {"walk": 2.0 + 4.0, "stand": 2.0 + 10.0}
BAD = (("ft3", "walk"), ("t1", "walk"), ("s2r6_4", "stand"))  # the mode in which the robot dropped each one
GOOD_MAX, GAP_MIN, BLOCK = 6, 12, 10


def hb(msg):
    HB.parent.mkdir(parents=True, exist_ok=True)
    with open(HB, "a") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%S ") + msg + "\n")


def one(job):
    label, models, case, extra, env, seed = job
    os.environ.pop("FLIGHT_THRUST", None)
    for k in COND_ENV:
        if k in env:
            os.environ[k] = env[k]
        else:
            os.environ.pop(k, None)
    import flight_eval as fe
    r = fe.episode((models, NONE, case, seed, 0.0, 8.0, False, extra))
    return label, {k: r.get(k) for k in ("seed", "fell_at", "fall_dir", "max_tilt", "speed", "action_jumps")}


def cells():
    c = {}
    for cond, (extra, env) in COND.items():
        for pol, (models, cases) in POL.items():
            for case in cases:
                label = f"{pol}_{cond}_{case}"
                if "only" not in opts or opts["only"] in label:
                    c[label] = (models, case, extra, env)
    return c


def wilson(k, n):
    z = 1.96
    p = k / n
    mid, half = (p + z * z / (2 * n)) / (1 + z * z / n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, mid - half), 3), round(min(1.0, mid + half), 3)]


def summarise(label, eps):
    case = label.rsplit("_", 1)[1]
    eps = sorted(eps, key=lambda e: e["seed"])
    falls = sorted(e["fell_at"] for e in eps if e["fell_at"] is not None)
    inwin = [e["fell_at"] is not None and e["fell_at"] <= WINDOW[case] for e in eps]
    per = sorted(round(e["action_jumps"] / max(e["fell_at"] if e["fell_at"] is not None else 20.0, 0.5) * 10, 1) for e in eps)
    sp = [e["speed"] for e in eps if e["speed"] is not None and e["fell_at"] is None]
    blocks = [sum(inwin[i:i + BLOCK]) for i in range(0, len(inwin), BLOCK)]
    return dict(cell=label, seeds=len(eps), seed0=eps[0]["seed"], window_s=WINDOW[case], falls_in_window=sum(inwin),
                falls_whole_episode=len(falls), fall_times=falls, falls_in_window_per_block_of_10=blocks,
                falls_in_window_wilson95=wilson(sum(inwin), len(eps)), jumps_per_10s_median=per[len(per) // 2],
                jumps_per_10s_quartiles=[per[len(per) // 4], per[(3 * len(per)) // 4]],
                speed_mean_upright=round(sum(sp) / len(sp), 4) if sp else None,
                max_tilt=max((e["max_tilt"] for e in eps if e["max_tilt"] is not None), default=None))


def verdict(summ):
    out = {}
    for cond in COND:
        need = [f"deployed_{cond}_walk", f"deployed_{cond}_stand"] + [f"{p}_{cond}_{c}" for p, c in BAD]
        if any(n not in summ for n in need):
            out[cond] = dict(complete=False)
            continue
        good = {c: summ[f"deployed_{cond}_{c}"]["falls_in_window"] for c in ("walk", "stand")}
        lines = {}
        for pol, case in BAD:
            s, ref = summ[f"{pol}_{cond}_{case}"], summ[f"deployed_{cond}_{case}"]
            lim = max(1.5 * ref["jumps_per_10s_median"], ref["jumps_per_10s_median"] + 2)
            by_falls = s["falls_in_window"] - ref["falls_in_window"] >= GAP_MIN
            by_jumps = s["jumps_per_10s_median"] > lim
            lines[pol] = dict(case=case, falls_in_window=s["falls_in_window"], deployed_falls_in_window=ref["falls_in_window"],
                              jumps_median=s["jumps_per_10s_median"], jumps_limit=round(lim, 2), fails_by_falls=by_falls,
                              fails_by_jumps=by_jumps, on_robot_side=by_falls or by_jumps)
        good_ok = all(v <= GOOD_MAX for v in good.values())
        out[cond] = dict(complete=True, tuned_on=TUNED_ON[cond], deployed_falls_in_window=good, deployed_ok=good_ok, bad=lines,
                         separates_all_five=good_ok and all(v["on_robot_side"] for v in lines.values()))
    return out


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    C, summ = cells(), {}
    for label in list(C):  # resume: a cell whose file is complete is kept
        try:
            old = json.loads((OUT / f"{label}.json").read_text())
            if len(old["episodes"]) == SEEDS and old["episodes"][0]["seed"] == SEED0:
                summ[label] = old["summary"]
                del C[label]
        except (OSError, ValueError, KeyError, IndexError):
            pass
    files = {p: {f: sha(Path(m) / f) for f in ("walk61.onnx", "stand61.onnx")} for p, (m, _) in POL.items()}
    hb(f"START pid {os.getpid()}: {len(C)} cells x {SEEDS} seeds from {SEED0} ({len(summ)} kept from files), {WORKERS} workers; "
       f"model files {json.dumps(files)}")
    jobs = [(label,) + spec + (s,) for label, spec in C.items() for s in range(SEED0, SEED0 + SEEDS)]
    got = {k: [] for k in C}

    def write():
        (OUT / "summary.json").write_text(json.dumps(dict(
            stage="B0", rule=dict(good_max_falls_in_window=GOOD_MAX, bad_min_extra_falls=GAP_MIN, windows_s=WINDOW,
                                  jumps_limit="max(1.5 x deployed, deployed + 2)"),
            model_files_sha256_16=files, conditions={k: dict(flags=v[0], env=v[1]) for k, v in COND.items()},
            cells=summ, verdict=verdict(summ)), indent=1, default=str))

    with ProcessPoolExecutor(WORKERS) as ex:
        for label, r in ex.map(one, jobs):
            got[label].append(r)
            if len(got[label]) < SEEDS:
                continue
            s = summarise(label, got[label])
            summ[label] = s
            (OUT / f"{label}.json").write_text(json.dumps(dict(summary=s, episodes=got[label]), indent=1, default=str))
            write()
            hb(f"{label}: window falls {s['falls_in_window']} of {SEEDS} (blocks of 10: {s['falls_in_window_per_block_of_10']}, "
               f"95 % {s['falls_in_window_wilson95']}); whole episode {s['falls_whole_episode']}; jumps/10 s median "
               f"{s['jumps_per_10s_median']} quartiles {s['jumps_per_10s_quartiles']}; speed {s['speed_mean_upright']}")
    write()
    for cond, v in verdict(summ).items():
        if not v.get("complete"):
            hb(f"VERDICT {cond}: incomplete")
            continue
        hb(f"VERDICT {cond}: separates all five {v['separates_all_five']}; deployed window falls {v['deployed_falls_in_window']}; "
           + "; ".join(f"{p} {b['case']} falls {b['falls_in_window']} jumps {b['jumps_median']} (limit {b['jumps_limit']}) "
                       f"on robot side {b['on_robot_side']}" for p, b in v["bad"].items()))
    hb("DONE")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        hb(f"FAILED {type(e).__name__}: {e}")
        raise
