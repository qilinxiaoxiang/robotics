"""Round 2 cold-start study (2026-11-18), runtime side: why does student s2g_200 creep forward at zero command in the
first 2 s at COM x +10 mm? Runtime simulation on the Mac mini, one job through mini.sh (lock + pre-flight),
--stand-s 0, 20 episodes, seeds 0..19, 8 workers, default drop 0.036 unless stated.

  dump          comx+10, walk, drops off, FLIGHT_STATE_DUMP: the recurrent state at the end of every episode without a fall
  warm          comx+10, walk, FLIGHT_WARM: each seed starts with the state its dump episode ended with (shadow log on)
  nominal/none  empty state at the other manifests, shadow log on (the 0-2 s forward speed at zero command)
  stand         comx+10, empty state, zero command for the whole episode (case stand), shadow log on
  stand_warm    the same with the warm state

  python3 train/ts2_start.py     run the missing cells (cells -> eval/cz_s2g_200_<cell>.json)
Analysis: ts2_start_analyse.py -> out/ts2_cause_start.json
"""
import subprocess
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
D = "s2g_200"
W = "train/eval/cz_warm_s2g_200"
# (cell, env, manifest, case, extra)
CELLS = [("dump", f"FLIGHT_STATE_DUMP={W}", "comx+10", "walk", "--stand-s 0 --drop 0"),
         ("warm", f"FLIGHT_SHADOW=1 FLIGHT_WARM={W}", "comx+10", "walk", "--stand-s 0"),
         ("nominal", "FLIGHT_SHADOW=1", "nominal", "walk", "--stand-s 0"),
         ("none", "FLIGHT_SHADOW=1", "none", "walk", "--stand-s 0"),
         ("stand", "FLIGHT_SHADOW=1", "comx+10", "stand", "--stand-s 0"),
         ("stand_warm", f"FLIGHT_SHADOW=1 FLIGHT_WARM={W}", "comx+10", "stand", "--stand-s 0"),
         ("stand_teacher", "FLIGHT_SHADOW=1 FLIGHT_SWAP=student_after:0", "comx+10", "stand", "--stand-s 0"),
         # the runtime episode started the way a distillation episode starts: released 2.5-3.5 cm above the floor,
         # tilted up to 5 degrees (flight_eval --landing), empty state
         ("landing", "FLIGHT_SHADOW=1", "comx+10", "walk --landing", "--stand-s 0"),
         ("landing_teacher", "FLIGHT_SHADOW=1 FLIGHT_SWAP=student_after:0", "comx+10", "walk --landing", "--stand-s 0"),
         # a warm state that carries no knowledge of this COM: saved at the end of no-pack episodes, used at COM x +10 mm
         ("dump_none", f"FLIGHT_STATE_DUMP={W}_from_none", "none", "walk", "--stand-s 0 --drop 0"),
         ("warm_from_none", f"FLIGHT_SHADOW=1 FLIGHT_WARM={W}_from_none", "comx+10", "walk", "--stand-s 0"),
         ("landing_warm_from_none", f"FLIGHT_SHADOW=1 FLIGHT_WARM={W}_from_none", "comx+10", "walk --landing", "--stand-s 0")]


def main():
    mini = str(TRAIN / "mini.sh")
    todo = [c for c in CELLS if not (TRAIN / f"eval/cz_{D}_{c[0]}.json").exists()]
    if todo:
        subprocess.run(["zsh", mini, "push"], check=True, capture_output=True)
        cmd = "; ".join(
            f"{env} $PY train/flight_eval.py --models train/ckpt/{D} --manifest train/manifests/flightpack-{man}.json "
            f"--case {case} --episodes 20 --workers 8 --extra='{extra}' --out train/eval/cz_{D}_{name}.json > /dev/null "
            f"2> train/eval/cz_{D}_{name}.err; echo done {name}" for name, env, man, case, extra in todo)
        r = subprocess.run(["zsh", mini, "run", cmd], capture_output=True, text=True)
        print(r.stdout.strip()[-400:].replace("\n", " "), r.stderr.strip()[-300:], flush=True)
        subprocess.run(["zsh", mini, "pull"], check=True, capture_output=True)


if __name__ == "__main__":
    main()
