"""Seeing-pick deployment rehearsal: walk_brain.Brain + seepick61.onnx in the as-built MuJoCo model (brain_sim_check.py
--sp-at), run case by case with a timeout, one JSON row per run in results/<stage>.jsonl (each row carries its
command line). Sim only; nothing here talks to the robot.

  python3 run_rehearsal.py main        # 9 placements x ball/box x 3 seeds on the as-built model (87979d52 plugged)
  python3 run_rehearsal.py mass        # landing spot on the training-time masses (1f2ab62c) and on 87979d52 without
                                       # the robot COM calibration
  python3 run_rehearsal.py diag        # landing spot with a training-like jaw, no I/O delay, training beak friction
  python3 run_rehearsal.py summary     # results/summary.json from every stage file
"""
import concurrent.futures as cf
import json
import os
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
SIM_ROOT = os.path.normpath(os.path.join(MAC, "..", "..", ".."))
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
NEW = os.path.join(SIM_ROOT, "microduck_rl", "cmu", "model", "manifests", "plugged.json")  # 87979d52, V1.35 saddle
OLD = os.path.join(HERE, "plugged_1f2ab62c.json")  # git show 1f2ab62c: the masses sp-b-1027 was trained on
STATE = json.load(open(os.path.join(SIM_ROOT, "CURRENT-STATE.json")))["facts"]
VOLT = float(STATE["servo_rail_v"]["value"])
DROP = float(STATE["servo_read_drop_fraction"]["value"])
COM_X = -2.25  # D-030 addendum: the robot's COM sits 2.25-2.5 mm behind the 87979d52 model (calibrated to its fall)
OFFSETS = [(0.0, 0.0), (0.01, 0.0), (-0.01, 0.0), (0.03, 0.0), (-0.03, 0.0),
           (0.0, 0.01), (0.0, -0.01), (0.0, 0.03), (0.0, -0.03)]
SHAPES = ("ball", "box")
SEEDS = (0, 1, 2)
TIMEOUT_S = 300


def base(manifest=NEW, com=COM_X):
    return ["--model", "asbuilt", "--manifest", manifest, "--com-x", str(com), "--volt", str(VOLT), "--drop", str(DROP),
            "--wired-guards", "--walk-s", "0", "--sp-at", "4"]


def cases(stage):
    out = []
    if stage == "main":
        for dx, dy in OFFSETS:
            for shape in SHAPES:
                for seed in SEEDS:
                    out.append((dict(case="as-built", dx=dx, dy=dy, shape=shape, seed=seed),
                                base() + ["--sp-offset", str(dx), str(dy), "--sp-shape", shape, "--seed", str(seed)]))
    elif stage == "mass":
        for label, man, com in (("trained-masses-1f2ab62c", OLD, 0.0), ("as-built-87979d52-uncalibrated", NEW, 0.0)):
            for shape in SHAPES:
                for seed in SEEDS:
                    out.append((dict(case=label, dx=0.0, dy=0.0, shape=shape, seed=seed),
                                base(man, com) + ["--sp-shape", shape, "--seed", str(seed)]))
    elif stage == "diag":
        extra = {"train-jaw": ["--sp-jaw-current", "1470", "--sp-jaw-kp", "400"],
                 "train-jaw-beak-mu-1.5": ["--sp-jaw-current", "1470", "--sp-jaw-kp", "400", "--sp-beak-mu", "1.5"],
                 "no-io-delay": ["--sensor-delay", "0", "--action-delay", "0", "--drop", "0"],
                 "no-cap": ["--sp-no-cap"],
                 "holding-stopped": ["--sp-holding", "stopped"]}
        for label, ex in extra.items():
            for shape in SHAPES:
                for seed in SEEDS:
                    args = base() + ["--sp-shape", shape, "--seed", str(seed)] + ex
                    if "--drop" in ex:  # the later --drop wins in argparse; keep one for the record
                        k = args.index("--drop")
                        del args[k:k + 2]
                    out.append((dict(case=label, dx=0.0, dy=0.0, shape=shape, seed=seed), args))
    return out


def run_one(meta, args):
    cmd = [PY, os.path.join(MAC, "brain_sim_check.py")] + args
    line = " ".join(shlex.quote(c) for c in cmd)
    try:
        p = subprocess.run(cmd, cwd=MAC, capture_output=True, text=True, timeout=TIMEOUT_S)
        last = [x for x in p.stdout.splitlines() if x.startswith("{")]
        if p.returncode or not last:
            return dict(meta, cmd=line, error=(p.stderr or p.stdout)[-2000:])
        r = json.loads(last[-1])
        return dict(meta, cmd=line, result=r, brain_log=[x for x in p.stdout.splitlines() if not x.startswith("{")])
    except subprocess.TimeoutExpired:
        return dict(meta, cmd=line, error=f"timeout {TIMEOUT_S} s")


def row_summary(row):
    """The per-run numbers the README reports."""
    if "error" in row:
        return dict({k: row[k] for k in ("case", "dx", "dy", "shape", "seed")}, error=row["error"][-300:])
    r = row["result"]
    s = r["seepick"]
    end, hb, ev, cap = s.get("at_end") or {}, s.get("at_handback") or {}, s["events"], s["jaw_cap"]
    return dict({k: row[k] for k in ("case", "dx", "dy", "shape", "seed")},
                object=dict(size_mm=round(s["object"]["size"] * 1000, 1), mass_g=round(s["object"]["mass"] * 1000, 2),
                            mu=s["object"]["mu"]),
                held_end=end.get("held"), lifted_end=bool(end.get("lift_m", 0) > 0.01), object_lift_end_m=end.get("lift_m"),
                pinched_end=end.get("pinched"), holding_bit_end=end.get("holding_bit"),
                holding_bit_handback=hb.get("holding_bit"), held_handback=hb.get("held"),
                first_pinched_s=ev["first_pinched_t"], first_holding_bit_s=ev["first_holding_bit_t"],
                fell=r["fell_at"] is not None, fell_at=r["fell_at"], peak_tilt_deg=round(ev["max_tilt"], 1),
                max_action_rad=ev["max_action"], guard_stop=s["guard"]["stop_at"], guard_why=s["guard"]["why"],
                guard_clipped_ticks=s["guard"]["clipped_ticks"], handback_s=s["handback_from_switch_s"],
                end_mode=r["end_mode"], lip_min_mm=None if ev["lip_min_m"] is None else round(ev["lip_min_m"] * 1000, 1),
                beak_floor_max_n=ev["beak_floor_force_max_n"],
                close=None if ev["close_at"] is None else dict(pad_xy_err_mm=round(ev["close_at"]["pad_xy_err_m"] * 1000, 1),
                                                                pad_z_mm=round(ev["close_at"]["pad_z_m"] * 1000, 1),
                                                                pad_root0_xy=ev["close_at"]["pad_root0_xy"],
                                                                tilt_deg=ev["close_at"]["tilt"]),
                goal_clamped_ticks=ev.get("goal_clamped_ticks"),
                holding_bit_without_pinch_ticks=ev.get("holding_bit_without_pinch_ticks", 0),
                pinch_without_holding_bit_ticks=ev.get("pinch_without_holding_bit_ticks", 0),
                camera=dict(visible_frames=s["camera"]["visible"], delivered=s["camera"]["delivered"],
                            last_visible_s=s["camera"]["last_visible_from_switch_s"], delay_s=s["camera"]["delay_s"]),
                jaw_cap=dict(min_cap_deg=cap["min_cap_deg"], ticks_cap_below_22=cap["ticks_cap_below_trained"],
                             ticks_clamped=cap["ticks_clamped"], first_clamp=cap["first_clamp"],
                             closed_zone_ticks=cap["closed_zone_ticks"], clamp_names=cap["clamp_names"],
                             max_head_pitch_open_deg=cap["max_head_pitch_open_deg"]))


def main():
    stage = sys.argv[1]
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    if stage == "summary":
        out = {}
        for st in ("main", "mass", "diag"):
            path = os.path.join(HERE, "results", f"{st}.jsonl")
            if os.path.exists(path):
                out[st] = [row_summary(json.loads(x)) for x in open(path)]
        json.dump(out, open(os.path.join(HERE, "results", "summary.json"), "w"), indent=1)
        return
    todo = cases(stage)
    workers = int(os.environ.get("SP_WORKERS", "3"))
    path = os.path.join(HERE, "results", f"{stage}.jsonl")
    with open(path, "w") as f, cf.ThreadPoolExecutor(workers) as ex:
        for row in ex.map(lambda c: run_one(*c), todo):
            f.write(json.dumps(row) + "\n")
            f.flush()
            sm = row_summary(row)
            print(json.dumps({k: sm.get(k) for k in ("case", "dx", "dy", "shape", "seed", "held_end", "fell",
                                                     "peak_tilt_deg", "max_action_rad", "guard_why", "error")}), flush=True)


if __name__ == "__main__":
    main()
