"""Round 2 diagnostic (2026-11-18): does stepping a recurrent student's state across dropped ticks remove its
forward-COM falls? flight_eval FLIGHT_CATCHUP=1 (after g - 1 skipped ticks the state is stepped g - 1 times on the
previous observation before the normal call). Runtime simulation on the Mac mini, one job through mini.sh (lock +
pre-flight), walk, 20 episodes, seeds 0..19.

  python3 train/ts2_catchup.py

Cells -> eval/cu_<dir>_<case>.json; summary out/ts2_catchup.json with the references without the switch
(eval/pk_<dir>_comx.json, eval/dr_s2g_200_comx_d072.json, eval/pk_s2g_200_full.json).
"""
import json
import subprocess
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
# (dir, case name, manifest, extra flags, reference file without the switch)
CELLS = [("s2d_300", "comx", "comx+10", "--stand-s 0", "pk_s2d_300_comx"),
         ("s2g_140", "comx", "comx+10", "--stand-s 0", "pk_s2g_140_comx"),
         ("s2g_200", "comx", "comx+10", "--stand-s 0", "pk_s2g_200_comx"),
         ("s2g_200", "comx_d072", "comx+10", "--stand-s 0 --drop 0.072", "dr_s2g_200_comx_d072"),
         ("s2g_200", "full", "load100", "--stand-s 0", "pk_s2g_200_full")]
mini = str(TRAIN / "mini.sh")
todo = [c for c in CELLS if not (TRAIN / f"eval/cu_{c[0]}_{c[1]}.json").exists()]
if todo:
    subprocess.run(["zsh", mini, "push"], check=True, capture_output=True)
    cmd = "; ".join(
        f"FLIGHT_CATCHUP=1 $PY train/flight_eval.py --models train/ckpt/{d} --manifest train/manifests/flightpack-{man}.json "
        f"--case walk --episodes 20 --workers 8 --extra='{extra}' --out train/eval/cu_{d}_{name}.json > /dev/null "
        f"2> train/eval/cu_{d}_{name}.err; echo done {d} {name}" for d, name, man, extra, _ in todo)
    r = subprocess.run(["zsh", mini, "run", cmd], capture_output=True, text=True)
    print(r.stdout.strip()[-300:].replace("\n", " "), r.stderr.strip()[-300:], flush=True)
    subprocess.run(["zsh", mini, "pull"], check=True, capture_output=True)


def read(stem):
    p = TRAIN / f"eval/{stem}.json"
    if not p.exists():
        return None
    s = json.loads(p.read_text())["summary"]
    return dict(falls_of_20=s["falls"], fall_times=[round(x, 1) for x in s["fall_times"]], speed=s["speed_median_upright"],
                file=f"eval/{stem}.json")


out = {}
for d, name, man, extra, ref in CELLS:
    row = dict(catchup=read(f"cu_{d}_{name}"), reference=read(ref))
    out[f"{d}_{name}"] = row
    print(f"{d} {name}: catch-up {row['catchup']} | without {row['reference']}", flush=True)
(TRAIN / "out/ts2_catchup.json").write_text(json.dumps(out, indent=1))
