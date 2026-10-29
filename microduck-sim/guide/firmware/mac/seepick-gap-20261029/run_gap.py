"""Seeing-pick gap study (2026-10-29), runtime side: the rehearsal grid (run_rehearsal.py main: 9 placements x ball/box x
seeds 0-2, as-built model 87979d52 plugged, --com-x -2.25, CURRENT-STATE rail voltage and read drops) under one change at a
time, one JSON row per run in results/<stage>.jsonl (each row carries its command line). Success is reported both as the
training env's measure (held_ticks: pinched, off the floor, lifted over 1 cm, on >= 20 ticks from phase 0.44 until the
hand-back) and as the rehearsal's held_end (still held 3 s after the hand-back).

  stale        the rehearsal as it ran (evaluate_delay's post-compile inertia edits leave stale collision bounding volumes)
  refit        --bvh-refit (brain_sim_check.refit_body_bvh): the only change
  refit_tjaw   --bvh-refit with the training-strength jaw (1470 mA, KP 400)
  refit_mu15   --bvh-refit with the training beak friction 1.5 (a lined beak)
  refit_jaw150 --bvh-refit with the jaw at the 150 mA EEPROM current limit (a runtime patch candidate)
  refit_sticky --bvh-refit and the training env's contact solver (elliptic cone, impratio 10: microduck_ground_grasp_env_cfg)
  refit_sticky_tjaw      refit_sticky with the training-strength jaw (1470 mA, KP 400)
  refit_sticky_mu15      refit_sticky with the training beak friction 1.5
  refit_sticky_tjaw_mu15 both of the above
  refit_sticky_jaw150    refit_sticky with the jaw at the 150 mA EEPROM current limit (runtime-reachable)

  SP_WORKERS=2 nice python3 run_gap.py refit      (Mac mini: workers 3 or fewer)
  python3 run_gap.py summary                      # results/summary.json
"""
import concurrent.futures as cf
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "seepick-rehearsal-20261027"))
import run_rehearsal as R  # noqa: E402

SUCCESS_TICKS = 20  # seeing_audit.SUCCESS_STEPS (brain_sim_check SP_SUCCESS_TICKS)
EXTRA = {"stale": [], "refit": ["--bvh-refit"],
         "refit_tjaw": ["--bvh-refit", "--sp-jaw-current", "1470", "--sp-jaw-kp", "400"],
         "refit_mu15": ["--bvh-refit", "--sp-beak-mu", "1.5"],
         "refit_jaw150": ["--bvh-refit", "--sp-jaw-current", "150"],
         "refit_sticky": ["--bvh-refit", "--sp-cone", "elliptic", "--sp-impratio", "10"],
         "refit_sticky_tjaw": ["--bvh-refit", "--sp-cone", "elliptic", "--sp-impratio", "10", "--sp-jaw-current", "1470", "--sp-jaw-kp", "400"],
         "refit_sticky_mu15": ["--bvh-refit", "--sp-cone", "elliptic", "--sp-impratio", "10", "--sp-beak-mu", "1.5"],
         "refit_sticky_tjaw_mu15": ["--bvh-refit", "--sp-cone", "elliptic", "--sp-impratio", "10", "--sp-jaw-current", "1470", "--sp-jaw-kp", "400", "--sp-beak-mu", "1.5"],
         "refit_sticky_jaw150": ["--bvh-refit", "--sp-cone", "elliptic", "--sp-impratio", "10", "--sp-jaw-current", "150"]}
# Shawn's two levers for the printed orange ball (2026-10-29), on refit_sticky: lip friction set by the beak (priority 1,
# so the beak's value is the pair's: inner-tube lining 1.1 against bare PLA 0.35 and 0.5), and the close timing (close at
# the first beak touch instead of phase 0.34; the 150 mA jaw). Run them ball-only: SP_SHAPES=ball.
STICKY = ["--bvh-refit", "--sp-cone", "elliptic", "--sp-impratio", "10"]
EXTRA.update({"refit_sticky_jaw300": STICKY + ["--sp-jaw-current", "300"],   # jaw current sweep at KP 200
              "refit_sticky_jaw600": STICKY + ["--sp-jaw-current", "600"],
              "refit_sticky_kp400": STICKY + ["--sp-jaw-kp", "400"],           # stiffness alone, 100 mA
              "lip_mu110": STICKY + ["--sp-beak-mu", "1.1", "--sp-beak-priority"],
              "lip_mu050": STICKY + ["--sp-beak-mu", "0.5", "--sp-beak-priority"],
              "lip_mu035": STICKY + ["--sp-beak-mu", "0.35", "--sp-beak-priority"],
              "lip_mu110_jaw150": STICKY + ["--sp-beak-mu", "1.1", "--sp-beak-priority", "--sp-jaw-current", "150"],
              "lip_mu050_jaw150": STICKY + ["--sp-beak-mu", "0.5", "--sp-beak-priority", "--sp-jaw-current", "150"],
              "lip_mu035_jaw150": STICKY + ["--sp-beak-mu", "0.35", "--sp-beak-priority", "--sp-jaw-current", "150"],
              "ball_baseline": list(STICKY),  # refit_sticky again, ball-only, with the contact and push fields of 2026-10-29
              "ball_jaw150": STICKY + ["--sp-jaw-current", "150"],   # refit_sticky_jaw150 again, ball-only, same fields
              "close_on_contact": STICKY + ["--sp-close-on-contact"],
              "close_on_contact_jaw150": STICKY + ["--sp-close-on-contact", "--sp-jaw-current", "150"]})


def run_one(meta, args, tries=3):
    """R.run_one, rerun when MuJoCo/onnxruntime aborts in libc++ (recursive_mutex lock failed, seen under load in the
    rehearsal); the kept row is the completed rerun."""
    for _ in range(tries):
        row = R.run_one(meta, args)
        if "recursive_mutex" not in row.get("error", ""):
            return row
    return row


def cases(stage):
    shapes = os.environ.get("SP_SHAPES", ",".join(R.SHAPES)).split(",")  # SP_SHAPES=ball: the ball cases only
    return [(dict(meta, case=stage), args + EXTRA[stage]) for meta, args in R.cases("main") if meta["shape"] in shapes]


def summarize(rows):
    rows = [R.row_summary(x) for x in rows]
    raw = rows
    return raw


def main():
    stage = sys.argv[1]
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    if stage == "summary":
        out = {}
        for st in EXTRA:
            path = os.path.join(HERE, "results", f"{st}.jsonl")
            if not os.path.exists(path):
                continue
            raw = [json.loads(x) for x in open(path)]
            rows = [R.row_summary(x) for x in raw]
            for r, x in zip(rows, raw):
                if "error" not in r:
                    r["held_ticks"] = x["result"]["seepick"]["events"].get("held_ticks", 0)
                    r["train_success"] = r["held_ticks"] >= SUCCESS_TICKS
            ok = [r for r in rows if "error" not in r]
            out[st] = dict(
                runs=len(rows), errors=len(rows) - len(ok),
                train_success=sum(r["train_success"] for r in ok),
                held_handback=sum(bool(r["held_handback"]) for r in ok),
                held_end=sum(bool(r["held_end"]) for r in ok),
                pinched_ever=sum(r["first_pinched_s"] is not None for r in ok),
                fell=sum(r["fell"] for r in ok), guard_stops=sum(r["guard_why"] is not None for r in ok),
                peak_tilt_deg=[min(r["peak_tilt_deg"] for r in ok), max(r["peak_tilt_deg"] for r in ok)] if ok else None,
                lip_min_mm=[min(r["lip_min_mm"] for r in ok), max(r["lip_min_mm"] for r in ok)] if ok else None,
                beak_floor_max_n=[min(r["beak_floor_max_n"] for r in ok), max(r["beak_floor_max_n"] for r in ok)] if ok else None,
                pad_xy_err_mm_at_close=[min(r["close"]["pad_xy_err_mm"] for r in ok if r["close"]),
                                        max(r["close"]["pad_xy_err_mm"] for r in ok if r["close"])] if ok else None,
                by_shape={s: f'{sum(r["train_success"] for r in ok if r["shape"] == s)}/{sum(r["shape"] == s for r in ok)}'
                          for s in R.SHAPES},
                by_offset={f'{dx:+.2f},{dy:+.2f}': f'{sum(r["train_success"] for r in ok if (r["dx"], r["dy"]) == (dx, dy))}/'
                                                   f'{sum((r["dx"], r["dy"]) == (dx, dy) for r in ok)}'
                           for dx, dy in R.OFFSETS},
                rows=rows)
        json.dump(out, open(os.path.join(HERE, "results", "summary.json"), "w"), indent=1)
        print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in out.items()}, indent=1))
        return
    todo = cases(stage)
    path = os.path.join(HERE, "results", f"{stage}.jsonl")
    with open(path, "w") as f, cf.ThreadPoolExecutor(int(os.environ.get("SP_WORKERS", "2"))) as ex:
        for row in ex.map(lambda c: run_one(*c), todo):
            f.write(json.dumps(row) + "\n")
            f.flush()
            sm = R.row_summary(row)
            held = None if "error" in row else row["result"]["seepick"]["events"].get("held_ticks", 0)
            print(json.dumps({k: sm.get(k) for k in ("case", "dx", "dy", "shape", "seed", "held_end", "held_handback", "fell", "error")}
                             | {"held_ticks": held}), flush=True)


if __name__ == "__main__":
    main()
