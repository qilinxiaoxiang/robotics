"""Added acceptance case of TEACHER-STUDENT-PLAN.md: walking with a neck and head command at every load state.

  python3 train/accept_head.py run <models dir under train/ckpt> [<models dir> ...]
  python3 train/accept_head.py score <models dir> [<models dir> ...]     -> out/accept_head_<first dir>.json

Per load (none, 25 %, 50 %, 75 %, batteries out, full pack): the runtime walk command of the acceptance set (20 s,
seeds 0..19) with the neck commanded to 0.5 rad and the head yawed 0.6 rad from the walk start, through style_eval.py
on the Mac mini (same tool, seeds and machine as accept_universal.py; result files eval/uh_<dir>_neck_<load>.json).
Read-out per load and policy: falls of 20, median speed of the upright episodes (m/s) and the distance that speed
covers in the 15 s of walking, mean neck pitch and head yaw reached. No pass line of its own: the arms are compared on
identical cases.
"""
import json
import subprocess
import sys
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
LOADS = (("none", "none", ""), ("load025", "load025", "--stand-s 0"), ("load050", "load050", "--stand-s 0"),
         ("load075", "load075", "--stand-s 0"), ("nobatt", "nobatt", "--stand-s 0"), ("load100", "load100", "--stand-s 0"))
HEAD = "--neck-pitch 0.5 --head-yaw 0.6"
EPISODES, SEED0 = 20, 0


def run(dirs):
    mini = str(TRAIN / "mini.sh")
    subprocess.run(["zsh", mini, "push"], check=True, capture_output=True)
    for m in dirs:
        todo = [(n, man, ex) for n, man, ex in LOADS if not (TRAIN / f"eval/uh_{m}_neck_{n}.json").exists()]
        for i in range(0, len(todo), 6):
            cmd = "; ".join(
                f"$PY train/style_eval.py --name uh_{m}_neck_{n} --models train/ckpt/{m} "
                f"--manifest train/manifests/flightpack-{man}.json --case walk --episodes {EPISODES} --workers 8 "
                f"--seed0 {SEED0} --extra='{(ex + ' ' + HEAD).strip()}' --out train/eval/uh_{m}_neck_{n}.json > /dev/null 2>&1; "
                f"echo done {n}" for n, man, ex in todo[i:i + 6])
            r = subprocess.run(["zsh", mini, "run", cmd], capture_output=True, text=True)
            print(m, r.stdout.replace("busy\n", "").strip()[-300:], flush=True)
            subprocess.run(["zsh", mini, "pull"], check=True, capture_output=True)


def score(dirs):
    out = dict(case=f"walk {HEAD}", episodes=EPISODES, seeds=f"{SEED0}..{SEED0 + EPISODES - 1}", loads={})
    for n, _, _ in LOADS:
        row = {}
        for m in dirs:
            p = TRAIN / f"eval/uh_{m}_neck_{n}.json"
            if not p.exists():
                row[m] = None
                continue
            s = json.loads(p.read_text())["summary"]
            v = s.get("speed_median_upright")
            row[m] = dict(falls=s["falls"], speed_m_s=v, distance_15s_m=None if v is None else round(15 * v, 2),
                          neck_pitch_mean=s.get("neck_pitch_mean"), head_yaw_mean=s.get("head_yaw_mean"),
                          leg_p99_nm=s.get("leg_force_p99_nm_median"))
        out["loads"][n] = row
        print(n, "; ".join(f"{m}: " + ("missing" if r is None else
                                         f"falls {r['falls']}/20, {r['speed_m_s']} m/s, neck {r['neck_pitch_mean']}, yaw {r['head_yaw_mean']}")
                           for m, r in row.items()))
    (TRAIN / f"out/accept_head_{dirs[0]}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    (run if sys.argv[1] == "run" else score)(sys.argv[2:])
