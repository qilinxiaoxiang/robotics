"""Round 2 cause study (2026-11-18): why do the students fall at forward COM with dropped reads while teacher A-999
does not? Runtime simulation on the Mac mini, one job through mini.sh (lock + pre-flight), walk, manifest comx+10,
--stand-s 0, 20 episodes, seeds 0..19, 8 workers. Switches of flight_eval.py (default off):

  FLIGHT_SHADOW=1                the student drives; per called tick both actions, skipped ticks, trunk pitch/roll/vx
  FLIGHT_SWAP=teach_after:N      the teacher's action on the N called ticks after every skipped tick
  FLIGHT_SWAP=student_after:3    the teacher drives, the student's action on the 3 ticks after every skipped tick
  FLIGHT_SWAP=teach_rand:3:p     the teacher's action on 3 ticks from random ticks (control, same rate as the drops)

  python3 train/ts2_cause.py            run the missing cells, then the summary of the swap cells
  python3 train/ts2_cause_analyse.py    shadow-log and observation-parity analysis

Cells -> eval/cz_<dir>_<cell>.json; swap summary -> out/ts2_cause_swap.json (with the counters that show each switch fired).
"""
import json
import subprocess
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
P_RAND = 0.0347   # start probability per called tick = called ticks that follow a skip, 0.036 * (1 - 0.036)
# (cell name, env, extra flags)
CELLS = [("shadow", "FLIGHT_SHADOW=1", "--stand-s 0"),
         ("shadow_nodrop", "FLIGHT_SHADOW=1", "--stand-s 0 --drop 0"),
         ("teach1", "FLIGHT_SWAP=teach_after:1", "--stand-s 0"),
         ("teach3", "FLIGHT_SWAP=teach_after:3", "--stand-s 0"),
         ("student3", "FLIGHT_SWAP=student_after:3", "--stand-s 0"),
         ("rand3", f"FLIGHT_SWAP=teach_rand:3:{P_RAND}", "--stand-s 0"),
         # beyond the three requested checks: the teacher drives every tick and the student's action is logged beside it
         # (the student's error on the teacher's own path), and the teacher with action noise of the student's error size
         ("tshadow", "FLIGHT_SHADOW=1 FLIGHT_SWAP=student_after:0", "--stand-s 0"),
         ("tnoise08", "FLIGHT_SWAP=teach_noise:0.08", "--stand-s 0"),
         ("tnoise15", "FLIGHT_SWAP=teach_noise:0.15", "--stand-s 0"),
         ("tnoise15_nodrop", "FLIGHT_SWAP=teach_noise:0.15", "--stand-s 0 --drop 0"),
         # the teacher drives the first 100 / 200 control ticks (the standing start; the walk start too), the student
         # sees every observation and builds its state, then drives alone: are the early falls a start-up effect?
         ("hand100", "FLIGHT_HANDOVER=train/ckpt/ts2a999_teacher/teacher.onnx:100", "--stand-s 0"),
         ("hand200", "FLIGHT_HANDOVER=train/ckpt/ts2a999_teacher/teacher.onnx:200", "--stand-s 0")]
ONE_DIR = ("tnoise08", "tnoise15", "tnoise15_nodrop")   # the student plays no part in these: first directory only
DIRS = ["s2g_200", "s2d_300"]
REF = dict(s2g_200="pk_s2g_200_comx", s2d_300="pk_s2d_300_comx")


def main():
    mini = str(TRAIN / "mini.sh")
    todo = [(d, c) for d in DIRS for c in CELLS if not (TRAIN / f"eval/cz_{d}_{c[0]}.json").exists()
            and (c[0] not in ONE_DIR or d == DIRS[0])]
    if todo:
        subprocess.run(["zsh", mini, "push"], check=True, capture_output=True)
        cmd = "; ".join(
            f"{env} $PY train/flight_eval.py --models train/ckpt/{d} --manifest train/manifests/flightpack-comx+10.json "
            f"--case walk --episodes 20 --workers 8 --extra='{extra}' --out train/eval/cz_{d}_{name}.json > /dev/null "
            f"2> train/eval/cz_{d}_{name}.err; echo done {d} {name}" for d, (name, env, extra) in todo)
        r = subprocess.run(["zsh", mini, "run", cmd], capture_output=True, text=True)
        print(r.stdout.strip()[-400:].replace("\n", " "), r.stderr.strip()[-300:], flush=True)
        subprocess.run(["zsh", mini, "pull"], check=True, capture_output=True)

    out = {}
    for d in DIRS:
        ref = json.loads((TRAIN / f"eval/{REF[d]}.json").read_text())["summary"]
        out[d] = dict(reference_no_switch=dict(falls_of_20=ref["falls"], file=f"eval/{REF[d]}.json"))
        for name, env, extra in CELLS:
            p = TRAIN / f"eval/cz_{d}_{name}.json"
            if not p.exists():
                continue
            j = json.loads(p.read_text())
            s, eps = j["summary"], j["episodes"]
            stat = {}
            for e in eps:
                for k, v in (e.get("diag_stat") or {}).items():
                    stat[k] = stat.get(k, 0) + v
            row = dict(switch=env, extra=extra, falls_of_20=s["falls"], fall_times=[round(x, 1) for x in s["fall_times"]],
                       speed=s["speed_median_upright"], counters_sum_over_episodes=stat,
                       episodes_with_counters=sum(1 for e in eps if e.get("diag_stat")), file=f"eval/cz_{d}_{name}.json")
            if stat.get("calls"):
                row["teacher_applied_fraction"] = round(stat.get("teacher_applied_ticks", 0) / stat["calls"], 4)
                row["skipped_per_tick"] = round(stat.get("skipped_ticks", 0) / (stat["calls"] + stat.get("skipped_ticks", 0)), 4)
            out[d][name] = row
            print(f"{d} {name}: falls {s['falls']}/20 at {row['fall_times']}  counters {stat}", flush=True)
    (TRAIN / "out/ts2_cause_swap.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
